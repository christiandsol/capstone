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


class Game:
    def __init__(self, player_amount):
        self.state = "LOBBY"
        self.players= [None] * player_amount
        self.votes = {}
        self.kill = -1
        self.save = -1
        self.mafiaOne = None
        #self.mafiaTwo = None
        self.doctorNum = None
        self.expected_signals = {"setup"}
        self.clients : Dict[socket.socket, int]= {}
        self.player_cap = player_amount

    def add_player(self, id):
        self.players[id-1] = Player(id, "")

    def check_everyone_in_game(self):
        for i, state in range(self.player_cap):
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
        for i, state in range(self.player_cap):
            if (i+1) not in nums and state["head"] == "up" and self.players[i]:
                return False
        return True

    def assign_roles(self):
        #this can be edited to make it less hardcoded
        self.mafiaOne, self.doctorNum = random.sample(range(1,self.player_cap+1), 2)
        self.players[self.mafiaOne-1].isMafia = True
        #self.players[self.mafiaTwo].isMafia = True
        self.players[self.doctorNum-1].isDoctor = True

    def handle_kill(self):
        victim = self.players[self.doctorNum-1].last_signal["save"]
        if not self.players[victim-1].isAlive:
            print("Player is already Dead")
            return -1
        if victim:
            print(f"Doctor Saved Player {victim}")
            self.players[self.mafiaOne-1].last_signal["kill"] = None
            return victim
        return -1
        
    def handle_save(self):
        patient = self.players[self.doctorNum-1].last_signal["save"]
        if not self.players[patient-1].isAlive:
            print("Player is already Dead")
            return -1
        if patient:
            print(f"Doctor Saved Player {patient}")
            self.players[self.doctorNum-1].last_signal["save"] = None
            return patient
        return -1

    """
   def everyone_voted(self):
        
        Returns true if everyone has voted
        
        for i, state in enumerate(self.last_signal):
            # print(state)
            if state["vote"] == None and self.alive[i]: # if you are alive and haven't voted
                return False
        return True
    def handle_vote(self):
        
        Check who has the most votes, return that person
        
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
    """
    def valid_signal(self, signal: Dict[str, Union[str, int]]):
        """Check if the signal action is allowed in this state"""
        if "action" not in signal:
            return False
        return signal["action"] in self.expected_signals

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
            self.assign_roles()
            for socket, player_id in self.clients.items():
                if player_id == self.mafiaOne:
                    send_json(socket, player_id, "mafia", None)
                elif player_id == self.doctorNum:
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

            if not self.check_heads_down([self.mafiaOne]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT MAFIA")
            else:
                # print("MAFIA, signal who to kill")
                victim = self.handle_kill()
                if victim != -1:
                    self.kill = victim
                    # mafia chose to kill someone, say that they are killed
                    self.expected_signals = {"headDown", "headUp"}
                    print("MAFIA VOTE READ, MOVING ON")
                    if self.doctorNum == -1:
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
            if not self.check_heads_down([self.doctorNum]):
                print("EVERYONE NEEDS TO HAVE THEIR HEAD DOWN EXCEPT DOCTOR")
            else:
                print("DOCTOR, signal who to save")
                patient = self.handle_save()
                if patient != -1:
                    self.save = patient
                    # doctor chose to save someone, say that they are alive 
                    self.expected_signals = {}
                    print("DOCTOR VOTE READ, MOVING ON")
                    print("EVERYONE put their heads up")
                    self.state = "RESOLVE"

        if self.state == "RESOLVE":
            if self.save != self.kill:
                self.players[self.kill-1].isAlive = False
            self.state = "NARRATE"

        if self.state == "NARRATE":
            print(f"IN THE NIGHT, THE MAFIA CHOSE TO KILL...")
            time.sleep(2)
            print(f"PLAYER {self.kill}")
            time.sleep(1)
            if self.save == self.kill:
                print("BUT...")
                time.sleep(1)
                print(f"THEY WERE SAVED BY THE DOCTOR")
            else:
                print(f"Unfortunately they were not saved")
            time.sleep(2)
            """
            if self.check_game_finished():
                print(f"DRUM ROLL...")
                time.sleep(2)
                print(f"MAFIA WINS!")
                self.state = "FINISHED"
                return
            """
            self.save = -1
            self.kill = -1
            print("NOW IT IS THE VOTING STAGE, SAY WHEN YOU ARE READY TO VOTE AND IT WILL BEGIN")
            command = listen_for_command()
            if command == "ready to vote":
                print("YOU MAY NOW SIGNAL WHO TO VOTE")
                self.expected_signals = {"targeted"}
                self.state = "VOTE"
        """
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
        """
        if self.state == "FINISHED":
            pass
