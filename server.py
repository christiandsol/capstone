import asyncio
import random
from typing import Dict, List
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from util import send_json, parse_json

HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 10

class MafiaGame:
    def __init__(self, players: int):
        self.state = "LOBBY"
        self.expected_signals = {"setup"}
        self.player_cap = players

        self.players: Dict[str, dict] = {}  # name -> player data
        self.clients: Dict[WebSocketServerProtocol, str] = {}  # ws -> name
        self.rpis: Dict[WebSocketServerProtocol, str] = {} # name --> ws
        
        self.player_id_to_name: Dict[int, str] = {}  # player_id -> name
        self.name_to_player_id: Dict[str, int] = {}  # name -> player_id
        
        self.mafia_name = None
        self.doctor_name = None
        
        self.last_killed = None
        self.last_saved = None

    def valid_signal(self, signal):
        return signal and signal.get("action") in self.expected_signals

    def check_everyone_in_game(self):
        return len(self.players) == self.player_cap and all(p["setup"] for p in self.players.values())

    def check_heads_down(self, allowed: List[str | None]):
        for name, data in self.players.items():
            print(f"[DEBUG] Checking player {name}'s head state: {data['head']}")
            if data["alive"] and data["head"] == "up" and name not in allowed:
                return False
        return True

    async def request_action(self, name: str, action: str):
        print(f"[DEBUG] NAME: {name}")
        ws = self.rpis[name]
        await send_json(ws, name, action, None)

    def id_to_name(self, player_id: int) -> str | None:
        """Convert a player ID to player name"""
        return self.player_id_to_name.get(player_id)

    def name_to_id(self, name: str) -> int | None:
        """Convert a player name to player ID"""
        return self.name_to_player_id.get(name)

    def mafia_kill(self):
        if self.mafia_name and self.players[self.mafia_name]["kill"]:
            kill = self.players[self.mafia_name]["kill"]
            self.players[self.mafia_name]["kill"] = None
            return kill
        return None

    def doctor_save(self):
        if self.doctor_name and self.players[self.doctor_name]["save"]:
            save = self.players[self.doctor_name]["save"]
            self.players[self.doctor_name]["save"] = None
            return save
        return None

    def everyone_voted(self):
        for name, data in self.players.items():
            if data["alive"] and data["vote"] is None:
                return False
        return True

    def handle_vote(self):
        votes = {}
        for name, data in self.players.items():
            if data["alive"] and data["vote"]:
                votes[data["vote"]] = votes.get(data["vote"], 0) + 1

        if not votes:
            return []

        max_votes = max(votes.values())
        winners = [name for name, count in votes.items() if count == max_votes]

        # Clear votes
        for data in self.players.values():
            data["vote"] = None

        return winners

    async def broadcast(self, action, target=None):
        for ws, name in self.clients.items():
            await send_json(ws, name, action, target)

    async def broadcast_vote(self):
        for name in self.rpis:
            await self.request_action(name, "vote")

    async def assign_player(self):
        for ws, name in self.clients.items():
            role = "civilian"
            if name == self.mafia_name:
                role = "mafia"
            elif name == self.doctor_name:
                role = "doctor"
            await send_json(ws, name, role, None)
        for name, ws in self.rpis.items():
            role = "civilian"
            if name == self.mafia_name:
                role = "mafia"
            elif name == self.doctor_name:
                role = "doctor"
            await send_json(ws, name, role, None)


    async def update(self):
        if self.state == "LOBBY" and self.check_everyone_in_game():
            print("All players connected")
            # Assign roles randomly
            player_names = list(self.players.keys())
            if len(player_names) >= 2:
                self.mafia_name, self.doctor_name = random.sample(player_names, 2)
            self.state = "ASSIGN"
            self.expected_signals = set()

        if self.state == "ASSIGN":
            await self.assign_player()
                
            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("Moving on to mafia stage, everyone put head down please")

        if self.state == "HEADSDOWN" and self.check_heads_down([]):
            self.state = "MAFIAVOTE"
            self.expected_signals = {"headUp", "headDown", "targeted"}
            print("MOVING ON TO MAFIA VOTE STAGE")
            await self.request_action(self.mafia_name, "kill")

        if self.state == "MAFIAVOTE":
            if self.check_heads_down([self.mafia_name]):
                kill = self.mafia_kill()
                if kill:
                    self.last_killed = kill
                    self.players[kill]["alive"] = False
                    self.state = "DOCTORVOTE" if self.doctor_name else "NARRATE"
                    if self.state == "DOCTORVOTE":
                        await self.request_action(self.doctor_name, "save")

        if self.state == "DOCTORVOTE":
            if self.check_heads_down([self.doctor_name]):
                save = self.doctor_save()
                if save:
                    self.last_saved = save
                    self.players[save]["alive"] = True
                    self.state = "NARRATE"

        if self.state == "NARRATE":
            await self.broadcast("night_result", {
                "killed": self.last_killed,
                "saved": self.last_saved
            })
            self.state = "VOTE"
            self.expected_signals = {"targeted"}
            await self.broadcast_vote()

        if self.state == "VOTE" and self.everyone_voted():
            voted_out = self.handle_vote()
            if len(voted_out) != 1:
                print(f"[DEBUG] voted tied between {[player for player in voted_out]}")
                await self.broadcast("vote_result_tie", voted_out)
                await self.broadcast_vote()
                return 
            await self.broadcast("vote_result", voted_out)
            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}


