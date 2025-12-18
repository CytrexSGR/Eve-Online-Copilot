#!/bin/bash
# Cron job for updating production economics data
# Runs every 30 minutes to keep economics data fresh
#
# Add to crontab:
# */30 * * * * /home/cytrex/eve_copilot/jobs/cron_production_economics.sh

cd /home/cytrex/eve_copilot

# Run updater for The Forge (Jita)
python3 -m jobs.production_economics_updater --region=10000002 --limit=1000 >> /home/cytrex/eve_copilot/logs/production_economics.log 2>&1

echo "Economics update completed at $(date)" >> /home/cytrex/eve_copilot/logs/production_economics.log
