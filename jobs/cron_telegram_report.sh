#!/bin/bash
# Cron wrapper for Telegram 24h Battle Report
# Runs every 10 minutes

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"

# Run Python script
python3 jobs/telegram_battle_report.py >> logs/telegram_report.log 2>&1

# Log completion
echo "[$(date)] Telegram report sent" >> logs/telegram_report.log
