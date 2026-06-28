import asyncio
import sys
import aioconsole
import socket 

from network import grpc_server, grpc_client, dht, discovery
from ui import console


def get_local_ip(target_ip="8.8.8.8", target_port=53):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target_ip, target_port))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1" 
    finally:
        s.close()
    return local_ip

async def main():
    print("=== MULTIPLAYER TEXTUAL P2P ===")
    
    # 1. Pede o player_id
    player_id = await aioconsole.ainput("Enter your Player ID: ")
    player_id = player_id.strip()
    
    my_ip = get_local_ip()
    
    # 2. Inicia o servidor e adquire a porta automaticamente
    server, servicer, my_port = await grpc_server.start_grpc_server(player_id, my_ip)
    
    # 3. Procura Lobbies na Rede Local 
    print("\nScanning local network for available lobbies...")
    lobbies = await discovery.discover_lobbies()

    # 4. Apresenta o Menu de Lobbies
    if lobbies:
        print("\nAvailable Lobbies:")
        for i, lobby in enumerate(lobbies):
            print(f"[{i + 1}] Host: {lobby['player_id']} (IP: {lobby['ip']}:{lobby['port']})")
        print(f"[{len(lobbies) + 1}] Create a new Lobby")
    else:
        print("\nNo lobbies found on the local network.")
        print("[1] Create a new Lobby")

    choice = await aioconsole.ainput("\nSelect an option: ")
    
    try:
        choice_idx = int(choice.strip()) - 1
    except ValueError:
        print("[ERROR] Invalid choice. Shutting down.")
        sys.exit(1)

    discovery_task = None
    is_host = False 

    # 5. Lógica baseada na escolha
    if lobbies and 0 <= choice_idx < len(lobbies):
        # JOIN LOBBY (Jogador Cliente)
        host = lobbies[choice_idx]
        print(f"\nRequesting access to {host['player_id']}'s lobby...")
        
        res = await grpc_client.send_join_network(host['ip'], host['port'], player_id, my_ip, my_port)
        
        if res and res.success:
            print("Access granted! Downloading DHT table from host...")
            
            async with servicer.dht_lock:
                # Guarda o Host
                servicer.dht_table[res.host_id] = {"ip": host['ip'], "port": host['port']}
                
                # Guarda os restantes jogadores enviados pelo Host
                for node in res.all_nodes:
                    servicer.dht_table[node.node_id] = {"ip": node.ip, "port": node.port}
            
            print(f"Network discovery complete. {len(servicer.dht_table)} nodes known.")
        else:
            print("Failed to join the network.")
            await server.stop(0)
            return

    else:
        # HOST LOBBY (Jogador Criador/Host)
        print("\nCreating new lobby. You are the Host of this network.")
        is_host = True  # Ativa a flag apenas para o Host

    # 6. ALTERAÇÃO CRÍTICA: Apenas o Host anuncia o lobby na LAN
    if is_host:
        discovery_task = asyncio.create_task(discovery.run_discovery_server(player_id, my_port))

    heartbeat_task = asyncio.create_task(grpc_server.monitor_heartbeats(servicer))
    # 7. Iniciar Interface
    try:
        await console.start_user_interface(player_id, servicer)
    finally:
        if discovery_task:
            discovery_task.cancel()
        if heartbeat_task:
            heartbeat_task.cancel()
        async with servicer.dht_lock:
            nodes = list(servicer.dht_table.values())
        for node in nodes:
            await grpc_client.send_leave(node["ip"], node["port"], player_id)
        await server.stop(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForcefully closed.")
        sys.exit(0)