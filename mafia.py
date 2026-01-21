## Game logic
from typing import List
from player import Player
import socket
from voice import listen_for_command, listen_for_okay_mafia
from util import send_json, receive_json, print_dic
from typing import Dict, Union, List
import voice
import random
import sys
import time

class MafiaGame:
    def __init__(self, players: int):
        self.state = "LOBBY"
        self.player_cap = players
        self.players : Dict[int, Player] = {
            i + 1: Player(id=i+1, name = f"Player {i + 1}")
            for i in range(self.player_cap)
        }
        self.expected_signals = {"setup"}

        # Sockets to monitor
        self.clients : Dict[socket.socket, int]= {}
        self.mafiaOne, self.mafiaTwo, self.doctor = random.sample(range(1, self.player_cap + 1), 3)
        # COMMENT THIS OUT LATER
        # self.mafia = 1
        # self.doctor = -1
        self.last_killed = -1
        self.last_saved = -1
        self.mafia_count = -1


    def valid_signal(self, signal: Dict[str, Union[str, int]]):
        """Check if the signal action is allowed in this state"""
        if "action" not in signal:
            return False
        return signal["action"] in self.expected_signals

    def check_everyone_in_game(self):
        for player in self.players.values():
            if player.last_signal["setup"] == False:
                return False
        return True

    def check_heads_down(self, nums: List[int]):
        """
        @param nums: list of player id's who are ALLOWED to have their heads up at the given moment, pass empty list if no one is allowed
        """
        for player in self.players.values():
            if player.id not in nums and player.last_signal["head"] == "up" and player.isAlive:
                return False
        return True

    def mafia_kill(self):
        """
        Checks who the mafia voted for, returns True if signal has been received
        """
        if self.players[self.mafiaOne].isAlive and self.players[self.mafiaTwo].isAlive:
            last_kill_M1 = self.players[self.mafiaOne].last_signal["kill"]
            last_kill_M2 = self.players[self.mafiaTwo].last_signal["kill"]
            if last_kill_M1 == last_kill_M2:
                print(f"Mafia voted to kill {last_kill_M1}")
                self.players[self.mafiaOne].last_signal["kill"] = None
                self.players[self.mafiaTwo].last_signal["kill"] = None
                return last_kill_M1
            else:
                print("Please Redo. Mafia did not collectively agree.")
                return -1
        elif self.players[self.mafiaOne].isAlive:
            last_kill = self.players[self.mafiaOne].last_signal["kill"]
            if last_kill:
                print(f"Mafia voted to kill {last_kill}")
                self.players[self.mafiaOne].last_signal["kill"] = None
                return last_kill
        elif self.players[self.mafiaTwo].isAlive:
            last_kill = self.players[self.mafiaTwo].last_signal["kill"]
            if last_kill:
                print(f"Mafia voted to kill {last_kill}")
                self.players[self.mafiaTwo].last_signal["kill"] = None
                return last_kill
        return -1

    def doctor_save(self):
        """
        Checks who the doctor saved, returns True if signal has been received
        """
        last_save= self.players[self.doctor].last_signal["save"]
        if last_save:
            print(f"Doctor saved: {last_save}")
            self.players[self.doctor].last_signal["save"] = None
            return last_save
        return -1

    def everyone_voted(self):
        """
        Returns true if everyone has voted
        """
        for player in self.players.values():
            # print(state)
            if player.last_signal["vote"] == None and player.isAlive: # if you are alive and haven't voted
                return False
        return True
    def handle_vote(self):
        """
        Check who has the most votes, return that person
        """
        votes = [0] * self.player_cap
        for player in self.players.values():
            if player.isAlive:
                votes[player.last_signal["vote"] - 1] += 1

        max_votes = max(votes)
        # Find all players who received the max votes

        winners = [i for i, v in enumerate(votes) if v == max_votes]

        # now clear votes for next time
        for player in self.players.values():
            player.last_signal["vote"] = None

        if len(winners) != 1:
            return winners

        return [winners[0] + 1]
    def check_game_finished(self):
        alive_count = 0
        mafia_count = 0
        for player in self.players.values():
            if player.isMafia and player.isAlive:
                mafia_count += 1
            if not player.isMafia and player.isAlive:
                civilian_count += 1
        if mafia_count >= civilian_count:
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
                command = listen_for_command()
                if command == 2:
                    self.state = "MAFIACOUNT"
                    self.expected_signals = {}

        if self.state == "MAFIACOUNT":
            command = listen_for_command()
            if command == 3:
                self.mafia_count = 1
                self.players[self.mafiaOne].isMafia = True
                self.players[self.doctor].isDoctor = True
                self.state = "ASSIGN"
            elif command == 4:
                self.mafia_count = 2
                self.players[self.mafiaOne].isMafia = True
                self.players[self.mafiaTwo].isMafia = True
                self.players[self.doctor].isDoctor = True
                self.state = "ASSIGN"
                

        if self.state == "ASSIGN":
            for socket, player_id in self.clients.items():
                if player_id == self.mafiaOne or player_id == self.mafiaTwo:
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
                self.state = "MAFIAVOTE"
                self.expected_signals = {"headDown", "headUp", "targeted"}


        if self.state == "MAFIAVOTE":

            if not self.check_heads_down([self.mafiaOne, self.mafiaTwo]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT MAFIA")
            else:
                # print("MAFIA, signal who to kill")
                mafia_target = self.mafia_kill()
                if mafia_target != -1:
                    self.last_killed = mafia_target
                    # mafia chose to kill someone, say that they are killed
                    self.players[mafia_target].isAlive = False
                    self.expected_signals = {"headDown", "headUp"}
                    print("MAFIA VOTE READ, MOVING ON")
                    if self.doctor == -1:
                        print("HERE")
                        self.expected_signals = {}
                        self.state = "NARRATE"
                    else:
                        self.state = "DOCTORHEADSDOWN"

        if self.state == "DOCTORHEADSDOWN":
            if self.check_heads_down([]):
                print("EVERYONE'S HEAD IS DOWN, HEALER, put head up")
                self.state = "Mafia up and vote"
                self.state = "DOCTORVOTE"
                self.expected_signals = {"headDown", "headUp", "targeted"}

        if self.state == "DOCTORVOTE":
            if not self.check_heads_down([self.doctor]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT DOCTOR")
            else:
                print("DOCTOR, signal who to save")
                healer_target = self.doctor_save()
                if healer_target != -1:
                    self.last_saved = healer_target
                    # doctor chose to save someone, say that they are alive 
                    self.players[healer_target].isAlive = True
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
            print(f"HEARD COMMAND{command}")
            if command == 3:
                print("YOU MAY NOW SIGNAL WHO TO VOTE")
                self.expected_signals = {"targeted"}
                self.state = "VOTE"

        if self.state == "VOTE":
            if self.everyone_voted():
                voted_out = self.handle_vote()
                if len(voted_out) == 1:
                    print(f"Player: {voted_out} was voted out, sorry")
                    self.players[voted_out[0]].isAlive = False
                    print("DRUM ROLL...")
                    time.sleep(2)
                    if voted_out[0] == self.mafiaOne or voted_out[0] == self.mafiaTwo:
                        self.mafia_count -= 1
                        if self.mafia_count == 0:
                            print("CIVILIANS CORRECTLY VOTED OUT THE MAFIA, CIVILIANS WIN!!!")
                            self.state = "FINISHED"
                        else:
                            print("GAME CONTINUES, EVERYONE PUT YOUR HEADS DOWN")
                            self.state = "HEADSDOWN"
                            self.expected_signals = {"headDown", "headUp"}
                    elif self.check_game_finished():
                        print("MAFIA WINS")
                        self.state = "FINISHED"
                    else:
                        print("GAME CONTINUES, EVERYONE PUT YOUR HEADS DOWN")
                        self.state = "HEADSDOWN"
                        self.expected_signals = {"headDown", "headUp"}
                else:
                    print(f"There was a tie between {voted_out}, moving on!")
                    print("CIVILIANS FAILED TO VOTE OUT THE MAFIA, GAME CONTINUES, EVERYONE PUT YOUR HEADS DOWN")
                    self.state = "HEADSDOWN"
                    self.expected_signals = {"headDown", "headUp"}

        if self.state == "FINISHED":
            pass