import random
import aioconsole
from network import grpc_client
from network import dht

async def start_user_interface(player_id, servicer):
    print("\n--- GAME STARTED ---")
    print("Valid commands:")
    print("  /chat <target_id> <message>")
    print("  /attack <target_id> <punch|sword|fireball>")
    print("  /dht")
    print("  /quit")
    print("  /respawn")
    print("  /heal")
    print("---------------------\n")

    while True:
        line = await aioconsole.ainput(f"[{player_id} | HP:{servicer.hp}] > ")
        line = line.strip()
        if not line:
            continue

        if line.startswith("/help"):
            print("Valid commands:")
            print("  /chat <target_id> <message>")
            print("  /attack <target_id> <punch|sword|fireball>")
            print("  /dht")
            print("  /quit")
            print("  /respawn")
            print("  /heal")
            print("---------------------\n")

        elif line.startswith("/quit"):
            break

        elif line.startswith("/respawn"):
            if servicer.hp > 0:
                print("You are still alive! You can only respawn when dead.")
            else:
                async with servicer.hp_lock:
                    servicer.hp = 50
                print("You have respawned with 50 HP!")
        
        elif servicer.hp <= 0:
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
            if len(parts) < 3:
                print("[ERROR] Usage: /attack <target_id> <punch|sword|fireball>")
                continue
            target_id = parts[1]
            weapon_choice = parts[2].lower()

            weapons = {
                "punch":    {"damage": 5,  "chance": 0.90, "name": "Punch"},
                "sword":    {"damage": 10, "chance": 0.55, "name": "Sword"},
                "fireball": {"damage": 20, "chance": 0.25, "name": "Fireball"},
            }

            if weapon_choice not in weapons:
                print("[ERROR] Unknown weapon. Choose: punch, sword, fireball")
                continue

            weapon = weapons[weapon_choice]

            hit = random.random() < weapon["chance"]
            if not hit:
                print(f"You missed with {weapon['name']}!")
                continue

            addr = await dht.iterative_find_player(target_id, servicer)
            if addr:
                print(f"Attacking {target_id} with {weapon['name']}...")
                res = await grpc_client.send_attack(addr[0], addr[1], player_id, weapon["name"], weapon["damage"])
                if res:
                    print(f"[REMOTE RESPONSE] {res.status_message}")
            else:
                print(f"[ERROR] '{target_id}' not found on the network.")

        elif line.startswith("/heal"):
            async with servicer.hp_lock:
                if servicer.hp == 100:
                    print(f"Already at Full HP: {servicer.hp}")
                else:
                    servicer.hp = min(100, servicer.hp + 5)
                    print(f"Healed! Current HP: {servicer.hp}")
        else:
            print("Invalid command. /help")