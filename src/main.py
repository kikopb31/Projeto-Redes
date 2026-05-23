import asyncio
import sys
import aioconsole

from network import grpc_server, grpc_client
from ui import console

async def main():
    print("=== MULTIPLAYER TEXTUAL P2P ===")
    
    player_id = await aioconsole.ainput("Enter your Player ID: ")
    player_id = player_id.strip()
    
    try:
        port_str = await aioconsole.ainput("Enter your gRPC port: ")
        port = int(port_str.strip())
    except ValueError:
        print("[ERROR] Invalid port.")
        return
    server, servicer = await grpc_server.start_grpc_server(player_id, port)
    bootstrap = await aioconsole.ainput("\nDo you want to connect to a known node? (y/n): ")
    if bootstrap.strip().lower() == 'y':
        b_ip = await aioconsole.ainput("Known node IP: ")
        b_port = int(await aioconsole.ainput("Known node port: "))
        
        print(f"Registering on bootstrap node {b_ip}:{b_port}...")
        res = await grpc_client.send_store_player(b_ip, b_port, player_id, "127.0.0.1", port)
        
        if res and res.success:
            print("Success! Stored on the network.")
            async with servicer.dht_lock:
                servicer.dht_table["Initial_Node"] = {"ip": b_ip, "port": b_port}
    try:
        await console.start_user_interface(player_id, servicer)
    finally:
        print("\nShutting down gRPC server...")
        await server.stop(0)
        print("Terminated.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForcefully closed.")
        sys.exit(0)