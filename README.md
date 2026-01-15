
# Manual

# Finish Lab 3
# Set up Conda Environment
# 

## Arguments: 
- n <num>: number of people[Required]
- m <num>: number of mafias[Optional]
    - default = 1
- e: medic[Optional]
    - default = no medics


# Dependencies
- conda environment with: 
    - python 3.10 at least
    - openCV installed
    conda install -c conda-forge opencv
        ```conda install -c conda-forge opencv```
    - mediapipe installed (install in conda environment)
        ```pip install mediapipe```

# Running
Server (RUN FIRST, only need one laptop for this):
```python server.py```

(in a separate instance) Pose recognition client:
```python poserecognition.py```

Host website: run in the frontend/smart-mafia directory to launch: ```npm run dev```


# Voice Commands

- "okay mafia": computer constantly listens for this command, when heard starts listening for other commands, say "okay mafia" before any voice command input
- "assign roles": use this command when players are ready to start and receive their roles
    - after this command call assign roles function 
- "ready to vote": use this command when players are done discussing who to vote as mafia
    - after this command call gesture recognition start
- "the sun has set": use this command to start the night phase
    - call pose recognition to start, making sure all heads are down