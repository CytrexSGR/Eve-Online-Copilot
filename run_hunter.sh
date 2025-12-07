#!/bin/bash
# EVE Co-Pilot Market Hunter Runner
# Run this script via cron to automate market scanning

# Configuration
COPILOT_DIR="/home/cytrex/eve_copilot"
LOG_DIR="${COPILOT_DIR}/logs"
LOG_FILE="${LOG_DIR}/hunter_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Change to project directory
cd "${COPILOT_DIR}"

# Run the market hunter
echo "=== Market Hunter Started: $(date) ===" >> "${LOG_FILE}"
python3 -m jobs.market_hunter >> "${LOG_FILE}" 2>&1
EXIT_CODE=$?
echo "=== Market Hunter Finished: $(date) (exit: ${EXIT_CODE}) ===" >> "${LOG_FILE}"

# Keep only last 7 days of logs
find "${LOG_DIR}" -name "hunter_*.log" -mtime +7 -delete

exit ${EXIT_CODE}
