import grpc
import asyncio
import hashlib         

from proto import game_pb2
from proto import game_pb2_grpc


def xor_distance(id1: str, id2: str) -> int:     
    h1 = int(hashlib.sha1(id1.encode()).hexdigest(), 16)
    h2 = int(hashlib.sha1(id2.encode()).hexdigest(), 16)
    return h1 ^ h2

class GameNodeServicer(game_pb2_grpc.GameNodeServicer):
    def __init__(self, player_id, my_ip):
        self.player_id = player_id
        self.port = 0
        self.my_ip = my_ip  
        self.hp = 100
        self.hp_lock = asyncio.Lock()
        self.dht_table = {}
        self.dht_lock = asyncio.Lock()
        self.missed_pings = {}
        self.missed_pings_lock = asyncio.Lock()
        self.is_host = False
        self.host_id = None
        self.host_ip = None
        self.host_port = None
        self.lobby_nodes = [player_id] 

    async def Ping(self, request, context):
        return game_pb2.PingResponse(success=True)
        
    async def remove_dead_node(self, node_id):
        async with self.dht_lock:
            if node_id in self.dht_table:
                del self.dht_table[node_id]

        async with self.missed_pings_lock:
            if node_id in self.missed_pings:
                del self.missed_pings[node_id]
                
        if hasattr(self, 'lobby_nodes') and node_id in self.lobby_nodes:
            self.lobby_nodes.remove(node_id)

    async def StorePlayer(self, request, context):
        async with self.dht_lock:
            self.dht_table[request.player_id] = {
                "ip": request.ip,
                "port": request.port
            }
            if request.player_id not in self.lobby_nodes:
                self.lobby_nodes.append(request.player_id)
            print(f"\n[DHT] Stored in local DHT: {request.player_id} -> {request.ip}:{request.port}")
        return game_pb2.ActionResponse(success=True, status_message="Data stored successfully.")
        
    async def JoinNetwork(self, request, context):
        from network import grpc_client 

        async with self.dht_lock:
            current_nodes = []
            existing_nodes = list(self.dht_table.values()) 
            
            for nid, info in self.dht_table.items():
                current_nodes.append(
                    game_pb2.NodeContact(node_id=nid, ip=info["ip"], port=info["port"])
                )
            
            self.dht_table[request.player_id] = {
                "ip": request.ip,
                "port": request.port
            }
            
            if request.player_id not in self.lobby_nodes:
                self.lobby_nodes.append(request.player_id)
                
            print(f"\n[HOST] Player '{request.player_id}' joined the lobby! Added to DHT.")

        for node in existing_nodes:
            asyncio.create_task(
                grpc_client.send_store_player(
                    target_ip=node["ip"],
                    target_port=node["port"],
                    player_id=request.player_id, 
                    my_ip=request.ip,            
                    my_port=request.port         
                )
            )

        return game_pb2.JoinResponse(
            success=True,
            status_message="Welcome to the network!",
            host_id=self.player_id,
            all_nodes=current_nodes
        )

    async def LeaveNetwork(self, request, context):
        await self.remove_dead_node(request.player_id)
        print(f"\n[NETWORK] Player '{request.player_id}' disconnected.", flush=True)
        return game_pb2.ActionResponse(success=True, status_message="Removed from DHT.")

    async def HostDisconnected(self, request, context):
        if request.old_host_id in self.lobby_nodes or request.old_host_id in self.dht_table:
            print(f"\n[NETWORK] Host '{request.old_host_id}' disconnected!", flush=True)
            await self.remove_dead_node(request.old_host_id)
        
        async with self.dht_lock:
            self.host_id = request.new_host_id
            self.host_ip = request.new_host_ip
            self.host_port = request.new_host_port           
            self.dht_table[request.new_host_id] = {
                "ip": request.new_host_ip,
                "port": request.new_host_port
            }
            
            self.lobby_nodes = [request.new_host_id]
            
            for node in request.all_nodes:
                if node.node_id != self.player_id:
                    self.dht_table[node.node_id] = {"ip": node.ip, "port": node.port}
                if node.node_id not in self.lobby_nodes:
                    self.lobby_nodes.append(node.node_id)
            
            if self.player_id not in self.lobby_nodes:
                self.lobby_nodes.append(self.player_id)
        
        print(f"\n[NETWORK] New host: '{request.new_host_id}'", flush=True)
        return game_pb2.ActionResponse(success=True, status_message="Host changed.")
    
    async def PromoteToHost(self, request, context):
        old_host = self.host_id
        
        if old_host and old_host != self.player_id:
            print(f"\n[NETWORK] The host '{old_host}' disconnected.", flush=True)
            await self.remove_dead_node(old_host)
        
        print(f"[NETWORK] You are the new HOST by succession!", flush=True)
        
        self.is_host = True
        self.host_id = request.new_host_id
        self.host_ip = request.new_host_ip
        self.host_port = request.new_host_port
        
        from network import discovery
        asyncio.create_task(discovery.run_discovery_server(self.player_id, self.port))
        return game_pb2.ActionResponse(success=True, status_message="You are now the host.")
    
