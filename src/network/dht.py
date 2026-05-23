import asyncio
from network import grpc_client

async def iterative_find_player(target_id, servicer):
    async with servicer.dht_lock:
        if target_id in servicer.dht_table:
            return servicer.dht_table[target_id]["ip"], servicer.dht_table[target_id]["port"]
        
        nodes_to_ask = list(servicer.dht_table.values())

    if not nodes_to_ask:
        print("Search impossible. You don't know any nodes in the network.")
        return None

    visited_nodes = set()
    while nodes_to_ask:
        current_node = nodes_to_ask.pop(0)
        node_key = f"{current_node['ip']}:{current_node['port']}"
        
        if node_key in visited_nodes:
            continue
        visited_nodes.add(node_key)

        print(f"Asking {node_key} about the whereabouts of '{target_id}'...")
        response = await grpc_client.send_find_player(current_node["ip"], current_node["port"], target_id)
        
        if response:
            if response.found:
                print(f"Success! '{target_id}' was found at {response.ip}:{response.port}")

                async with servicer.dht_lock:
                    servicer.dht_table[target_id] = {"ip": response.ip, "port": response.port}
                
                return response.ip, response.port
            
            else:
                print(f"Node {node_key} does not know the target, but suggested {len(response.closest_nodes)} closer nodes.")
                for contact in response.closest_nodes:
                    if contact.node_id == servicer.player_id:
                        continue
                        
                    new_contact = {"ip": contact.ip, "port": contact.port}
                    contact_key = f"{contact.ip}:{contact.port}"
                    
                    if contact_key not in visited_nodes:
                        nodes_to_ask.append(new_contact)
                        async with servicer.dht_lock:
                            if contact.node_id not in servicer.dht_table:
                                servicer.dht_table[contact.node_id] = new_contact

    print(f"Search finished. Player '{target_id}' was not found on the network.")
    return None