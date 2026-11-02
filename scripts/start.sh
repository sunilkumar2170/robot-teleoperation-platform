#!/usr/bin/env bash
# Teleop-Sim Startup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/teleop-sim.pid"
LOG_FILE="$PROJECT_ROOT/logs/application.log"

cd "$PROJECT_ROOT"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Teleop-Sim is already running with PID $PID."
        exit 0
    fi
fi

mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/data"

echo "Starting Teleop-Sim backend..."
export PYTHONPATH="$PROJECT_ROOT/backend"

# Run in background and record PID
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

echo "Teleop-Sim backend started with PID $PID (listening on port 8000)."
