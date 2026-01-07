#!/bin/bash
# EVE Co-Pilot Batch Calculator Cronjob
# Läuft alle 5 Minuten und aktualisiert manufacturing_opportunities

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/batch_calculator.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run batch calculator
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting batch calculation" >> $LOG_FILE
python3 -m jobs.batch_calculator >> $LOG_FILE 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') - Batch calculation complete" >> $LOG_FILE
echo "" >> $LOG_FILE
