#!/usr/bin/env bash
# Teleop-Sim Graceful Stop Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/teleop-sim.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found. Teleop-Sim does not appear to be running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Sending SIGTERM (15) to Teleop-Sim process $PID..."
    kill -15 "$PID"
    
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "Teleop-Sim stopped gracefully."
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    echo "Process did not terminate after 10s. Sending SIGKILL (9)..."
    kill -9 "$PID"
    rm -f "$PID_FILE"
    echo "Teleop-Sim process killed."
else
    echo "Process $PID is not running. Cleaning up stale PID file."
    rm -f "$PID_FILE"
fi
