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
        

async def send_join_network(target_ip, target_port, player_id, my_ip, my_port):
    target_address = f"{target_ip}:{target_port}"
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        request = game_pb2.JoinRequest(
            player_id=player_id,
            ip=my_ip,
            port=my_port
        )
        try:
            response = await stub.JoinNetwork(request, timeout=5)
            return response
        except grpc.RpcError as e:
            print(f"Failed to join lobby at {target_address}: {e.details()}")
            return None


async def send_ping(target_ip, target_port, sender_id):
    target_address = f"{target_ip}:{target_port}"

    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        request = game_pb2.PingRequest(sender_id=sender_id)
        try:
            response = await stub.Ping(request, timeout=2)
            return response
        except grpc.RpcError:
            return None
        except Exception as e:
            return None

async def send_host_disconnected(target_ip, target_port, old_host_id, new_host_id, new_host_ip, new_host_port, all_nodes):
    target_address = f"{target_ip}:{target_port}"
    
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        
        node_contacts = [
            game_pb2.NodeContact(node_id=nid, ip=info["ip"], port=info["port"])
            for nid, info in all_nodes.items()
        ]
        
        request = game_pb2.HostDisconnectRequest(
            old_host_id=old_host_id,
            new_host_id=new_host_id,
            new_host_ip=new_host_ip,
            new_host_port=new_host_port,
            all_nodes=node_contacts
        )
        
        try:
            response = await stub.HostDisconnected(request, timeout=5)
            return response
        except grpc.RpcError:
            return None

async def send_promote_to_host(target_ip, target_port, new_host_id, new_host_ip, new_host_port):
    target_address = f"{target_ip}:{target_port}"
    
    async with grpc.aio.insecure_channel(target_address) as channel:
        stub = game_pb2_grpc.GameNodeStub(channel)
        
        request = game_pb2.PromoteToHostRequest(
            new_host_id=new_host_id,
            new_host_ip=new_host_ip,
            new_host_port=new_host_port
        )
        
        try:
            response = await stub.PromoteToHost(request, timeout=5)
            return response
        except grpc.RpcError:
            return None