import grpc
import asyncio

import hashlib         

from proto import game_pb2
from proto import game_pb2_grpc

# função para definir distancia entre nodes
def xor_distance(id1: str, id2: str) -> int:     
    h1 = int(hashlib.sha1(id1.encode()).hexdigest(), 16)
    h2 = int(hashlib.sha1(id2.encode()).hexdigest(), 16)
    return h1 ^ h2

class GameNodeServicer(game_pb2_grpc.GameNodeServicer):
    def __init__(self, player_id, port):
        self.player_id = player_id
        self.port = port
        self.hp = 100
        self.hp_lock = asyncio.Lock()
        self.dht_table = {}
        self.dht_lock = asyncio.Lock()
    
    

    async def Attack(self, request, context):
        async with self.hp_lock:

            if self.hp <= 0: # evita que um jogador morto possa ser atacado, ja esta morto
                return game_pb2.ActionResponse(
                    success=False,
                    status_message=f"{self.player_id} is already dead!"
                )


            self.hp = max(0, self.hp - request.damage) #evitar underflow de vida

            print(f"\n OUCH!!! You have been attacked by {request.attacker_id} with {request.weapon}! {request.damage} damage points taken!")
            print(f"Current HP : {self.hp}")

            died = self.hp == 0;

            if died:
                print("\n You have been eliminated! X-X")
                print("\n You can no longer attack or chat.")

        return game_pb2.ActionResponse(
            success = True,
            status_message=f"Attack towards {self.player_id} successful! Remaining HP: {self.hp}"
        )
    
    async def Chat(self, request, context):
        print(f"\n[{request.sender_id}]: {request.text}")
        return game_pb2.ActionResponse(success=True, status_message="Message delivered.")

    async def Move(self, request, context):
        print(f"\nPlayer {request.player_id} moved to {request.direction}.")
        return game_pb2.ActionResponse(success=True, status_message="Movement registred.")

    async def StorePlayer(self, request, context):
        async with self.dht_lock:
            self.dht_table[request.player_id] = {
                "ip": request.ip,
                "port": request.port
            }
            print(f"\nStored in local DHT: {request.player_id} -> {request.ip}:{request.port}")
        return game_pb2.ActionResponse(success=True, status_message="Data stored successfully.")

    async def FindPlayer(self, request, context):
        target = request.target_player_id
        
        async with self.dht_lock:
            if target == self.player_id:
                return game_pb2.FindPlayerResponse(found=True, ip="127.0.0.1", port=self.port)

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

async def start_grpc_server(player_id, port):
    server = grpc.aio.server()
    servicer = GameNodeServicer(player_id, port)
    
    game_pb2_grpc.add_GameNodeServicer_to_server(servicer, server)
    server.add_insecure_port(f'0.0.0.0:{port}')
    
    await server.start()
    print(f"gRPC server active on port {port}. P2P network started.")
    return server, servicer