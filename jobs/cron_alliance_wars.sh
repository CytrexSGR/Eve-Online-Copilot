#!/bin/bash
# Alliance War Tracker - Runs every 30 minutes
# Tracks active alliance conflicts with kill/death ratios

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"
python3 jobs/telegram_alliance_wars.py >> logs/alliance_wars.log 2>&1
