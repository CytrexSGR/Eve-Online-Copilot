#!/bin/bash
# EVE Co-Pilot Sovereignty Tracker Cronjob
# Fetches sovereignty campaigns from ESI every 30 minutes

cd /home/cytrex/eve_copilot

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/sov_tracker.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run sovereignty tracker
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting sovereignty tracker" >> $LOG_FILE
python3 -m jobs.sov_tracker >> $LOG_FILE 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') - Sovereignty tracker complete" >> $LOG_FILE
echo "" >> $LOG_FILE
