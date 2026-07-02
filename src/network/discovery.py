# discovery.py
import asyncio
import socket
import json

BROADCAST_PORT = 9999

async def discover_lobbies(timeout=2.0):
    """Envia um broadcast UDP e escuta por respostas de Lobbies."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', 0)) 
    sock.setblocking(False)

    # Broadcast
    msg = b"DISCOVER_LOBBIES"
    await loop.sock_sendto(sock, msg, ('255.255.255.255', BROADCAST_PORT))

    lobbies = []
    end_time = loop.time() + timeout

    try:
        while True:
            time_left = end_time - loop.time()
            if time_left <= 0:
                break
            try:
                data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 1024), timeout=time_left)
                lobby_info = json.loads(data.decode())
                lobby_info['ip'] = addr[0]
                lobbies.append(lobby_info)
            except asyncio.TimeoutError:
                break
            except Exception:
                pass
    finally:
        sock.close()
    
    return lobbies

async def run_discovery_server(player_id, grpc_port):
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', BROADCAST_PORT))
    sock.setblocking(False)

    print("[Discovery] Listening for new players on the local network...")
    try:
        while True:
            data, addr = await loop.sock_recvfrom(sock, 1024)
            if data == b"DISCOVER_LOBBIES":
                response = json.dumps({"player_id": player_id, "port": grpc_port})
                await loop.sock_sendto(sock, response.encode(), addr)
    except asyncio.CancelledError:
        sock.close()