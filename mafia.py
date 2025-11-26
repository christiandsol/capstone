## Game logic
from game import Game
from typing import List
from player import Player
import voice
import sys

night_phase = False
day_phase = False
voting_phase = False
mafias = []

game = Game(["-n","10"])

#Setup Phase
#Everyone put head down
#Random player chosen as mafia
#Random player chosen as nurse
#
while True:
    #End condition checks throughout where if mafia == civilians, game end
    #Night Phase
    night_phase = True
    while night_phase == True:
        night_phase = False
        #while in night, keep checking to make sure everyone is face down
        #computer tells mafia to face up and gesture who they want to kill
        #mafia gestures and puts head down
        #computer tells nurse to face up and gesture who they want to save
        #nurse gestures and puts head down
        #computer tells everyone to put face up
    while day_phase == True:
        voice.listen_for_okay_mafia()
        #Storytelling Aspect for Q2
        #if some voice command said
            #day_phase = False
            #voting_phase = True

    #Day Phase
        #computer will tell story of previous night
        #Voice command to go onto voting phase
    #Voting Phase
    while voting_phase == True:
        #Players gesture to indicate who they vote for
        #Amount of votes for players shown on display screen
        #If Majority, player gets voted out and continue to night phase
        #Else continue to night phase


#if __name__ == "__main__":
#    Mafia = Game(sys.argv[1:])
#    Mafia.headsDown()

