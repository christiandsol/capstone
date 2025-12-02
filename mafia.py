## Game logic
from typing import List
from player import Player
from voice import listen_for_command
from typing import Dict, Union, List
import voice
import random
import sys

class Game:
    def __init__(self):
        self.phase = "PRESETUP"
        self.players= {}
        self.votes = {}
        self.kill = None
        self.heal = None
        self.last_signal = {}
        self.expected_signals = {"setup"}
        self.player_cap = 10

    def add_player(self, id):
        self.players[id] = Player(id, "", False, False, True)

    def assign_roles(self):
        mafiaOne, mafiaTwo, doctorNum = random.sample(range(1, 11), 3)
        self.players[mafiaOne].isMafia = True
        self.players[mafiaTwo].isMafia = True
        self.players[doctorNum].isDoctor = True

    def handle_kill(self, mafia_id, target_id):
        

    def handle_save(self, doctor_id, target_id):


    def valid_signal(self, signal: Dict[str, Union[str, int]]):
        """Check if the signal action is allowed in this state"""
        return signal["action"] in self.expected_signals

    def update(self, signal_queue: List[Dict[str, Union[str,int]]]):
        """
        Consume only the signals that matter for the current state.
        Ignore or discard others.
        """

        if self.phase == "PRESETUP":
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
                    self.phase = "NIGHTMAFIA"
                    self.expected_signals = {"headUp", "headDown"}

        elif self.phase == "NIGHTMAFIA":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Night Mafia Signal] {sig}")

        elif self.phase == "NIGHTDOCTOR":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Night Doctor Signal] {sig}")

        elif self.phase == "DAY":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Day Signal] {sig}")

        elif self.phase == "VOTE":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Vote Signal] {sig}")
