## Game logic
from game import Game
from typing import List
import sys



if __name__ == "__main__":
    Mafia = Game(sys.argv[1:])
    Mafia.headsDown()

