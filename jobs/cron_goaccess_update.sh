#!/bin/bash
# Update GoAccess web analytics report

LOGFILE="/home/cytrex/eve_copilot/logs/goaccess_update.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting GoAccess report update..." >> "$LOGFILE"

# Generate GoAccess HTML report
echo 'Aug2012#' | sudo -S goaccess /var/log/nginx/access.log \
    --log-format=COMBINED \
    --output=/var/www/html/stats.html \
    >> "$LOGFILE" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ GoAccess report updated successfully" >> "$LOGFILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ GoAccess report update failed" >> "$LOGFILE"
fi
