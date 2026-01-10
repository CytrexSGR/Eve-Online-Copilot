#!/bin/bash
# Strategic Briefing Generator - Runs every 6 hours
# Crontab: 0 */6 * * * /home/cytrex/eve_copilot/jobs/cron_strategic_briefing.sh

cd /home/cytrex/eve_copilot
source /home/cytrex/.env 2>/dev/null || true

python3 jobs/strategic_briefing_generator.py >> /home/cytrex/eve_copilot/logs/strategic_briefing.log 2>&1
