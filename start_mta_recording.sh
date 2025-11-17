#!/bin/bash

# Log file path
LOG_FILE="/tmp/timer_log.txt"

# Start time
echo "Timer started at: $(date)" >> "$LOG_FILE"

# Infinite loop
SECONDS_ELAPSED=0
while true; do
    SECONDS_ELAPSED=$((SECONDS_ELAPSED + 1))
    echo "Elapsed time: ${SECONDS_ELAPSED}s" >> "$LOG_FILE"
    sleep 1
done
