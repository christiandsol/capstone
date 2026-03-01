
import asyncio
import random
from typing import Dict, List, Optional
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from util import send_json, parse_json

MAX_PLAYERS = 8


class MafiaGame:
    def __init__(self):
        self.state: str = "LOBBY"
        self.expected_signals: set = {"setup"}
        self.max_players: int = MAX_PLAYERS

        self.players: Dict[str, dict] = {}                     # player_name: str -> player data: player_state
        self.clients: Dict[WebSocketServerProtocol, str] = {}  # ws               -> player_name
        self.rpis: Dict[str, WebSocketServerProtocol] = {}     # player_name      -> rpi_ws

        # id <-> name lookup (ids only used by RPis for targeting)
        self.player_id_to_name: Dict[int, str] = {}
        self.name_to_player_id: Dict[str, int] = {}

        # role assignments
        self.mafia_name_one: Optional[str] = None
        self.mafia_name_two: Optional[str] = None
        self.doctor_name_one: Optional[str] = None
        self.doctor_name_two: Optional[str] = None

        self.mafia_count: int = 0
        self.doctor_count: int = 0

        # night-phase tracking
        self.last_killed: Optional[str] = None
        self.last_saved: Optional[str] = None

        self.game_winner: Optional[str] = None
        self.game_started: bool = False

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def valid_signal(self, signal: dict) -> bool:
        return bool(signal and signal.get("action") in self.expected_signals)

    def id_to_name(self, player_id: int) -> Optional[str]:
        return self.player_id_to_name.get(player_id)

    def name_to_id(self, player_name: str) -> Optional[int]:
        return self.name_to_player_id.get(player_name)

    def _active_mafia_names(self) -> List[str]:
        """return list of currently assigned mafia player names"""
        return [n for n in [self.mafia_name_one, self.mafia_name_two] if n is not None]

    def _active_doctor_names(self) -> List[str]:
        """return list of currently assigned doctor player names"""
        return [n for n in [self.doctor_name_one, self.doctor_name_two] if n is not None]

    def _remove_mafia(self, player_name: str):
        """remove a player from mafia slots and decrement mafia_count"""
        if self.mafia_name_one == player_name:
            self.mafia_name_one = self.mafia_name_two
            self.mafia_name_two = None
            self.mafia_count -= 1
        elif self.mafia_name_two == player_name:
            self.mafia_name_two = None
            self.mafia_count -= 1

    def _remove_doctor(self, player_name: str):
        """remove a player from doctor slots and decrement doctor_count"""
        if self.doctor_name_one == player_name:
            self.doctor_name_one = self.doctor_name_two
            self.doctor_name_two = None
            self.doctor_count -= 1
        elif self.doctor_name_two == player_name:
            self.doctor_name_two = None
            self.doctor_count -= 1

    # ------------------------------------------------------------------
    # ready / vote checks
    # ------------------------------------------------------------------

    def check_everyone_ready(self) -> bool:
        if len(self.players) < 3:
            return False
        return all(p["ready"] for p in self.players.values())

    def check_everyone_ready_to_vote(self) -> bool:
        alive = [p for p in self.players.values() if p["alive"]]
        return bool(alive) and all(p["ready_to_vote"] for p in alive)

    def check_everyone_wants_restart(self) -> bool:
        return bool(self.players) and all(p["restart"] for p in self.players.values())

    def everyone_voted(self) -> bool:
        return all(
            p["vote"] is not None
            for p in self.players.values()
            if p["alive"]
        )

    # ------------------------------------------------------------------
    # GAME OVER checker
    # ------------------------------------------------------------------

    def check_game_over(self) -> Optional[str]:
        """Return 'mafia', 'civilians', or None if the game continues"""
        alive_mafia = [
            name for name in self._active_mafia_names()
            if self.players[name]["alive"]
        ]
        if not alive_mafia:
            return "civilians"

        alive_players = [name for name, data in self.players.items() if data["alive"]]
        alive_civilians = [name for name in alive_players if name not in self._active_mafia_names()]

        if len(alive_mafia) >= len(alive_civilians):
            return "mafia"

        return None

    # ------------------------------------------------------------------
    # night phase actions
    # ------------------------------------------------------------------

    def get_mafia_kill_target(self) -> Optional[str]:
        """
        Return the agreed kill target once all living mafia have chosen the
        same player, then clear their choices
        If both mafia voted but disagreed, reset both votes and return None
        """
        if self.mafia_count == 1:
            m = self.mafia_name_one
            if m and self.players[m]["alive"] and self.players[m]["kill"]:
                target = self.players[m]["kill"]
                self.players[m]["kill"] = None
                return target
            return None

        # mafia_count == 2: both must agree on the same target
        m1, m2 = self.mafia_name_one, self.mafia_name_two
        if m1 and self.players[m1]["kill"] and m2 and self.players[m2]["kill"]:
            if self.players[m1]["kill"] == self.players[m2]["kill"]:
                target = self.players[m1]["kill"]
                self.players[m1]["kill"] = None
                self.players[m2]["kill"] = None
                return target
            # Disagreement means reset both so they vote again
            self.players[m1]["kill"] = None
            self.players[m2]["kill"] = None
        return None

    def get_doctor_save_target(self) -> Optional[str]:
        """
        Return the agreed save target once all living doctors have chosen the
        same player, then clear their choices
        """
        if self.doctor_count == 0:
            return None

        if self.doctor_count == 1:
            d = self.doctor_name_one
            if d and self.players[d]["alive"] and self.players[d]["save"]:
                target = self.players[d]["save"]
                self.players[d]["save"] = None
                return target
            return None

        # doctor_count == 2: both must agree on the same target
        d1, d2 = self.doctor_name_one, self.doctor_name_two
        if d1 and self.players[d1]["save"] and d2 and self.players[d2]["save"]:
            if self.players[d1]["save"] == self.players[d2]["save"]:
                target = self.players[d1]["save"]
                self.players[d1]["save"] = None
                self.players[d2]["save"] = None
                return target
        return None

    # ------------------------------------------------------------------
    # tallying
    # ------------------------------------------------------------------

    def tally_day_votes(self) -> List[str]:
        """
        Count day votes from all alive players
        Returns a list of player_names — length > 1 means a tie
        Clears all votes after tallying
        """
        vote_counts: Dict[str, int] = {}
        for data in self.players.values():
            if data["alive"] and data["vote"]:
                target = data["vote"]
                vote_counts[target] = vote_counts.get(target, 0) + 1

        for data in self.players.values():
            data["vote"] = None

        if not vote_counts:
            return []

        max_votes = max(vote_counts.values())
        return [name for name, count in vote_counts.items() if count == max_votes]

    # ------------------------------------------------------------------
    # Broadcasting helpers
    # ------------------------------------------------------------------

    async def broadcast(self, action: str, target=None):
        """Send a message to all connected web clients"""
        for ws, player_name in list(self.clients.items()):
            try: 
                await send_json(ws, player_name, action, target)
            except Exception as e:
                print(f"[DEBUG] Failed to broadcast to {player_name}: {e}")

    async def broadcast_lobby_status(self):
        """Send current lobby state to all web clients"""
        ready_count = sum(1 for p in self.players.values() if p["ready"])
        total_count = len(self.players)
        payload = {
            "ready_count": ready_count,
            "total_count": total_count,
            "min_players": 3,
            "max_players": self.max_players,
            "players": {
                name: data["ready"]
                for name, data in self.players.items()
            },
        }
        for ws, player_name in list(self.clients.items()):
            await send_json(ws, player_name, "lobby_status", payload)

    async def broadcast_restart_status(self):
        """Send current restart-vote state to all web clients and RPis"""
        restart_count = sum(1 for p in self.players.values() if p["restart"])
        total_count = len(self.players)
        payload = {
            "restart_count": restart_count,
            "total_count": total_count,
            "players": {
                name: data["restart"]
                for name, data in self.players.items()
            },
        }
        for ws, player_name in list(self.clients.items()):
            await send_json(ws, player_name, "restart_status", payload)
        for player_name, ws in list(self.rpis.items()):
            await send_json(ws, player_name, "restart_status", payload)

    async def request_action_from_rpi(self, player_name: str, action: str):
        """Ask a specific player's RPi to perform an action (kill / save / vote)"""
        if not player_name:
            return
        ws = self.rpis.get(player_name)
        if ws:
            print(f"[DEBUG] Requesting '{action}' from {player_name}'s RPi")
            await send_json(ws, player_name, action, None)

    async def broadcast_vote_request(self):
        """Ask every alive player's RPi to cast a day vote"""
        for player_name in self._active_mafia_names() + self._active_doctor_names():
            pass  # mafia/doctor still vote in day phase
        for player_name, ws in self.rpis.items():
            if player_name in self.players and self.players[player_name]["alive"]:
                await self.request_action_from_rpi(player_name, "vote")

    async def broadcast_roles(self):
        """Send each player their role (mafia / doctor / civilian)"""
        mafia_names = self._active_mafia_names()
        doctor_names = self._active_doctor_names()

        def role_for(player_name: str) -> str:
            if player_name in mafia_names:
                return "mafia"
            if player_name in doctor_names:
                return "doctor"
            return "civilian"

        for ws, player_name in self.clients.items():
            await send_json(ws, player_name, role_for(player_name), None)
        for player_name, ws in self.rpis.items():
            await send_json(ws, player_name, role_for(player_name), None)

    # ------------------------------------------------------------------
    # Game state reset
    # ------------------------------------------------------------------

    def reset_game_state(self):
        """Reset all game variables for a new round, keeping existing players"""
        print("[DEBUG] Resetting game state for new round...")

        for player_data in self.players.values():
            player_data["ready"] = False
            player_data["ready_to_vote"] = False
            player_data["restart"] = False
            player_data["head"] = "up"
            player_data["vote"] = None
            player_data["kill"] = None
            player_data["save"] = None
            player_data["alive"] = True

        self.player_id_to_name = {}
        self.name_to_player_id = {}


        self.mafia_name_one = None
        self.mafia_name_two = None
        self.doctor_name_one = None
        self.doctor_name_two = None
        self.mafia_count = 0
        self.doctor_count = 0
        self.last_killed = None
        self.last_saved = None
        self.game_winner = None
        self.game_started = False

        self.state = "LOBBY"
        self.expected_signals = {"setup"}

        print("[DEBUG] Game state reset complete")

    def check_heads_down(self, allowed: List[str]) -> bool:
        """Return True if every alive player (not in `allowed`) has their head down"""
        for player_name, data in self.players.items():
            if data["alive"] and data["head"] == "up" and player_name not in allowed:
                print(f"[DEBUG] {player_name} still has head up")
                return False
        return True

    # ------------------------------------------------------------------
    # Main game-loop state machine
    # ------------------------------------------------------------------

    async def update(self):
        """Drive the game state machine forward after any player action"""

        # LOBBY: wait for everyone to ready up (min 3 players)
        if self.state == "LOBBY" and self.check_everyone_ready():
            print(f"[DEBUG] All {len(self.players)} players ready! Assigning roles...")
            player_names = list(self.players.keys())

            if len(player_names) >= 7:
                self.mafia_count = 2
                self.doctor_count = 2
                (
                    self.mafia_name_one,
                    self.mafia_name_two,
                    self.doctor_name_one,
                    self.doctor_name_two,
                ) = random.sample(player_names, 4)
            else:
                self.mafia_count = 1
                self.doctor_count = 1
                self.mafia_name_one, self.doctor_name_one = random.sample(player_names, 2)

            print(f"[DEBUG] Roles: mafia={self._active_mafia_names()}, doctors={self._active_doctor_names()}")
            self.state = "ASSIGN"
            self.expected_signals = set()
            self.game_started = True

        # ASSIGN: send roles and ask everyone to put heads down
        if self.state == "ASSIGN":
            await self.broadcast_roles()
            await self.broadcast("heads_down")
            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("[DEBUG] Roles sent — waiting for heads down")

        # HEADSDOWN: wait for all alive players to put heads down
        if self.state == "HEADSDOWN" and self.check_heads_down([]):
            self.state = "MAFIAVOTE"
            self.expected_signals = {"headUp", "headDown", "voiceCommand", "target"}
            await self.broadcast("night_phase_kill")
            print("[DEBUG] Night phase — requesting mafia kill vote")
            for mafia_name in self._active_mafia_names():
                await self.request_action_from_rpi(mafia_name, "kill")
            return

        # MAFIAVOTE: wait for mafia to agree on a kill target
        if self.state == "MAFIAVOTE":
            kill_target = self.get_mafia_kill_target()
            if kill_target is None:
                print(f"[DEBUG] Kill Target is None")
                return  # Not ready yet (or disagreement was reset — they'll re-vote)

            print(f"[DEBUG] Mafia agreed to kill: {kill_target}")
            self.last_killed = kill_target

            # If no living doctor exists, apply the kill immediately
            doctor_alive = any(
                self.players[d]["alive"] for d in self._active_doctor_names()
            ) if self._active_doctor_names() else False

            if not doctor_alive:
                self.players[kill_target]["alive"] = False

            await self.broadcast("mafia_kill", kill_target)

            winner = self.check_game_over()
            if winner:
                await self._end_game(winner)
                return

            self.state = "DOCTORVOTE"
            self.expected_signals = {"headUp", "headDown", "voiceCommand", "target"}
            print("[DEBUG] Doctor voting")
            for doctor_name in self._active_doctor_names():
                await self.request_action_from_rpi(doctor_name, "save")
            return

        # DOCTORVOTE: wait for doctor(s) to agree on a save target
        if self.state == "DOCTORVOTE":
            save_target = self.get_doctor_save_target()

            if save_target is None and self.doctor_count > 0:
                return  # Doctor(s) haven't chosen yet

            self.last_saved = save_target

            # Apply the mafia kill if the doctor didn't save the target
            if self.last_killed and self.last_killed != save_target:
                self.players[self.last_killed]["alive"] = False
                self._remove_mafia(self.last_killed)
                self._remove_doctor(self.last_killed)

            await self.broadcast("doctor_save", save_target)
            self.state = "NARRATE"

        # NARRATE: announce what happened overnight, then move to day discussion
        if self.state == "NARRATE":
            print("[DEBUG] Narrating night results...")
            await self.broadcast("night_result", {
                "killed": self.last_killed,
                "saved": self.last_saved,
            })
            self.last_killed = None
            self.last_saved = None

            winner = self.check_game_over()
            if winner:
                await self._end_game(winner)
                return

            for player_data in self.players.values():
                player_data["ready_to_vote"] = False

            self.state = "READYTOVOTE"
            self.expected_signals = {"voiceCommand"}
            print("[DEBUG] Waiting for players to say 'ready to vote'")

        # READYTOVOTE: wait for all alive players to signal they're ready
        if self.state == "READYTOVOTE" and self.check_everyone_ready_to_vote():
            print("[DEBUG] All ready — starting day vote")
            self.state = "VOTE"
            self.expected_signals = {"voiceCommand", "target"}
            await self.broadcast_vote_request()

        # VOTE: wait for all alive players to cast their vote
        if self.state == "VOTE" and self.everyone_voted():
            candidates = self.tally_day_votes()

            if len(candidates) != 1:
                print(f"[DEBUG] Vote tied between {candidates} — voting again")
                await self.broadcast("vote_result_tie", candidates)
                await self.broadcast_vote_request()
                return

            voted_out_name = candidates[0]
            print(f"[DEBUG] Voted out: {voted_out_name}")

            self.players[voted_out_name]["alive"] = False
            self._remove_mafia(voted_out_name)
            self._remove_doctor(voted_out_name)

            await self.broadcast("vote_result", voted_out_name)

            winner = self.check_game_over()
            if winner:
                await self._end_game(winner)
                return

            # Reset per-round player state and return to night phase
            for player_data in self.players.values():
                player_data["vote"] = None
                player_data["kill"] = None
                player_data["save"] = None
                player_data["head"] = "up"
                player_data["ready_to_vote"] = False

            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}
            print("[DEBUG] Back to night phase")
            await self.broadcast("heads_down", voted_out_name)

        # GAMEOVER: wait for everyone to vote restart
        if self.state == "GAMEOVER" and self.check_everyone_wants_restart():
            print("[DEBUG] All players want to restart!")
            self.reset_game_state()
            await self.broadcast_lobby_status()

    async def _end_game(self, winner: str):
        """Transition to GAMEOVER and notify all clients"""
        print(f"[DEBUG] Game over — winner: {winner}")
        self.game_winner = winner
        # NOTE: This is commented so that no one can join even when people are in the play again phase
        # self.game_started = False
        self.state = "GAMEOVER"
        self.expected_signals = set()
        await self.broadcast("game_over", {
            "winner": winner,
            "mafia": self._active_mafia_names(),
        })
        await self.broadcast_restart_status()

