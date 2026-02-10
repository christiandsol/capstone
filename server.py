import asyncio
import random
from typing import Dict, List
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from util import send_json, parse_json

HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 8

class MafiaGame:
    
    async def broadcast_status(self, message: str):
        # Send a status message to all players
        for ws, name in self.clients.items():
            await send_json(ws, name, "status", message)
    def __init__(self):
        self.state = "LOBBY"
        self.expected_signals = {"setup"}
        self.max_players = MAX_PLAYERS

        self.players: Dict[str, dict] = {}  # name -> player data
        self.clients: Dict[WebSocketServerProtocol, str] = {}  # ws -> name
        self.rpis: Dict[WebSocketServerProtocol, str] = {} # name --> ws
        
        self.player_id_to_name: Dict[int, str] = {}  # player_id -> name
        self.name_to_player_id: Dict[str, int] = {}  # name -> player_id
        
        self.mafia_name_one = None
        self.mafia_name_two = None
        self.doctor_name_one = None
        self.doctor_name_two = None
        
        self.last_killed = None
        self.last_saved = None
        self.mafia_count = None
        self.doctor_count = None
        self.game_winner = None
        self.pending_code = -1

    def valid_signal(self, signal):
        return signal and signal.get("action") in self.expected_signals

    def check_everyone_ready(self):
        """Check if all players are ready to start (minimum 3 players)"""
        if len(self.players) < 3:
            return False
        return all(p["ready"] for p in self.players.values())
    
    def check_everyone_wants_restart(self):
        """Check if all players want to restart"""
        if len(self.players) == 0:
            return False
        return all(p["restart"] for p in self.players.values())

    def check_game_over(self):
        """Check if game is over and determine winner"""
        alive_players = [name for name, data in self.players.items() if data["alive"]]
        
        # Check if any mafia are alive
        mafia_alive = self.is_alive(self.mafia_name_one) or self.is_alive(self.mafia_name_two)
        # If no mafia alive, civilians win
        if not mafia_alive:
            return "civilians"
        
        # Count alive civilians (non-mafia)
        alive_civilians = len([name for name in alive_players 
                              if name != self.mafia_name_one and name != self.mafia_name_two])
        
        # If mafia >= civilians, mafia wins
        alive_mafia_count = sum([
            1 if self.is_alive(self.mafia_name_one) else 0,
            1 if self.is_alive(self.mafia_name_two) else 0
        ])
        
        if alive_mafia_count >= alive_civilians:
            return "mafia"
        
        return None  # Game continues

    def reset_game_state(self):
        """Reset game state for a new round while keeping players"""
        print("[DEBUG] Resetting game state for new round...")
        
        # Reset all player states
        for player_data in self.players.values():
            player_data["ready"] = True
            player_data["restart"] = False
            player_data["voiceCommand"] = False
            player_data["head"] = "up"
            player_data["vote"] = None
            player_data["kill"] = None
            player_data["save"] = None
            player_data["alive"] = True
        
        # Reset game variables
        self.mafia_name_one = None
        self.mafia_name_two = None
        self.doctor_name_one = None
        self.doctor_name_two = None
        self.last_killed = None
        self.last_saved = None
        self.mafia_count = None
        self.doctor_count = None
        self.game_winner = None
        self.pending_code = -1
        
        # Back to lobby
        self.state = "LOBBY"
        self.expected_signals = {"setup"}
        
        print("[DEBUG] Game state reset complete")

    def check_heads_down(self, allowed: List[str | None]):
        for name, data in self.players.items():
            print(f"[DEBUG] Checking player {name}'s head state: {data['head']}")
            if data["alive"] and data["head"] == "up" and name not in allowed:
                print("[DEBUG] CHECKING HEAD DOWN RETURNING FALSE")
                return False
        return True

    async def request_action(self, name: str, action: str):
        print(f"[DEBUG] NAME: {name}")
        if name == None:
            return
        ws = self.rpis.get(name)
        if ws:
            await send_json(ws, name, action, None)

    def id_to_name(self, player_id: int) -> str | None:
        """Convert a player ID to player name"""
        return self.player_id_to_name.get(player_id)

    def name_to_id(self, name: str) -> int | None:
        """Convert a player name to player ID"""
        return self.name_to_player_id.get(name)

    def mafia_kill(self):
        if self.mafia_count == 1:
            print(f"[DEBUG] pick something")
            if self.is_alive(self.mafia_name_one) and self.players[self.mafia_name_one]["kill"]:
                kill = self.players[self.mafia_name_one]["kill"]
                self.players[self.mafia_name_one]["kill"] = None
                return kill
            elif self.is_alive(self.mafia_name_two) and self.players[self.mafia_name_two]["kill"]:
                    kill = self.players[self.mafia_name_two]["kill"]
                    self.players[self.mafia_name_two]["kill"] = None
                    return kill
            return None
        elif self.mafia_count == 2:
            if self.is_alive(self.mafia_name_one) and self.players[self.mafia_name_one]["kill"] and self.is_alive(self.mafia_name_two) and self.players[self.mafia_name_two]["kill"]:
                if self.players[self.mafia_name_one]["kill"] == self.players[self.mafia_name_two]["kill"]:
                    kill = self.players[self.mafia_name_one]["kill"]
                    self.players[self.mafia_name_one]["kill"] = None
                    self.players[self.mafia_name_two]["kill"] = None
                    return kill
            return None

    def doctor_save(self):
        if self.doctor_count == 1:
            if self.is_alive(self.doctor_name_one) and self.players[self.doctor_name_one]["save"]:
                save = self.players[self.doctor_name_one]["save"]
                self.players[self.doctor_name_one]["save"] = None
                return save
            elif self.is_alive(self.doctor_name_two) and self.players[self.doctor_name_two]["save"]:
                save = self.players[self.doctor_name_two]["save"]
                self.players[self.doctor_name_two]["save"] = None
                return save
            return None
        elif self.doctor_count == 2:
            if self.is_alive(self.doctor_name_one) and self.players[self.doctor_name_one]["save"] and self.is_alive(self.doctor_name_two) and self.players[self.doctor_name_two]["save"]:
                if self.players[self.doctor_name_one]["save"] == self.players[self.doctor_name_two]["save"]:
                    save = self.players[self.doctor_name_one]["save"]
                    self.players[self.doctor_name_one]["save"] = None
                    self.players[self.doctor_name_two]["save"] = None
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

    def check_role_counts(self):
        if self.mafia_count == 2:
            if self.is_alive(self.mafia_name_one) == False or self.is_alive(self.mafia_name_two) == False:
                self.mafia_count = 1
        if self.doctor_count == 2:
            if self.is_alive(self.doctor_name_one) == False or self.is_alive(self.doctor_name_two) == False:
                self.doctor_count = 1

    def is_alive(self, name: str | None) -> bool:
        return bool(name) and name in self.players and self.players[name].get("alive")

    async def broadcast(self, action, target=None):
        for ws, name in self.clients.items():
            await send_json(ws, name, action, target)

    async def broadcast_lobby_status(self):
        """Broadcast current lobby status to all players"""
        ready_count = sum(1 for p in self.players.values() if p["ready"])
        total_count = len(self.players)
        for ws, name in self.clients.items():
            await send_json(ws, name, "lobby_status", {
                "ready_count": ready_count,
                "total_count": total_count,
                "min_players": 3,
                "max_players": self.max_players,
                "players": {
                    pname: pdata["ready"] 
                    for pname, pdata in self.players.items()
                }
            })
    
    async def broadcast_restart_status(self):
        """Broadcast restart status to all players"""
        restart_count = sum(1 for p in self.players.values() if p["restart"])
        total_count = len(self.players)
        
        for ws, name in self.clients.items():
            await send_json(ws, name, "restart_status", {
                "restart_count": restart_count,
                "total_count": total_count,
                "players": {
                    pname: pdata["restart"] 
                    for pname, pdata in self.players.items()
                }
            })

    async def broadcast_vote(self):
        for name in self.rpis:
            await self.request_action(name, "vote")

    async def broadcast_game_end(self, winner: str):
        for ws, name in self.clients.items():
            await send_json(ws, name, winner, None)

    async def assign_player(self):
        if self.mafia_count == 2:
            for ws, name in self.clients.items():
                role = "civilian"
                if name == self.mafia_name_one or name == self.mafia_name_two:
                    role = "mafia"
                elif name == self.doctor_name_one or name == self.doctor_name_two:
                    role = "doctor"
                await send_json(ws, name, role, None)
            for name, ws in self.rpis.items():
                role = "civilian"
                if name == self.mafia_name_one or name == self.mafia_name_two:
                    role = "mafia"
                elif name == self.doctor_name_one or name == self.doctor_name_two:
                    role = "doctor"
                await send_json(ws, name, role, None)
        else:
            for ws, name in self.clients.items():
                role = "civilian"
                if name == self.mafia_name_one:
                    role = "mafia"
                elif name == self.doctor_name_one:
                    role = "doctor"
                await send_json(ws, name, role, None)
            for name, ws in self.rpis.items():
                role = "civilian"
                if name == self.mafia_name_one:
                    role = "mafia"
                elif name == self.doctor_name_one:
                    role = "doctor"
                await send_json(ws, name, role, None)

    async def update(self):
        state_before = self.state
        
        if self.state == "LOBBY" and self.check_everyone_ready():
            print(f"[DEBUG] All {len(self.players)} players ready! Starting game...")
            await self.broadcast_status(f"All {len(self.players)} players ready! Starting game...")
            if self.pending_code == 2:
                self.pending_code = -1
                # Assign roles randomly based on player count
                player_names = list(self.players.keys())
                num_players = len(player_names)
            
                if num_players >= 7:
                    self.mafia_count = 2
                    self.doctor_count = 2
                    self.mafia_name_one, self.mafia_name_two, self.doctor_name_one, self.doctor_name_two = random.sample(player_names, 4)
                else:
                    self.mafia_count = 1
                    self.doctor_count = 1
                    self.mafia_name_one, self.doctor_name_one = random.sample(player_names, 2)
                
                print(f"[DEBUG] Assigned roles: Mafia={self.mafia_count}, Doctor={self.doctor_count}")
                await self.broadcast_status(f"Assigned roles: Mafia={self.mafia_count}, Doctor={self.doctor_count}")

                self.state = "ASSIGN"
                self.expected_signals = set()

        if self.state == "ASSIGN":
            await self.assign_player()
            await self.broadcast("heads_down", None)
            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("Moving on to mafia stage, everyone put head down please")
            await self.broadcast_status("Moving on to mafia stage, everyone put head down please")

