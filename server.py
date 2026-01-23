import asyncio
import socket
import json
import select
import sys
import random
from collections import deque
import time
from player import Player
from util import send_json, receive_json, print_dic, parse_json
from voice import listen_for_command
from player import Player
from typing import Dict, Union, List, Deque
from mafia import Game
import websockets
from websockets.server import WebSocketServerProtocol


# Socket setup
HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 10

class MafiaGame:
    def __init__(self, players: int):
        self.state = "LOBBY"
        self.expected_signals = {"setup"}
        self.player_cap = players

        template = {
            "head": None,
            "vote": None,
            "kill": None,
            "save": None,
            "setup": False
        }

        self.last_signal = [template.copy() for _ in range(players)]
        self.clients: Dict[WebSocketServerProtocol, int] = {}

        self.mafia, self.doctor = random.sample(range(1, players + 1), 2)
        self.alive = [True] * players

        self.last_killed = -1
        self.last_saved = -1

    def valid_signal(self, signal):
        return signal and signal.get("action") in self.expected_signals

    def check_everyone_in_game(self):
        return all(p["setup"] for p in self.last_signal)

    def check_heads_down(self, allowed: List[int]):
        for i, s in enumerate(self.last_signal):
            if self.alive[i] and s["head"] == "up" and (i + 1) not in allowed:
                return False
        return True

    def mafia_kill(self):
        kill = self.last_signal[self.mafia - 1]["kill"]
        if kill:
            self.last_signal[self.mafia - 1]["kill"] = None
            return kill
        return -1

    def doctor_save(self):
        save = self.last_signal[self.doctor - 1]["save"]
        if save:
            self.last_signal[self.doctor - 1]["save"] = None
            return save
        return -1

    def everyone_voted(self):
        for i, s in enumerate(self.last_signal):
            if self.alive[i] and s["vote"] is None:
                return False
        return True

    def handle_vote(self):
        votes = [0] * self.player_cap
        for s in self.last_signal:
            votes[s["vote"] - 1] += 1

        max_votes = max(votes)
        winners = [i + 1 for i, v in enumerate(votes) if v == max_votes]

        for s in self.last_signal:
            s["vote"] = None

        return winners

    async def broadcast(self, action, target=None):
        for ws, pid in self.clients.items():
            await send_json(ws, pid, action, target)

    async def update(self):
        if self.state == "LOBBY" and self.check_everyone_in_game():
            print("All players connected")
            self.state = "ASSIGN"
            self.expected_signals = set()

        if self.state == "ASSIGN":
            for ws, pid in self.clients.items():
                role = "civilian"
                if pid == self.mafia:
                    role = "mafia"
                elif pid == self.doctor:
                    role = "doctor"
                await send_json(ws, pid, role, None)

            self.state = "HEADSDOWN"
            self.expected_signals = {"headUp", "headDown"}

        if self.state == "HEADSDOWN" and self.check_heads_down([]):
            self.state = "MAFIAVOTE"
            self.expected_signals = {"headUp", "headDown", "targeted"}

        if self.state == "MAFIAVOTE":
            if self.check_heads_down([self.mafia]):
                kill = self.mafia_kill()
                if kill != -1:
                    self.last_killed = kill
                    self.alive[kill - 1] = False
                    self.state = "DOCTORVOTE" if self.doctor else "NARRATE"

        if self.state == "DOCTORVOTE":
            if self.check_heads_down([self.doctor]):
                save = self.doctor_save()
                if save != -1:
                    self.last_saved = save
                    self.alive[save - 1] = True
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
next_player_id = 1
lock = asyncio.Lock()


async def handler(ws: WebSocketServerProtocol):
    global next_player_id

    async with lock:
        pid = next_player_id
        next_player_id += 1
        game.clients[ws] = pid
        game.last_signal[pid - 1]["setup"] = True

    await send_json(ws, pid, "player_id", None)
    print(f"Player {pid} connected")

    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue

            msg["player"] = pid

            if game.valid_signal(msg):
                action = msg["action"]
                if action == "headUp":
                    game.last_signal[pid - 1]["head"] = "up"
                elif action == "headDown":
                    game.last_signal[pid - 1]["head"] = "down"
                elif action == "targeted":
                    if pid == game.mafia and game.state == "MAFIAVOTE":
                        game.last_signal[pid - 1]["kill"] = msg["target"]
                    elif pid == game.doctor and game.state == "DOCTORVOTE":
                        game.last_signal[pid - 1]["save"] = msg["target"]
                    else:
                        game.last_signal[pid - 1]["vote"] = msg["target"]

            await game.update()

    finally:
        print(f"Player {pid} disconnected")
        del game.clients[ws]


async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"WebSocket server running on {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