# ------------------ SERVER ------------------

game = MafiaGame(3)
lock = asyncio.Lock()


async def handler(ws: WebSocketServerProtocol):
    player_name = None
    
    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            
            # Handle setup message
            if msg.get("action") == "setup":
                player_name = msg.get("target")
                if player_name == "rpi":
                    player_name = msg.get("name")
                    print(f"[DEBUG] server adding rpi: {player_name}")
                    game.rpis[player_name] = ws
                    continue
                print(f"[DEBUG] server adding player: {player_name}")
                
                # Move lock inside the loop, not outside
                async with lock:
                    if player_name in game.players:
                        print(f"[DEBUG] Name {player_name} already taken")
                        await ws.close(1008, "Name already taken")
                        return
                    
                    if len(game.players) >= game.player_cap:
                        print(f"[DEBUG] Game is full")
                        await ws.close(1008, "Game is full")
                        return

                    player_id = len(game.players) + 1
                    game.player_id_to_name[player_id] = player_name
                    game.name_to_player_id[player_name] = player_id

                    # Register player
                    game.clients[ws] = player_name
                    game.players[player_name] = {
                        "setup": True,
                        "head": "up",
                        "vote": None,
                        "kill": None,
                        "save": None,
                        "alive": True
                    }
                
                # Send confirmation
                await send_json(ws, player_id, "id_registered", None)
                print(f"[DEBUG] Player {player_name} registered successfully with ID {player_id}")
                
                # Trigger game update
                await game.update()
                continue
            
            # Handle other game signals
            if player_name and game.valid_signal(msg):
                action = msg["action"]
                
                async with lock:
                    if player_name not in game.players:
                        continue
                    
                    player_data = game.players[player_name]
                    
                    if action == "headUp":
                        player_data["head"] = "up"
                    elif action == "headDown":
                        player_data["head"] = "down"
                    elif action == "targeted":
                        target = msg.get("target")
                        print(f"[DEBUG], recieved target signal with target: {target}, of type: {type(target)}")

                        if target.isnumeric():
                            target = int(target)
                            target = game.id_to_name(target)
                            if target is None:
                                print(f"[DEBUG] Invalid player ID received: {msg.get('target')}")
                                continue
                        
                        if player_name == game.mafia_name and game.state == "MAFIAVOTE":
                            player_data["kill"] = target
                        elif player_name == game.doctor_name and game.state == "DOCTORVOTE":
                            player_data["save"] = target
                        else:
                            player_data["vote"] = target

                await game.update()

    except websockets.exceptions.ConnectionClosedError:
        print(f"[DEBUG] Connection closed unexpectedly for player: {player_name}")
    except Exception as e:
        print(f"[ERROR] Handler error for {player_name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if player_name:
            print(f"[DEBUG] Cleaning up player {player_name}")
            async with lock:
                if ws in game.clients:
                    del game.clients[ws]
                if player_name in game.players:
                    player_id = game.name_to_player_id.get(player_name)
                    if player_id is not None:
                        del game.player_id_to_name[player_id]
                        del game.name_to_player_id[player_name]
                    del game.players[player_name]
            print(f"[DEBUG] Player {player_name} removed from game")

async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"WebSocket server running on {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