# and self.check_heads_down([])
        if self.state == "HEADSDOWN":
            self.state = "MAFIAVOTE"
            self.expected_signals = {"headUp", "headDown", "targeted"}
            print("MOVING ON TO MAFIA VOTE STAGE")
            await self.broadcast_status("MOVING ON TO MAFIA VOTE STAGE")
            if self.mafia_count == 1:
                if self.players[self.mafia_name_one]["alive"] == True:
                    await self.request_action(self.mafia_name_one, "kill")
                    return
                elif self.players[self.mafia_name_two]["alive"] == True and self.mafia_name_two != None:
                    await self.request_action(self.mafia_name_two, "kill")
                    return
            elif self.mafia_count == 2:
                await asyncio.gather(
                    self.request_action(self.mafia_name_one, "kill"), 
                    self.request_action(self.mafia_name_two, "kill")
                )
                return
                
        if self.state == "MAFIAVOTE":
 #           if self.check_heads_down([self.mafia_name_one, self.mafia_name_two]):
                kill = self.mafia_kill()
                if kill == None and self.mafia_count == 2 and self.players[self.mafia_name_one]["kill"] != None and self.players[self.mafia_name_two]["kill"] != None:
                    print(f"[DEBUG] voted for diff people, try again")
                    await self.broadcast_status("Mafia voted for different people, try again.")

                    self.players[self.mafia_name_one]["kill"] = None
                    self.players[self.mafia_name_two]["kill"] = None
                    await asyncio.gather(
                    self.request_action(self.mafia_name_one, "kill"), 
                    self.request_action(self.mafia_name_two, "kill")
                    )
                    return
                if kill != None:
                    print(f"[DEBUG] kill successful")      
                    self.last_killed = kill
                    self.state = "DOCTORVOTE" if (self.players[self.doctor_name_one]["alive"] or (self.doctor_name_two != None and self.players[self.doctor_name_two]["alive"])) else "NARRATE"
                    if self.state == "DOCTORVOTE":
                        if self.doctor_count == 1:
                            if self.players[self.doctor_name_one]["alive"] == True:
                                await self.request_action(self.doctor_name_one, "save")
                                return
                            elif self.players[self.doctor_name_two]["alive"] == True and self.doctor_name_two != None:
                                await self.request_action(self.doctor_name_two, "save")
                                return
                        elif self.doctor_count == 2:
                            await asyncio.gather(
                                self.request_action(self.doctor_name_one, "save"), 
                                self.request_action(self.doctor_name_two, "save")
                            )
                            return

        if self.state == "DOCTORVOTE":
 #           if self.check_heads_down([self.doctor_name_one, self.doctor_name_two]):
                save = self.doctor_save()
                if save == None and self.doctor_count == 2 and self.players[self.doctor_name_one]["save"] != None and self.players[self.doctor_name_two]["save"] != None:
                    print(f"[DEBUG] voted for diff people, try again")
                    await self.broadcast_status("Doctor voted for different people, try again.")
                    self.players[self.doctor_name_one]["save"] = None
                    self.players[self.doctor_name_two]["save"] = None
                    await asyncio.gather(
                    self.request_action(self.doctor_name_one, "save"), 
                    self.request_action(self.doctor_name_two, "save")
                    )
                    return
                if save != None:
                    self.last_saved = save
                    if self.last_saved != self.last_killed:
                        print(f"[DEBUG] save failed")
                        await self.broadcast_status("Doctor save failed.")
                        self.players[self.last_killed]["alive"] = False
                        self.check_role_counts()
                    self.state = "NARRATE"

        if self.state == "NARRATE":
            print("[DEBUG] Narrating night results...")
            await self.broadcast_status("Narrating night results...")
            await self.broadcast("night_result", {
                "killed": self.last_killed,
                "saved": self.last_saved
            })
            self.last_saved = None
            self.last_killed = None
            # Check if game is over after night
            winner = self.check_game_over()
            if winner:
                self.game_winner = winner
                self.state = "GAMEOVER"
                self.expected_signals = set()
                await self.broadcast("game_over", {
                    "winner": winner,
                    "mafia": [self.mafia_name_one, self.mafia_name_two] if self.mafia_count == 2 else [self.mafia_name_one]
                })
                await self.broadcast_restart_status()
                return
            
            self.state = "PREVOTE"
            self.expected_signals = {"targeted"}
            print("[DEBUG] Moving to day voting stage")
            await self.broadcast_status("Moving to day voting stage.")

        if self.state == "PREVOTE":
            if self.pending_code == 3:
                self.pending_code = -1
                self.state = "VOTE"
                await self.broadcast_vote()

        if self.state == "VOTE" and self.everyone_voted():
            voted_out = self.handle_vote()
            if len(voted_out) != 1:
                print(f"[DEBUG] Vote tied between {[player for player in voted_out]}")
                await self.broadcast_status(f"Vote tied between {[player for player in voted_out]}")
                await self.broadcast("vote_result_tie", voted_out)
                self.state = "HEADSDOWN"
                self.expected_signals = {"headUp", "headDown"}
                print("[DEBUG] Moving back to night phase")
                await self.broadcast_status("Moving back to night phase.")
                await self.broadcast("heads_down", None)
                return
            
            print(f"[DEBUG] Player voted out: {voted_out[0]}")
            await self.broadcast_status(f"Player voted out: {voted_out[0]}")
            self.players[voted_out[0]]["alive"] = False
            self.check_role_counts()
            await self.broadcast("vote_result", voted_out)
            
            # Check if game is over after vote
            winner = self.check_game_over()
            if winner:
                self.game_winner = winner
                self.state = "GAMEOVER"
                self.expected_signals = set()
                await self.broadcast("game_over", {
                    "winner": winner,
                    "mafia": [self.mafia_name_one, self.mafia_name_two] if len(self.players) >= 7 else [self.mafia_name_one]
                })
                await self.broadcast_restart_status()
                return
            
            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("[DEBUG] Moving back to night phase")
            await self.broadcast_status("Moving back to night phase.")
            await self.broadcast("heads_down", voted_out)
            
        if self.state == "GAMEOVER" and self.check_everyone_wants_restart():
            print("[DEBUG] All players want to restart! Restarting game...")
            await self.broadcast_status("All players want to restart! Restarting game...")
            self.reset_game_state()
            await self.broadcast_lobby_status()
        
        # If state changed, recursively call update to continue processing
        if self.state != state_before:
            print(f"[DEBUG] State changed from {state_before} to {self.state}, continuing update...")
            await self.broadcast_status(f"State changed from {state_before} to {self.state}, continuing update...")
            await self.update()


