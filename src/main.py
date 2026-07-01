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
    player_id = await aioconsole.ainput("Enter your Player ID: ")
    player_id = player_id.strip()
    my_ip = get_local_ip()

    server, servicer, my_port = await grpc_server.start_grpc_server(player_id, my_ip)

    print("\nScanning local network for available lobbies...")
    lobbies = await discovery.discover_lobbies()

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

    if lobbies and 0 <= choice_idx < len(lobbies):
        host = lobbies[choice_idx]
        print(f"\nRequesting access to {host['player_id']}'s lobby...")
        
        res = await grpc_client.send_join_network(host['ip'], host['port'], player_id, my_ip, my_port)
        
        if res and res.success:
            print("Access granted! Downloading DHT table from host...")
            
            async with servicer.dht_lock:
                servicer.host_id = res.host_id
                servicer.host_ip = host['ip']
                servicer.host_port = host['port']         
                servicer.dht_table[res.host_id] = {"ip": host['ip'], "port": host['port']}

                servicer.lobby_nodes = [res.host_id]

                for node in res.all_nodes:
                    servicer.dht_table[node.node_id] = {"ip": node.ip, "port": node.port}
                    servicer.lobby_nodes.append(node.node_id)
                
                servicer.lobby_nodes.append(player_id)
            
            print(f"Network discovery complete. {len(servicer.dht_table)} nodes known.")
        else:
            print("Failed to join the network.")
            await server.stop(0)
            return

    else:
        print("\nCreating new lobby. You are the Host of this network.")
        is_host = True
        servicer.is_host = True
        servicer.host_id = player_id

    if is_host:
        discovery_task = asyncio.create_task(discovery.run_discovery_server(player_id, my_port))

    heartbeat_task = asyncio.create_task(grpc_server.monitor_heartbeats(servicer))
    
    try:
        await console.start_user_interface(player_id, servicer)
    finally:
        if discovery_task:
            discovery_task.cancel()
        if heartbeat_task:
            heartbeat_task.cancel()
        
        async with servicer.dht_lock:
            dht_items = list(servicer.dht_table.items())
        
        if is_host and len(dht_items) > 0:
            next_host_id, next_host_info = dht_items[0] 

            await grpc_client.send_promote_to_host(
                next_host_info["ip"],
                next_host_info["port"],
                next_host_id,  
                next_host_info["ip"],
                next_host_info["port"]
            )
            
            for nid, ninfo in dht_items[1:]:
                asyncio.create_task(
                    grpc_client.send_host_disconnected(
                        ninfo["ip"],
                        ninfo["port"],
                        player_id,
                        next_host_id,
                        next_host_info["ip"],
                        next_host_info["port"],
                        {k: v for k, v in servicer.dht_table.items() if k != player_id}
                    )
                )
        else:
            for nid, ninfo in dht_items:
                try:
                    await grpc_client.send_leave(ninfo["ip"], ninfo["port"], player_id)
                except Exception:
                    pass
        
        await server.stop(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForcefully closed.")
        sys.exit(0)