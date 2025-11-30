## Game logic
from game import Game
from typing import List
from player import Player
import voice
import random
import sys

night_phase = False
day_phase = False
voting_phase = False
mafias = []
civilians = []
innocentsAlive = 8
mafiaAlive = 2

game = Game(["-n","10"])
mafiaOne, mafiaTwo, doctorNum = random.sample(range(1, 11), 3)
for playerNum in range(game.numPeople):
    if (playerNum == mafiaOne or playerNum == mafiaTwo):
        newPlayer = Player(playerNum, "", True, False, True)
        mafias.append(newPlayer)
    elif (playerNum == doctorNum):
        newPlayer = Player(playerNum, "", False, True, True)
        civilians.append(newPlayer)
    else:
        newPlayer = Player(playerNum, "", False, False, True)
        civilians.append(newPlayer)

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
        #final check of night phase for win conditions
        if mafiaAlive >= innocentsAlive:
            #mafia win screen
            pass
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
        #final check of voting phase for win conditions
        if mafiaAlive >= innocentsAlive:
            #mafia win screen
            pass
        elif mafiaAlive == 0:
            #civilian win screen
            pass


#if __name__ == "__main__":
#    Mafia = Game(sys.argv[1:])
#    Mafia.headsDown()

