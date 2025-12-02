## Game logic
from typing import List
from player import Player
from voice import listen_for_command
from typing import Dict, Union, List
import voice
import random
import sys

night_phase = False
day_phase = False
voting_phase = False
mafias = []
civilians = []
civiliansAlive = 8
mafiaAlive = 2

class Game:
    def __init__(self):
        self.phase = "PRESETUP"
        self.players= {}
        self.votes = {}
        self.kill = None
        self.heal = None
        self.last_signal = {}
        self.expected_signals = {"setup"}

    def add_player(self, id):
        self.players[id] = Player(id, "", False, False, True)

    def assign_roles(self):
        mafiaOne, mafiaTwo, doctorNum = random.sample(range(1, 11), 3)
        self.players[mafiaOne].isMafia = True
        self.players[mafiaTwo].isMafia = True
        self.players[doctorNum].isDoctor = True

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
                    self.state = "NIGHT"
                    self.expected_signals = {"headUp", "headDown"}

        elif self.phase == "NIGHT":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Night Signal] {sig}")

        elif self.phase == "DAY":
            while signal_queue:
                sig = signal_queue.popleft()
                print(f"[Day Signal] {sig}")