# ------------------ SERVER ------------------

game = MafiaGame()
lock = asyncio.Lock()


async def handler(ws: WebSocketServerProtocol):
    player_name = None
    
    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            
            # Handle control messages (voice commands from frontend)
            if msg.get("action") == "voiceCommand":
                code = msg.get("target")
                
                if isinstance(code, str) and code.isnumeric():
                    code = int(code)
                
                async with lock:
                    game.pending_code = code
                    print(f"[VOICE_COMMAND] Received: player={player_name}, code={2}")
                    await game.update()
                continue
            
            # Handle setup message
            if msg.get("action") == "setup":
                player_name = msg.get("target")
                if player_name == "rpi":
                    player_name = msg.get("name")
                    print(f"[DEBUG] server adding rpi: {player_name}")
                    
                    async with lock:
                        # Check if player already exists (from frontend registration)
                        if player_name in game.players:
                            # Player already exists - link RPI to existing player
                            print(f"[DEBUG] Linking RPI to existing player: {player_name}")
                            game.rpis[player_name] = ws
                            player_id = game.name_to_player_id.get(player_name)
                            if player_id:
                                # Send confirmation with existing player ID
                                await send_json(ws, player_id, "id_registered", None)
                                print(f"[DEBUG] RPI linked to existing player {player_name} (ID: {player_id})")
                            else:
                                print(f"[DEBUG] Warning: Player {player_name} exists but has no ID")
                        else:
                            # New player registration via RPI
                            if len(game.players) >= game.max_players:
                                print(f"[DEBUG] Game is full ({game.max_players} players)")
                                await ws.close(1008, "Game is full")
                                return

                            player_id = len(game.players) + 1
                            game.player_id_to_name[player_id] = player_name
                            game.name_to_player_id[player_name] = player_id

                            # Register RPI player
                            game.rpis[player_name] = ws
                            game.players[player_name] = {
                                "setup": True,
                                "ready": False,
                                "restart": False,
                                "voiceCommand": False,
                                "head": "up",
                                "vote": None,
                                "kill": None,
                                "save": None,
                                "alive": True
                            }
                            
                            # Send confirmation
                            await send_json(ws, player_id, "id_registered", None)
                            print(f"[DEBUG] RPI Player {player_name} registered successfully with ID {player_id}")
                    
                    # Broadcast lobby status to all players
                    await game.broadcast_lobby_status()
                    continue
                print(f"[DEBUG] server adding player: {player_name}")
                
                async with lock:
                    if player_name in game.players:
                        print(f"[DEBUG] Name {player_name} already taken")
                        await ws.close(1008, "Name already taken")
                        return
                    
                    if len(game.players) >= game.max_players:
                        print(f"[DEBUG] Game is full ({game.max_players} players)")
                        await ws.close(1008, "Game is full")
                        return

                    player_id = len(game.players) + 1
                    game.player_id_to_name[player_id] = player_name
                    game.name_to_player_id[player_name] = player_id

                    # Register player (NOT ready by default)
                    game.clients[ws] = player_name
                    game.players[player_name] = {
                        "setup": True,
                        "ready": False,
                        "restart": False,
                        "voiceCommand": False,
                        "head": "up",
                        "vote": None,
                        "kill": None,
                        "save": None,
                        "alive": True
                    }
                
                # Send confirmation
                await send_json(ws, player_id, "id_registered", None)
                print(f"[DEBUG] Player {player_name} registered successfully with ID {player_id}")
                
                # Broadcast lobby status to all players
                await game.broadcast_lobby_status()
                continue
            
            # Handle ready signal
            if msg.get("action") == "ready":
                async with lock:
                    if player_name and player_name in game.players:
                        game.players[player_name]["ready"] = True
                        print(f"[DEBUG] Player {player_name} is ready!")
                        
                        # Broadcast updated lobby status
                        await game.broadcast_lobby_status()
                        
                        # Try to start the game
                        await game.update()
                continue
            
            # Handle restart signal
            if msg.get("action") == "restart":
                async with lock:
                    if player_name and player_name in game.players and game.state == "GAMEOVER":
                        game.players[player_name]["restart"] = True
                        print(f"[DEBUG] Player {player_name} wants to restart!")
                        
                        # Broadcast updated restart status
                        await game.broadcast_restart_status()
                        
                        # Try to restart the game
                        await game.update()
                continue

            # Handle other game signals
            if player_name and game.valid_signal(msg):
                action = msg["action"]
                print(f"received signal {msg}")
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
                        print(f"[DEBUG], received target signal with target: {target}, of type: {type(target)}")

                        if isinstance(target, str) and target.isnumeric():
                            target = int(target)
                            target = game.id_to_name(target)
                            if target is None:
                                print(f"[DEBUG] Invalid player ID received: {msg.get('target')}")
                                continue
                        
                        if (player_name == game.mafia_name_one or player_name == game.mafia_name_two) and game.state == "MAFIAVOTE":
                            player_data["kill"] = target
                            print(f"[DEBUG] {player_name} voted to kill: {target}")
                        elif (player_name == game.doctor_name_one or player_name == game.doctor_name_two) and game.state == "DOCTORVOTE":
                            player_data["save"] = target
                            print(f"[DEBUG] {player_name} voted to save: {target}")
                        else:
                            player_data["vote"] = target
                            print(f"[DEBUG] {player_name} voted for: {target}")

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
                
                game.check_role_counts()
                # Broadcast updated lobby status if still in lobby
                if game.state == "LOBBY":
                    await game.broadcast_lobby_status()
                elif game.state == "GAMEOVER":
                    await game.broadcast_restart_status()
                    
            print(f"[DEBUG] Player {player_name} removed from game")

async def main():
    async with websockets.serve(handler, HOST, PORT, ping_interval=30,ping_timeout=30):
        print(f"WebSocket server running on {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
