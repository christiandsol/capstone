# Table of Contents

# Introduction

# System Requirements

# Setup and Installation Instructions

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
  - Function: Indicates you are ready to proceed to the voting phase during the game, after discussing with fellow players. This is where you vote out the Mafia.

Say these commands clearly while the voice recognition is active. The system will listen for these phrases and automatically perform the corresponding game action.

## Gesture

# Known Issues and Troubleshooting
