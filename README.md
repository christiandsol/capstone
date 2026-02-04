

# Server-side/deployment  READ EVERYTHING
First I think it's important to know what each file is for. 
1. whatever is in the folder fronted/smart-mafia is the frontend, that'll just be ran
2. It's important to understand the motivation of the file debug_player.py:
- the file is ran like this: `python debug_player.py <player_name>`
- This file is intended for lazy purposes, I created it because it was annoying to have to ssh to the raspberry pi and change stuff there rather than locally, and also it was also annoyign to have to have everyone present in order to debug game logic. So I created this file to simulate separate raspberry pi instances. I.e, if you run this file in three different terminal instances ENSURING you pass in three different names as arguments, then you are simulating three separate raspberry pi instances of each of these players, and you can test game logic and server send and receive signals from this. The alternative is to run the `rasbpi.py` file, in the raspberry pi or not, but then you can only simulate one connection, so this is a much better alternative for debugging
3. Updating the right things: 
- ensure that if you are testing locally, then you have this resolved IP uncommented in smart-mafia/src/pages/Rpi.tsx:

  console.log(`player name: ${playerName}`)
  // const resolvedIp = ip_addr;
  // NOTE: HERE uncomment the resolved IP line if you don't want to use raspberry pi and you are debugging
  const resolvedIp = import.meta.env.DEV
    ? "127.0.0.1"
    : ip_addr;
4. In `debug_player.py` and `rasbpi.py`, the server IP is just ste to the default local host, which is good for when you are debuggin which is what this whole section is about:
    SERVER_IP = "127.0.0.1"
But for when you run it on the raspberry pi, you actually need to replace this with your machines IP address


## Tutorial on running in to debug it;

ENSURE THAT YOU HAVE READ THE PREVIOUS SECTION

Steps you need to do and in what order if you are debugging
1. run: python server.py
    - this just runs the server code, which is waiting for connections
2. run, in another terminal instance: node server.ts
    - this runs the server that is in charge of room connections whenever someone joins the room
    - first you must know how many players you are simulating, right now it's defaulted to 3 players
3. Now, if you are going to debugging and simulating a game on your own, meaning you have no other group mates to open up their own rasbpi, then you need to run `python debug_player.py <player_name>` in multiple terminal instances. The number of terminal instances is tied to exactly the number of people you have in your game, which is specified in server.py  when you initialize mafia game: `game = MafiaGame(3)`, right now it's three, which I think we should keep it at because it allows us to debug well. KEEP the player_names in your head, because this is a debug file, it's not as clean as how it's done in rasbpi.py where it gets the name from the frontend, you are essentially hard-coding the names on the rasbpi to send to the backend, but by doing this you unlock the ability to simulate multiple raspberry pi's, so it's worth it.
4. Now, you can `npm run dev` in frontend/smart-mafia to run the website on localhost
5. now you can open up `x` tabs, where `x` is the number of players the mafia game is, defaulted to 3 right now. In each tab now, you can enter each player name that you've remembered from the one's you've done in debug_player.py to register them and join a game with them. After you've clicked join game for each player, you should see a screen that asks for your raspberry pi's address. Since you're on local and sinc'e you've uncommented the proper line in instruction 3 in the previous section, it'll just default to localhost, which is where you should be running to debug. But if you are actaully testing on the raspberry pi, you actually have to put the raspberry pi's ip address there to connect to it. If you are debugging without the raspberry pi to simulate a game of multiple people, you can just go ahead and click join game for each of the tabs
6. The server should have already recognized by this point that players and raspberry pi's have been connected. When everyone joins the game, the server.py terminal output should say that everyone has joined. Now, for the camera, since you're debuggin on your own, you can't have multiple simultaneous camera's on you  for the multiple players you're meant to be simulating, since your machine likely only has one camera. However, you can go ahead and, for one player, start the camera, and for the rest, you should click the option to use a test video and start the test vidoe for each of them.
7. Now, you should be able to see not only your face but also the other test videos (may be laggy but that's fine). Once you put your head down, the server should move on to the first mafia vote stage, and for the terminal instance of debug_player.py, one of them should be the mafia, and it should give you an input command waiting for the id of the player that they want to kill. Type and press enter and it should send it to the server. Now you can just follow the logic in server.py and vote when necessary to start debuggin the game logic or anything else based on the signals sent. 

# Usage

## Camera activating tutorial

To be able to use our application, you must allow it to use our camera, but because (as of right now), we are using the http protocol rather than the https protocol, when viewing our application, it won't prompt you permission to use your camera and will instead block it. We need to bypass this, we will give you a tutorial here. It is possible among all browsers to do this, but it's easiest for chrome, and we assume almost everyone uses and if not has chrome downloaded. If you are using another browser, please look up 'How to allow non secure http website camera access'. Now on with the tutorial. 

Before joining our website, look up on your google chrome search bar `chrome://flags/#unsafely-treat-insecure-origin-as-secure` and enable the flag. You must also type in or paste our website address here: `http://163.192.0.247`. Now you must restart chrome, there should be some sort of button that shows when you have enabled the flag to do so, do so. Now you have everything you need to be able to start

## Using the platform

Now you can go ahead and visit [our website]http://163.192.0.247 and start a game!

