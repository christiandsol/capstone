
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
Server (RUN FIRST, only need one laptop for this):
```python server.py```

(in a separate instance) Pose recognition client:
```python poserecognition.py```

