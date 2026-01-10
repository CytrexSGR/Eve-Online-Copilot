#!/bin/bash
# Report Pre-Generator - Runs every 6 hours
# Pre-generates all intelligence reports so they're always cached
# Crontab: 0 */6 * * * /home/cytrex/eve_copilot/jobs/cron_report_generator.sh

cd /home/cytrex/eve_copilot
source /home/cytrex/.env 2>/dev/null || true

python3 jobs/report_generator.py >> /home/cytrex/eve_copilot/logs/report_generator.log 2>&1
