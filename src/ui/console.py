import aioconsole
from network import grpc_client
from network import dht

async def start_user_interface(player_id, servicer):
    print("\n--- GAME STARTED ---")
    print("Valid commands:")
    print("  /chat <target_id> <message>")
    print("  /attack <target_id>")
    print("  /dht")
    print("  /quit")
    print("---------------------\n")

    while True:
        line = await aioconsole.ainput(f"[{player_id}] > ")
        line = line.strip()
        if not line:
            continue

        if line.startswith("/quit"):
            break

        if servicer.hp <= 0:
            print("You are dead! You can no longer perform actions.")
            continue

        elif line.startswith("/dht"):
            
            async with servicer.dht_lock:
                print(f"\n--- LOCAL DHT TABLE ({len(servicer.dht_table)} nodes) ---")
                for k, v in servicer.dht_table.items():
                    print(f"  > {k} -> {v['ip']}:{v['port']}")
                print("-----------------------------------------\n")

        elif line.startswith("/chat"):
            
            parts = line.split(" ", maxsplit=2)
            if len(parts) < 3:
                print("[ERROR] Usage: /chat <target_id> <message>")
                continue
            
            target_id, msg_text = parts[1], parts[2]
            
            print(f"Locating '{target_id}' to send message...")
            addr = await dht.iterative_find_player(target_id, servicer)
            
            if addr:
                target_ip, target_port = addr
                await grpc_client.send_chat(target_ip, target_port, player_id, msg_text)
            else:
                print(f"[ERROR] Could not send message because '{target_id}' was not found on the network.")

        elif line.startswith("/attack"):
            parts = line.split(" ")
            if len(parts) < 2:
                print("[ERROR] Usage: /attack <target_id>")
                continue
            
            target_id = parts[1]
            print(f"Locating '{target_id}' to attack...")
            addr = await dht.iterative_find_player(target_id, servicer)
            
            if addr:
                target_ip, target_port = addr
                print(f"Attacking {target_id} at {target_ip}:{target_port} with Sword...")
                
                res = await grpc_client.send_attack(target_ip, target_port, player_id, "Sword", 10)
                
                if res:
                    print(f"[REMOTE RESPONSE] {res.status_message}")
            else:
                print(f"[ERROR] The attack failed because the player '{target_id}' was not found on the network.")
        else:
            print("Invalid command. Try /chat, /attack, /dht or /quit")