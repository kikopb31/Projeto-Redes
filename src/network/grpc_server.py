import grpc
import asyncio

from proto import game_pb2
from proto import game_pb2_grpc

class GameNodeServicer(game_pb2_grpc.GameNodeServicer):
    def __init__(self, player_id):
        self.plaer_id = player_id
        self.hp = 100

        self.hp_lock = asyncio.Lock()

    async def Attack(self, request, context):
        async with self.hp_lock:
            self.hp -= request.damage

            print(f"\n OUCH!!! You have been attacked by {request.attacker_id} with {request.weapon}! {request.damage} damage points taken!")
            print(f"Current HP : {self.hp}")

            if self.hp <= 0:
                print("\n You have been eliminated! X-X")
        return game_pb2.ActionResponse(
            success = True,
            status_message=f"Attack towards {self.player_id} successful! Remaining HP: {self.hp}"
        )
    
    # !!! Falta : receber msg Chat, Find e Store Player e start server