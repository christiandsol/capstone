import socket
import json
import select
import sys
import random
from collections import deque
from player import Player
from util import send_json, receive_json, print_dic
from voice import listen_for_command
from player import Player
from typing import Dict, Union, List

# Socket setup
HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 10

class MafiaGame:
    def __init__(self, players: int):
        self.state = "LOBBY"
        self.players = set()
        self.expected_signals = {"setup"}
        self.player_cap = players 
        self.last_signal = []  # An array of dictionaries for each player, mapping all signals to the LAST signal received of that type
        # Sockets to monitor
        self.clients : Dict[socket.socket, int]= {}
        # EACH ONE WILL BE:
        # {"head"}
        # i.e an array 

    def valid_signal(self, signal: Dict[str, Union[str, int]]):
        """Check if the signal action is allowed in this state"""
        return signal["action"] in self.expected_signals

    def add_player(self, player_id: int):
        """
        Add player to player set
        """
        self.players.add(player_id)

    def update(self, signal_queue: List[Dict[str, Union[str,int]]]):
        """
        Consume only the signals that matter for the current state.
        Ignore or discard others.
        """

        if self.state == "LOBBY":
            while signal_queue:
                sig = signal_queue.popleft()

                if sig["action"] == "setup":
                    print("ADDING PLAYER WITH ADD_PLAYER")
                    self.add_player(sig["player"])
                    print(self.players)

            if len(self.players) >= self.player_cap:
                print("All players connected — starting game!")
                command = listen_for_command()
                if command == "ready":
                    self.state = "ASSIGN"
                    self.expected_signals = {}

        if self.state == "ASSIGN":
            mafia, doctorNum = random.sample(range(1, self.player_cap + 1), 2)
            for socket, player_id in self.clients.items():
                if player_id == mafia:
                    send_json(socket, player_id, "mafia", None)
                elif player_id == doctorNum:
                    send_json(socket, player_id, "doctor", None)
                else:
                    send_json(socket, player_id, "civilian", None)



        elif self.state == "NIGHT":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Night Signal] {sig}")

        elif self.state == "DAY":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Day Signal] {sig}")




def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.setblocking(False)

    print(f"Listening on port {PORT}...")

    next_player_id = 1

    # For select()
    sockets = [server]

    # Central signal queue
    signal_queue = deque()

    game = MafiaGame(2)
    while True:
        readable, _, _ = select.select(sockets, [], [], 0.05)

        # Handle readable sockets
        for sock in readable:
            # A new client is connecting
            if sock is server:
                conn, addr = server.accept()
                conn.setblocking(False)

                if len(game.clients) >= MAX_PLAYERS:
                    print(f"Rejecting {addr} — server full")
                    send_json(conn, {"error": "Server full"})
                    conn.close()
                    continue

                player_id = next_player_id
                next_player_id += 1

                game.clients[conn] = player_id
                sockets.append(conn)

                send_json(conn, player_id, "player_id", None)

                print(f"[Connected] Player {player_id} from {addr}")

            # Existing client sent data
            else:
                msg = receive_json(sock)
                print_dic(msg)

                # Disconnect case
                if msg is None:
                    print(f"[Disconnected] Player {game.clients[sock]}")
                    sockets.remove(sock)
                    del game.clients[sock]
                    sock.close()
                    continue
                player = game.clients[sock]
                msg["player"] = player


                if game.valid_signal(msg):
                    signal_queue.append(msg)
                else:
                    print(f"Ignoring signal {msg} — not valid now")

        game.update(signal_queue)

    # Cleanup
    for c in list(game.clients.keys()):
        c.close()
    server.close()

if __name__ == "__main__":
    main()
