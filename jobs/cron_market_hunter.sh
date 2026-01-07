#!/bin/bash
# EVE Market Hunter Cronjob
# Läuft alle 5 Minuten

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"
/usr/bin/python3 -m jobs.market_hunter --top 15 --max-difficulty 3 >> /home/cytrex/eve_copilot/logs/market_hunter.log 2>&1
