import asyncio
import sys
import aioconsole

from network import grpc_server, grpc_client, dht
from ui import console

async def main():
    print("=== MULTIPLAYER TEXTUAL P2P ===")
    
    player_id = await aioconsole.ainput("Enter your Player ID: ")
    player_id = player_id.strip()
    
    action = await aioconsole.ainput("Do you want to (C)reate a new lobby or (J)oin an existing one? [C/J]: ")
    action = action.strip().upper()

    if action == 'C':
        try:
            port_str = await aioconsole.ainput("Enter your Lobby port (e.g. 50051): ")
            port = int(port_str.strip())
        except ValueError:
            print("[ERROR] Invalid port.")
            return
            
        try:
            server, servicer, actual_port = await grpc_server.start_grpc_server(player_id, port)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return
        
        print(f"\n[INFO] Your Lobby Address is: 127.0.0.1:{actual_port}")
        print("[INFO] Share this address with your friends so they can join you!\n")

    elif action == 'J':
        try:
            server, servicer, actual_port = await grpc_server.start_grpc_server(player_id, 0)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return
        
        lobby_address = await aioconsole.ainput("Enter Lobby Address to join (IP:Port): ")
        try:
            b_ip, b_port_str = lobby_address.strip().split(':')
            b_port = int(b_port_str)
        except ValueError:
            print("[ERROR] Invalid Lobby Address format. Expected format IP:Port")
            return
        
        print(f"Joining lobby at {b_ip}:{b_port}...")
        res = await grpc_client.send_store_player(b_ip, b_port, player_id, "127.0.0.1", actual_port)

        if res and res.success:
            print("Success! Stored on the network.")
            
            async with servicer.dht_lock:
                servicer.dht_table[f"Initial_Node"] = {"ip": b_ip, "port": b_port}

            print("Discovering network nodes...")
            await dht.iterative_find_player(player_id, servicer)
            async with servicer.dht_lock:
                print(f"Network discovery complete. {len(servicer.dht_table)} nodes known.")
        else:
            print("[ERROR] Could not join the lobby. Connection failed.")
            return
            
    else:
        print("Invalid choice. Exiting.")
        return

    try:
        await console.start_user_interface(player_id, servicer)
    finally:
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