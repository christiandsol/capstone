
# TODO

# Global TODO: 
- raspberry pi integration? (Almost done?)
    - hwo to get role if you just immediately connect?
    - it would be a good idea to have a component that changes it's value simply based off server inputs
    - JUST added playerID
- have names show up alongside players (as well as their status of alive or dead)
    - have server send when someone dies
- narration to everyone, how are we doing that?
- join room/start game maybe add it back?
- dynamic mafia's/players?
- Game completion? Re-do game?
- How to handle player_id's?

- Where you left off:
    - just received the role on raspberry pi end, now you can go ahead and send over the role to handle it on the server end

Kirt:
Finish game logic for more players
Add skeleton for play page

Christian: 
- [x] Connect to a web server
- [x] deploy
- Raspberry pi support:
- How are you going to make the raspberry pi get the proper role and player name?
    - you need the rpi to connect to the server and wait for a given name
    - How can I make both the heads up and heads down signal as well as the rpi signal appear as one?

Selena:
- [ ] start website frontend, hosted locally, build skeleton of home page

Jesus:
- [ ] Adding gesture recognition to allow up to 8 players
- [ ] Modify existing gesture to be able to support drawing a number 1-8 and recognize it to vote for a player



## INITIALIZATION SETUP NOTES:
/usr/bin/python3.7 -m pip install flask flask-cors websockets?


