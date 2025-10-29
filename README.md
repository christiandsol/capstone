
# Manual

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
For right now, we only have the argument -n supported, for number of people in the game, assuming one mafia, so we run like: 
```python mafia.py -n <numberofpeopleyouwant>```


