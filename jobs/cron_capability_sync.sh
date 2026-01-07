#!/bin/bash
# Capability Sync Cron Job
cd /home/cytrex/eve_copilot
source /home/cytrex/eve_copilot/venv/bin/activate 2>/dev/null || true
python3 jobs/capability_sync.py >> /home/cytrex/eve_copilot/logs/capability_sync.log 2>&1

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"
