import grpc
from proto import game_pb2
from proto import game_pb2_grpc

async def send_store_player(target_ip, target_port, player_id, my_ip, my_port):
    target_address = f"{target_ip}:{target_port}"
    
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        
        request = game_pb2.StorePlayerRequest(
            player_id=player_id,
            ip=my_ip,
            port=my_port
        )
        
        try:
            response = await stub.StorePlayer(request, timeout=5)
            return response
        except grpc.RpcError as e:
            print(f"Failed to register on node {target_address}: {e.details()}")
            return None

async def send_chat(target_ip, target_port, sender_id, text):
    target_address = f"{target_ip}:{target_port}"
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        request = game_pb2.ChatMessage(sender_id=sender_id, text=text)
        try:
            return await stub.Chat(request, timeout=5)
        except grpc.RpcError:
            return None

async def send_attack(target_ip, target_port, attacker_id, weapon, damage):
    target_address = f"{target_ip}:{target_port}"
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        request = game_pb2.AttackRequest(attacker_id=attacker_id, weapon=weapon, damage=damage)
        try:
            return await stub.Attack(request, timeout=5)
        except grpc.RpcError:
            return None



async def send_find_player(target_ip, target_port, target_player_id):
    target_address = f"{target_ip}:{target_port}"
    
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        
        request = game_pb2.FindPlayerRequest(target_player_id=target_player_id)
        
        try:
            response = await stub.FindPlayer(request, timeout=5)
            return response
        except grpc.RpcError as e:
            print(f"Failed to find player for {target_address}: {e.details()}")
            return None
        
async def send_leave(target_ip, target_port, player_id):
    async with grpc.aio.insecure_channel(f"{target_ip}:{target_port}") as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        try:
            return await stub.LeaveNetwork(game_pb2.LeaveRequest(player_id=player_id), timeout=5)
        except grpc.RpcError:
            return None