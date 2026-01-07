#!/bin/bash
# EVE Co-Pilot Faction Warfare Tracker Cronjob
# Tracks FW system status and detects hotspots

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/fw_tracker.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run FW tracker
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting FW tracker" >> $LOG_FILE
python3 -m jobs.fw_tracker >> $LOG_FILE 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') - FW tracker complete" >> $LOG_FILE
echo "" >> $LOG_FILE
