#!/usr/bin/bash
# Activate conda environment
source /home/opc/miniconda3/etc/profile.d/conda.sh
conda activate capstone

# Change to project directory
cd /home/opc/capstone

# Run your Python server
exec python server.py
