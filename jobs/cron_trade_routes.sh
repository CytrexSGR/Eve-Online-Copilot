#!/bin/bash
# Trade Route Danger Map - Runs daily at 08:00 UTC
# Analyzes danger levels along major trade routes

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"
python3 jobs/telegram_trade_routes.py >> logs/trade_routes.log 2>&1
