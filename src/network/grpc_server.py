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

    async def Ping(self, request, context):
        return game_pb2.PingResponse(success = True)
    
    async def remove_dead_node(self, node_id):
        async with self.dht_lock:
            if node_id in self.dht_table:
                del self.dht_table[node_id]

        async with self.missed_pings_lock:
            if node_id in self.missed_pings:
                del self.missed_pings[node_id]
    
    async def Attack(self, request, context):
        async with self.hp_lock:
            if self.hp <= 0:
                return game_pb2.ActionResponse(
                    success=False,
                    status_message=f"{self.player_id} is already dead!"
                )

            self.hp = max(0, self.hp - request.damage)

            print(f"\n OUCH!!! You have been attacked by {request.attacker_id} with {request.weapon}! {request.damage} damage points taken!")
            print(f"Current HP : {self.hp}")

            if self.hp == 0:
                print("\n You have been eliminated! X-X")
                print("\n You can no longer attack or chat.")

        return game_pb2.ActionResponse(
            success=True,
            status_message=f"Attack towards {self.player_id} successful! Remaining HP: {self.hp}"
        )
    
    async def Chat(self, request, context):
        print(f"\n[{request.sender_id}]: {request.text}", flush=True)
        return game_pb2.ActionResponse(success=True, status_message="Message delivered.")

    async def StorePlayer(self, request, context):
        async with self.dht_lock:
            self.dht_table[request.player_id] = {
                "ip": request.ip,
                "port": request.port
            }
            print(f"\n[DHT] Stored in local DHT: {request.player_id} -> {request.ip}:{request.port}")
        return game_pb2.ActionResponse(success=True, status_message="Data stored successfully.")

    async def FindPlayer(self, request, context):
        target = request.target_player_id
        
        async with self.dht_lock:
            if target == self.player_id:
                return game_pb2.FindPlayerResponse(found=True, ip=self.my_ip, port=self.port)

            if target in self.dht_table:
                return game_pb2.FindPlayerResponse(
                    found=True,
                    ip=self.dht_table[target]["ip"],
                    port=self.dht_table[target]["port"]
                )
            
            sorted_nodes = sorted(
                self.dht_table.items(),
                key=lambda item: xor_distance(item[0], target)
            )
            
            closest = [
                game_pb2.NodeContact(node_id=nid, ip=info["ip"], port=info["port"])
                for nid, info in sorted_nodes[:3]
            ]
            return game_pb2.FindPlayerResponse(found=False, closest_nodes=closest)
        
    async def LeaveNetwork(self, request, context):
        async with self.dht_lock:
            self.dht_table.pop(request.player_id, None)
        print(f"\n{request.player_id} left the network.")
        return game_pb2.ActionResponse(success=True, status_message="Removed from DHT.")

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


async def monitor_heartbeats(servicer, interval=5, max_misses=3):
    from network import grpc_client
    while True:
        await asyncio.sleep(interval)

        async with servicer.dht_lock:
            nodes_to_ping = dict(servicer.dht_table)

        for node_id, info in nodes_to_ping.items():
            res = await grpc_client.send_ping(info['ip'], info['port'], servicer.player_id)

            async with servicer.missed_pings_lock:
                if res and res.success:
                    self_missed = servicer.missed_pings.get(node_id, 0)
                    if self_missed > 0:
                         servicer.missed_pings[node_id] = 0
                else:
                    current_misses = servicer.missed_pings.get(node_id, 0) + 1
                    servicer.missed_pings[node_id] = current_misses

                    if current_misses >= max_misses:
                        await servicer.remove_dead_node(node_id)
                        print(f"\n[NETWORK] Dropped connection! '{node_id}' disconnected.", flush=True)

                        # Propagar a remoção a todos os nós ainda vivos
                        async with servicer.dht_lock:
                            remaining_nodes = list(servicer.dht_table.values())

                        for other_node in remaining_nodes:
                            asyncio.create_task(
                                grpc_client.send_leave(
                                    other_node["ip"],
                                    other_node["port"],
                                    node_id  # player_id do nó que morreu
                                )
                            )


async def start_grpc_server(player_id, my_ip):
    server = grpc.aio.server()
    servicer = GameNodeServicer(player_id, my_ip)
    
    game_pb2_grpc.add_GameNodeServicer_to_server(servicer, server)

    assigned_port = server.add_insecure_port('0.0.0.0:0')
    servicer.port = assigned_port

    await server.start()
    print(f"gRPC server automatically assigned to port {assigned_port}.")
    return server, servicer, assigned_port