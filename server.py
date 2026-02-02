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
            if data["alive"] and data["head"] == "up" and name not in allowed:
                return False
        return True

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
            for ws, name in self.clients.items():
                role = "civilian"
                if name == self.mafia_name:
                    role = "mafia"
                elif name == self.doctor_name:
                    role = "doctor"
                await send_json(ws, name, role, None)

            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("Moving on to mafia stage, everyone put head down please")

        if self.state == "HEADSDOWN" and self.check_heads_down([]):
            self.state = "MAFIAVOTE"
            self.expected_signals = {"headUp", "headDown", "targeted"}
            print("MOVING ON TO MAFIA VOTE STAGE")

        if self.state == "MAFIAVOTE":
            if self.check_heads_down([self.mafia_name]):
                kill = self.mafia_kill()
                if kill:
                    self.last_killed = kill
                    self.players[kill]["alive"] = False
                    self.state = "DOCTORVOTE" if self.doctor_name else "NARRATE"

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

        if self.state == "VOTE" and self.everyone_voted():
            voted_out = self.handle_vote()
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
                    print(f"[DEBUG] server adding rpi: {player_name}")
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

                    # Register player
                    game.clients[ws] = player_name
                    game.players[player_name] = {
                        "setup": True,
                        "head": None,
                        "vote": None,
                        "kill": None,
                        "save": None,
                        "alive": True
                    }
                
                # Send confirmation
                await send_json(ws, player_name, "player_registered", None)
                print(f"[DEBUG] Player {player_name} registered successfully")
                
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
                    del game.players[player_name]
            print(f"[DEBUG] Player {player_name} removed from game")

async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"WebSocket server running on {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
