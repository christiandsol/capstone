import socket
import json
import select
import sys
import random
from collections import deque
import time
from player import Player
from util import send_json, receive_json, print_dic
from voice import listen_for_command, listen_for_okay_mafia
from player import Player
from typing import Dict, Union, List, Deque
from mafia import MafiaGame

# Socket setup
HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 3

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

    game = MafiaGame(MAX_PLAYERS)
    while True:
        readable, _, _ = select.select(sockets, [], [], 0.05)

        # Handle readable sockets
        for sock in readable:
            # A new client is connecting
            if sock is server:
                conn, addr = server.accept()
                # conn.setblocking(True)
                conn.setblocking(False)


                msg = receive_json(conn)
                if msg is None:
                    print(f"[Connection Failed] No handshake from {addr}")
                    conn.close()
                    continue
                client_type = msg.get("action")
                if client_type == "setup" and msg.get("target") == "raspberry_pi":
                    print("RECIEVED RASBPI CONNECTION SIGNAL")
                    # this is a raspberry pi socket
                    player_id = msg.get("player")
                    if len(game.clients) >= MAX_PLAYERS:
                        print(f"Rejecting {addr} — server full")
                        send_json(conn, {"error": "Server full"})
                        conn.close()
                        continue
                    # add player_id to this reference client
                    game.clients[conn] = player_id
                    game.players[player_id].last_signal["setup"] = True
                    sockets.append(conn)
                    pass
                else:
                    # Normal socket
                    if len(game.clients) >= MAX_PLAYERS:
                        print(f"Rejecting {addr} — server full")
                        send_json(conn, {"error": "Server full"})
                        conn.close()
                        continue
                    player_id = next_player_id
                    next_player_id += 1
                    game.players[player_id].last_signal["setup"] = True

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
                    # print(f"[Disconnected] Player {game.clients[sock]}")
                    # sockets.remove(sock)
                    # del game.clients[sock]
                    # sock.close()
                    continue
                player = game.clients[sock]
                msg["player"] = player


                # template = {"head": None, "vote": None, "kill": None, "save": None, "setup": None}
                if game.valid_signal(msg):
                    print(f"RECEIVED signal {msg} — valid ")
                    action = msg["action"]
                    if action == "headDown":
                        game.players[player].last_signal["head"] = "down"
                    elif action == "headUp":
                        game.players[player].last_signal["head"] = "up"
                    elif action == "targeted":
                        print(f"STATE: {game.state} player: {player}")
                        if game.players[player].isMafia and game.state == "MAFIAVOTE":
                            print("1")
                            game.players[player].last_signal["kill"] = msg["target"]
                        elif game.players[player].isDoctor and game.state == "DOCTORVOTE":
                            print("2")
                            game.players[player].last_signal["save"] = msg["target"]
                        else:
                            print("3")
                            game.players[player].last_signal["vote"] = msg["target"]

                else:
                    pass
                    # print(f"Ignoring signal {msg} — not valid now")

        game.update()

    # Cleanup
    for c in list(game.clients.keys()):
        c.close()
    server.close()

if __name__ == "__main__":
    main()
