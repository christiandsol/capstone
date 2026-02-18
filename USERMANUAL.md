# Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Setup and Installation Instructions](#setup-and-installation-instructions)
4. [User Interface Overview](#smart-mafia-user-interface-overview)
5. [Specific Features](#specific-features)
   - [Voice](#voice)
   - [Gesture](#gesture)
6. [Known Issues and Troubleshooting](#known-issues-and-troubleshooting)
# Introduction

This document will cover everything revolving Smart Mafia. This includes the system requirements needed to run it, the setup and install instructions to use the product, and an overview on the UI and specific features people need to know while playing the game. Finally, this document covers known issues and how to quickly troubleshoot them.

# System Requirements
## Software
Ensure that you are running the application on: 
- either Chrome or Safari browser, that is what was tested with
- Ensure that your raspberry pi is running python3.7, check `which python`, if it's not 3.7, I chech `ls /usr/bin/python3.7` to see if it exists, if so, run that python
## Raspberry pi
- For more detail on setup and install, look at the next section

# Setup and Installation Instructions

The frontend and server is already running and acessible at mafiacapstone.duckdns.org.

## Raspberry Pi Setup

To use the Raspberry Pi client for the Mafia game, you'll need to SSH into your Raspberry Pi and clone the repository. First, establish an SSH connection to your Raspberry Pi using your credentials (e.g., `ssh pi@YourPINAME.local`). Once connected, clone the `notify-restart` branch from the repository using the command `git clone -b notify-restart https://github.com/christiandsol/capstone.git capstone`. After cloning, navigate into the repository directory using `cd capstone`. 

Before running the script, ensure you have Python 3.9 or higher installed (check with `python3 --version`). If you don't have `pip3` installed, install it using `sudo apt update && sudo apt install python3-pip`. Once pip3 is installed, install the required `websockets` library using `pip3 install websockets`. Make sure your BerryIMU hardware is properly connected to the Raspberry Pi via I2C(Should be done if you completed Lab1-3 last quarter). Once everything is set up, you can start the client by running `python3 rasbpi.py "player_Name"`, replacing `"player_Name"` with your actual player name (e.g., `python3 rasbpi.py "Jesus"`). The script will connect to the game server at `mafiacapstone.duckdns.org` and prompt you to choose between using the Raspberry Pi with gesture recognition (type 'y') or local debugging mode where you type numbers manually (type 'n'). When the server requests a vote during gameplay, follow the on-screen prompts to record your gesture or enter your vote.


# Smart Mafia User Interface Overview


The Smart Mafia user interface is a web application. The main UI components are:

- **Landing Page / Lobby:**
  - Players enter their name to join the game.
  - "Join Game" button to proceed.

- **Game Room:**
  - Displays game state, player info, role, head position, and voice command status.
  - Lobby status and player readiness display before game starts.
  - Video controls to start camera.
  - Voice controls for starting/stopping voice command recognition and muting/unmuting microphone.
  - Video streams for each player, including ID number and status (dead players indicated by a skull emoji).
  - Game over screen displayed at the end with winner announcement and option to restart game.


# Specific Features

## Voice

The Smart Mafia game supports the following voice commands:

- **"assign players"**
  - Function: Marks you as ready and triggers the assignment of player roles. Use this command when you are in the lobby and want to start the game. Each player in the lobby needs to use this command before the roles are assigned.

- **"ready to vote"**
  - Function: Indicates you are ready to proceed to the voting phase during the game, after discussing with fellow players. This is where you vote who you think is the Mafia

Say these commands clearly while the voice recognition is active. The system will listen for these phrases and automatically perform the corresponding game action.

## Gesture

The Smart Mafia game supports gesture-based voting using the BerryIMU. Players can gesture for digits 1-8 with the BerryIMU to vote for specific players. The gesture directions are mapped as follows:

- **Digit 1:** Right 
- **Digit 2:** Down
- **Digit 3:** Left
- **Digit 4:** Up
- **Digit 5:** Up-Right (diagonal)
- **Digit 6:** Down-Right (diagonal)
- **Digit 7:** Down-Left (diagonal)
- **Digit 8:** Up-Right (diagonal)

The `berryIMU/gesturetwo.py` file can be run independently to test gesture recognition and IMU functionality without connecting to the full game server. To use it, navigate to the repository directory cd berryIMU and check for file `gesturetwo.py`. Then run `python3 gesturetwo.py`. The script will start in interactive mode where you can press Enter to record a gesture, move the BerryIMU to signal a direction (1-8), and the system will recognize and optionally send a vote to the server. If the server is not running, the script will still recognize gestures and print what vote would have been sent, making it useful for testing gesture recognition independently. Slower movements will result in 1-4 while faster movements will result in diagonals. 

# Known Issues and Troubleshooting

One small issue we ran into on one computer was sometimes the microphone not connecting immediately. This can be quickly fixed by switching the audio device being used by the website and then switching back to the original device you want.

One other issue we had was not running the rasbpi script before starting the game. This would make it so that the player would be unable to perform any action during the game. Overall, this is a quick fix by disconnecting the player and reconnecting. Since this is at the beginning of the of the game, there should be no issue in restarting the game at this point.

While disconnects for the most part have been fixed, if one were to disconnect, the game should end and all the players can refresh and reconnect.
