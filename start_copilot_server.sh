#!/bin/bash
# Start EVE Co-Pilot AI Server

echo "Starting EVE Co-Pilot AI Server..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start server
cd "$(dirname "$0")"
python3 -m uvicorn copilot_server.main:app --host ${COPILOT_HOST:-0.0.0.0} --port ${COPILOT_PORT:-8001} --reload
