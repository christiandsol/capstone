## Game logic
from game import Game
from typing import List
import sys
#Setup Phase
#Everyone put head down
#Random player chosen as mafia
#Random player chosen as nurse
#
#While (true) {
#End condition checks throughout where if mafia == civilians, game end
#Night Phase
    #while in night, keep checking to make sure everyone is face down
    #computer tells mafia to face up and gesture who they want to kill
    #mafia gestures and puts head down
    #computer tells nurse to face up and gesture who they want to save
    #nurse gestures and puts head down
    #computer tells everyone to put face up
#Day Phase
    #computer will tell story of previous night
    #Voice command to go onto voting phase
#Voting Phase
    #Players gesture to indicate who they vote for
    #Amount of votes for players shown on display screen
    #If Majority, player gets voted out
    #Else continue to night phase
#}

if __name__ == "__main__":
    Mafia = Game(sys.argv[1:])
    Mafia.headsDown()

