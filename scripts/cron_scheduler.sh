#!/bin/bash
# Cron Wrapper for Smart Scheduler
# Call this from Synology Task Scheduler every 30 minutes

set -e

# Configuration
PHOTONER_DIR="/volume1/photos/photoner"
CONFIG_FILE="${PHOTONER_DIR}/config/config.production-nas.yaml"
VENV_DIR="${PHOTONER_DIR}/venv"
LOCKFILE="/tmp/photoner_scheduler.lock"

# Logging
LOG_DIR="/volume1/photos/logs"
CRON_LOG="${LOG_DIR}/cron_scheduler.log"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${CRON_LOG}"
}

# Check if already running (prevent overlapping runs)
if [ -f "${LOCKFILE}" ]; then
    PID=$(cat "${LOCKFILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        log "Scheduler already running (PID: ${PID}), skipping"
        exit 0
    else
        log "Stale lockfile found, removing"
        rm -f "${LOCKFILE}"
    fi
fi

# Create lockfile
echo $$ > "${LOCKFILE}"

# Cleanup on exit
cleanup() {
    rm -f "${LOCKFILE}"
}
trap cleanup EXIT

# Activate virtual environment
log "Activating virtual environment"
source "${VENV_DIR}/bin/activate"

# Run smart scheduler
log "Running smart scheduler"
python "${PHOTONER_DIR}/scripts/smart_scheduler.py" "${CONFIG_FILE}" 2>&1 | tee -a "${CRON_LOG}"

EXIT_CODE=$?

if [ ${EXIT_CODE} -eq 0 ]; then
    log "Scheduler completed successfully"
else
    log "Scheduler failed with exit code: ${EXIT_CODE}"
fi

exit ${EXIT_CODE}
