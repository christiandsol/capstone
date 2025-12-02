## Game logic
from typing import List
from player import Player
from voice import listen_for_command
from typing import Dict, Union, List
import voice
import random
import sys

mafiaOne = None
mafiaTwo = None
doctorNum = None

class Game:
    def __init__(self):
        self.phase = "PRESETUP"
        self.players= {}
        self.votes = {}
        self.kill = None
        self.heal = None
        self.last_signal = {}
        self.expected_signals = {"setup"}
        self.player_cap = 7

    def add_player(self, id):
        self.players[id] = Player(id, "", False, False, True)

    def assign_roles(self):
        mafiaOne, doctorNum = random.sample(range(1,self.player_cap), 2)
        self.players[mafiaOne].isMafia = True
        self.players[mafiaTwo].isMafia = True
        self.players[doctorNum].isDoctor = True

    def handle_kill(self, mafia_id, target_id):
        if self.phase != "MAFIANIGHT":
            return None

        mafia = self.players.get(mafiaOne)
        if not mafia.isAlive or not mafia.isMafia:
            return None
        
        victim = self.players.get(target_id)
        if not victim.isAlive or victim.isMafia:
            return None
        
        self.kill = target_id
        return None

    def handle_save(self, target_id):
        if self.phase != "DOCTORNIGHT":
            return None
        
        doctor = self.players.get(doctorNum)
        if not doctor.isAlive or not doctor.isDoctor:
            return None
        
        patient = self.players.get(target_id)
        if not patient.isAlive:
            return None
        
        self.heal = target_id
        return None

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
