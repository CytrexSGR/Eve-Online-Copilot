#!/bin/bash
# War Profiteering Daily Digest - Runs daily at 06:00 UTC
# Identifies market opportunities from destroyed items in combat

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"
python3 jobs/telegram_war_profiteering.py >> logs/war_profiteering.log 2>&1