async def monitor_heartbeats(servicer, interval=5, max_misses=3):
    from network import grpc_client
    from network import discovery

    async def ping_client_node(node_id, info):
        res = await grpc_client.send_ping(info['ip'], info['port'], servicer.player_id)
        
        is_dead = False 
        async with servicer.missed_pings_lock:
            if res and res.success:
                servicer.missed_pings[node_id] = 0
            else:
                current_misses = servicer.missed_pings.get(node_id, 0) + 1
                servicer.missed_pings[node_id] = current_misses
                if current_misses >= max_misses:
                    is_dead = True

        if is_dead:
            print(f"\n[NETWORK] Dropped connection! '{node_id}' disconnected.", flush=True)
            await servicer.remove_dead_node(node_id)
            async with servicer.dht_lock:
                remaining_nodes = list(servicer.dht_table.values())

            for other_node in remaining_nodes:
                asyncio.create_task(
                    grpc_client.send_leave(other_node["ip"], other_node["port"], node_id)
                )

    while True:
        try:
            await asyncio.sleep(interval)

            if servicer.is_host:
                async with servicer.dht_lock:
                    nodes_to_ping = dict(servicer.dht_table)

                tasks = []
                for node_id, info in nodes_to_ping.items():
                    if node_id == servicer.player_id:
                        continue 
                    tasks.append(ping_client_node(node_id, info))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            else:
                if not servicer.host_ip or not servicer.host_port:
                    if servicer.lobby_nodes:
                        next_potential = servicer.lobby_nodes[0]
                        if next_potential != servicer.player_id and next_potential in servicer.dht_table:
                            servicer.host_id = next_potential
                            servicer.host_ip = servicer.dht_table[next_potential]["ip"]
                            servicer.host_port = servicer.dht_table[next_potential]["port"]
                            continue
                    continue
                    
                res = await grpc_client.send_ping(servicer.host_ip, servicer.host_port, servicer.player_id)

                host_is_dead = False
                async with servicer.missed_pings_lock:
                    if res and res.success:
                        servicer.missed_pings[servicer.host_id] = 0
                    else:
                        current_misses = servicer.missed_pings.get(servicer.host_id, 0) + 1
                        servicer.missed_pings[servicer.host_id] = current_misses

                        if current_misses >= max_misses:
                            host_is_dead = True

                if host_is_dead:
                    old_host_id = servicer.host_id
                    print(f"\n[NETWORK] The host '{old_host_id}' disconnected abruptly!", flush=True)
                    await servicer.remove_dead_node(old_host_id)
                    
                    if servicer.lobby_nodes and servicer.lobby_nodes[0] == servicer.player_id:
                        print("\n[NETWORK] You are the new HOST by succession!", flush=True)
                        servicer.is_host = True
                        servicer.host_id = servicer.player_id
                        servicer.host_ip = servicer.my_ip
                        servicer.host_port = servicer.port

                        asyncio.create_task(discovery.run_discovery_server(servicer.player_id, servicer.port))

                        async with servicer.dht_lock:
                            remaining_nodes = list(servicer.dht_table.items())
                            
                        for nid, info in remaining_nodes:
                            asyncio.create_task(
                                grpc_client.send_host_disconnected(
                                    info["ip"], info["port"],
                                    old_host_id,
                                    servicer.player_id,
                                    servicer.my_ip,
                                    servicer.port,
                                    {k: v for k, v in servicer.dht_table.items()}
                                )
                            )
                    else:
                        if servicer.lobby_nodes:
                            next_host_id = servicer.lobby_nodes[0]
                            if next_host_id in servicer.dht_table:
                                servicer.host_id = next_host_id
                                servicer.host_ip = servicer.dht_table[next_host_id]["ip"]
                                servicer.host_port = servicer.dht_table[next_host_id]["port"]
                                print(f"[NETWORK] Waiting for succession. Next expected host: '{next_host_id}'", flush=True)
                            else:
                                servicer.host_id = None; servicer.host_ip = None; servicer.host_port = None
                        else:
                            servicer.host_id = None; servicer.host_ip = None; servicer.host_port = None
                            
        except asyncio.CancelledError:
            break
        except Exception:
            pass

async def start_grpc_server(player_id, my_ip):
    server = grpc.aio.server()
    servicer = GameNodeServicer(player_id, my_ip)
    
    game_pb2_grpc.add_GameNodeServicer_to_server(servicer, server)

    assigned_port = server.add_insecure_port('0.0.0.0:0')
    servicer.port = assigned_port

    await server.start()
    print(f"gRPC server automatically assigned to port {assigned_port}.")
    return server, servicer, assigned_port