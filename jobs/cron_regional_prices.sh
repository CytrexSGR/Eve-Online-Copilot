#!/bin/bash
# EVE Co-Pilot Regional Price Fetcher Cronjob
# Fetches market prices from ESI for all regions
# Runs every 30 minutes

cd /home/cytrex/eve_copilot

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/regional_prices.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run price fetcher
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting regional price fetch" >> $LOG_FILE
python3 -m jobs.regional_price_fetcher >> $LOG_FILE 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') - Regional price fetch complete" >> $LOG_FILE
echo "" >> $LOG_FILE
