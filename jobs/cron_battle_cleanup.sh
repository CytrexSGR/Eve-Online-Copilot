#!/bin/bash
cd /home/cytrex/eve_copilot
python3 jobs/battle_cleanup.py >> logs/battle_cleanup.log 2>&1
