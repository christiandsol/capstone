import socket
import json
import select
import sys
from collections import deque
from player import Player
from util import send_json, receive_json, print_dic
from voice import listen_for_command
from player import Player
from typing import Dict, Union, List
from mafia import Game

# Socket setup
HOST = "0.0.0.0"
PORT = 5050
MAX_PLAYERS = 10

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.setblocking(False)

    print(f"Listening on port {PORT}...")

    # Sockets to monitor
    clients = {}
    next_player_id = 1

    # For select()
    sockets = [server]

    # Central signal queue
    signal_queue = deque()

    game = Game()
    while True:
        readable, _, _ = select.select(sockets, [], [], 0.05)

        # Handle readable sockets
        for sock in readable:
            # A new client is connecting
            if sock is server:
                conn, addr = server.accept()
                conn.setblocking(False)

                if len(clients) >= MAX_PLAYERS:
                    print(f"Rejecting {addr} — server full")
                    send_json(conn, {"error": "Server full"})
                    conn.close()
                    continue

                player_id = next_player_id
                next_player_id += 1
                game.add_player(player_id)

                clients[conn] = player_id
                sockets.append(conn)

                send_json(conn, player_id, "player_id", None)

                print(f"[Connected] Player {player_id} from {addr}")

            # Existing client sent data
            else:
                msg = receive_json(sock)
                print_dic(msg)

                # Disconnect case
                if msg is None:
                    print(f"[Disconnected] Player {clients[sock]}")
                    sockets.remove(sock)
                    del clients[sock]
                    sock.close()
                    continue
                player = clients[sock]
                msg["player"] = player


                if game.valid_signal(msg):
                    signal_queue.append(msg)
                else:
                    print(f"Ignoring signal {msg} — not valid now")

        game.update(signal_queue)

    # Cleanup
    for c in list(clients.keys()):
        c.close()
    server.close()

if __name__ == "__main__":
    main()
