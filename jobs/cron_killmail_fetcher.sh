#!/bin/bash
cd /home/cytrex/eve_copilot
python3 -m jobs.killmail_fetcher >> logs/killmail_fetcher.log 2>&1
