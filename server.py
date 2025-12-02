import socket
import json
import select
import sys
import random
from collections import deque
import time
from player import Player
from util import send_json, receive_json, print_dic
from voice import listen_for_command
from player import Player
from typing import Dict, Union, List, Deque
from mafia import Game

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
        template = {"head": None, "vote": None, "kill": None, "save": None, "setup": False} ## An array of dictionaries for each player, mapping all signals to the LAST signal received of that type
        self.last_signal = [template.copy() for _ in range(self.player_cap)]

        # Sockets to monitor
        self.clients : Dict[socket.socket, int]= {}
        # self.mafia, self.doctor = random.sample(range(1, self.player_cap + 1), 2)
        # COMMENT THIS OUT LATER
        self.mafia = 1
        self.doctor = -1
        self.alive = [True] * self.player_cap
        self.last_killed = -1
        self.last_saved = -1


    def valid_signal(self, signal: Dict[str, Union[str, int]]):
        print(signal)
        """Check if the signal action is allowed in this state"""
        if "action" not in signal:
            return False
        return signal["action"] in self.expected_signals

    def add_player(self, player_id: int):
        """
        Add player to player set
        """
        self.players.add(player_id)

    def check_everyone_in_game(self):
        for i, state in enumerate(self.last_signal):
            if state["setup"] == False:
                return False
            else:
                self.add_player(i + 1)
                print(self.players)
        return True

    def check_heads_down(self, nums: List[int]):
        """
        @param nums: list of player id's who are ALLOWED to have their heads up at the given moment, pass empty list if no one is allowed
        """
        for i, state in enumerate(self.last_signal):
            if (i + 1) not in nums and state["head"] == "up" and self.alive[i]:
                return False
        return True

    def mafia_kill(self):
        """
        Checks who the mafia voted for, returns True if signal has been received
        """
        last_kill = self.last_signal[self.mafia - 1]["kill"]
        if last_kill:
            print(f"Mafia voted to kill {last_kill}")
            self.last_signal[self.mafia - 1]["kill"] = None
            return last_kill
        return -1

    def doctor_save(self):
        """
        Checks who the doctor saved, returns True if signal has been received
        """
        last_save= self.last_signal[self.doctor- 1]["save"]
        if last_save:
            print(f"Doctor saved: {last_save}")
            self.last_signal[self.doctor- 1]["save"] = None
            return last_save
        return -1

    def everyone_voted(self):
        """
        Returns true if everyone has voted
        """
        for i, state in enumerate(self.last_signal):
            if state["vote"] == None and self.alive[i]: # if you are alive and haven't voted
                return False
        return True
    def handle_vote(self):
        """
        Check who has the most votes, return that person
        """
        votes = [0] * self.player_cap
        for i, state in enumerate(self.last_signal):
            votes[state["vote"] - 1] += 1

        max_votes = max(votes)
        # Find all players who received the max votes

        winners = [i for i, v in enumerate(votes) if v == max_votes]

        # now clear votes for next time
        for i, state in enumerate(self.last_signal):
            self.last_signal[i]["vote"] = None

        if len(winners) != 1:
            return winners

        return [winners[0] + 1]
    def check_game_finished(self):
        alive_count = 0
        for item in self.alive:
            if item == True:
                alive_count += 1
        if alive_count == 2:
            return True
        else:
            return False

    def update(self):
        """
        Consume only the signals that matter for the current state.
        Ignore or discard others.
        """

        if self.state == "LOBBY":
            if self.check_everyone_in_game():
                print("All players connected — starting game!")
                # command = listen_for_command()
                # if command == "ready":
                self.state = "ASSIGN"
                self.expected_signals = {}

        if self.state == "ASSIGN":
            for socket, player_id in self.clients.items():
                if player_id == self.mafia:
                    send_json(socket, player_id, "mafia", None)
                elif player_id == self.doctor:
                    send_json(socket, player_id, "doctor", None)
                else:
                    send_json(socket, player_id, "civilian", None)
            # Maybe add a little time.sleep for the transitions
            print("EVERYONE PUT THEIR HEADS DOWN")
            self.state = "HEADSDOWN"
            self.expected_signals = {"headDown", "headUp"}

        if self.state == "HEADSDOWN": 
            if self.check_heads_down([]):
                print("EVERYONE'S HEAD IS DOWN, MAFIA, put head up")
                self.state = "Mafia up and vote"
                self.state = "MAFIAVOTE"
                self.expected_signals = {"headDown", "headUp", "targeted"}


        if self.state == "MAFIAVOTE":
            if not self.check_heads_down([self.mafia]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT MAFIA")
            else:
                print("MAFIA, signal who to kill")
                mafia_target = self.mafia_kill()
                if mafia_target != -1:
                    self.last_killed = mafia_target
                    # mafia chose to kill someone, say that they are killed
                    self.alive[mafia_target - 1] = False
                    self.expected_signals = {"headDown", "headUp"}
                    print("MAFIA VOTE READ, MOVING ON")
                    self.state = "DOCTORHEADSDOWN"

        if self.state == "DOCTORHEADSDOWN":
            if self.check_heads_down([]):
                print("EVERYONE'S HEAD IS DOWN, HEALER, put head up")
                self.state = "Mafia up and vote"
                self.state = "DOCTORVOTE"
                self.expected_signals = {"headDown", "headUp", "save"}

        if self.state == "DOCTORVOTE":
            if not self.check_heads_down([self.doctor]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT DOCTOR")
            else:
                print("DOCTOR, signal who to save")
                healer_target = self.doctor_save()
                if healer_target != -1:
                    self.last_saved = healer_target
                    # doctor chose to save someone, say that they are alive 
                    self.alive[healer_target - 1] = True
                    self.expected_signals = {}
                    print("DOCTOR VOTE READ, MOVING ON")
                    print("EVERYONE put their heads up")
                    self.state = "NARRATE"

        if self.state == "NARRATE":
            print(f"IN THE NIGHT, THE MAFIA CHOSE TO KILL...")
            time.sleep(2)
            print(f"PLAYER {self.last_killed}")
            time.sleep(1)
            if self.last_killed == self.last_saved:
                print("BUT...")
                time.sleep(1)
                print(f"THEY WERE SAVED BY THE DOCTOR")
            else:
                print(f"Unfortunately they were not saved")
            time.sleep(2)

            if self.check_game_finished():
                print(f"DRUM ROLL...")
                time.sleep(2)
                print(f"MAFIA WINS!")
                self.state = "FINISHED"
                return
            print("NOW IT IS THE VOTING STAGE, SAY WHEN YOU ARE READY TO VOTE AND IT WILL BEGIN")
            command = listen_for_command()
            if command == "vote":
                print("YOU MAY NOW SIGNAL WHO TO VOTE")
                self.expected_signals = {"vote"}
                self.state = "VOTE"

        if self.state == "VOTE":
            if self.everyone_voted():
                voted_out = self.handle_vote()
                if len(voted_out) == 1:
                    print(f"Player: {voted_out} was voted out, sorry")
                    self.alive[voted_out[0] - 1] = False
                    print("DRUM ROLL...")
                    time.sleep(2)
                    if voted_out[0] == self.mafia:
                        print("CIVILIANS CORRECTLY VOTED OUT THE MAFIA, CIVILIANS WIN!!!")
                        self.state = "FINISHED"
                    else:
                        print("CIVILIANS FAILED TO VOTE OUT THE MAFIA, GAME CONTINUES, EVERYONE PUT YOUR HEADS DOWN")
                        self.state = "HEADSDOWN"
                        self.expected_signals = {"headDown", "headUp"}
                else:
                    print(f"There was a tie between {voted_out}, vote again!")

        if self.state == "FINISHED":
            pass

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

    game = MafiaGame(1)
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
                    game.last_signal[player_id - 1]["setup"] = True

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
                        game.last_signal[player - 1]["head"] = "down"
                    elif action == "headUp":
                        game.last_signal[player - 1]["head"] = "up"
                    elif action == "targeted":
                        if player == game.mafia:
                            game.last_signal[player - 1]["kill"] = msg["target"]
                        elif player == game.doctor:
                            game.last_signal[player - 1]["save"] = msg["target"]
                        else:
                            game.last_signal[player - 1]["vote"] = msg["target"]

                else:
                    print(f"Ignoring signal {msg} — not valid now")

        game.update()

    # Cleanup
    for c in list(game.clients.keys()):
        c.close()
    server.close()

if __name__ == "__main__":
    main()
