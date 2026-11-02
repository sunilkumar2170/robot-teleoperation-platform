#!/usr/bin/env bash
# Teleop-Sim Graceful Stop Script
# Ensures signals are only delivered to verified Teleop-Sim processes.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/teleop-sim.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found ($PID_FILE). Teleop-Sim is not running."
    exit 0
fi

PID=$(cat "$PID_FILE")

# Verify that PID exists
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID is not running. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 0
fi

# Safety check: Verify the PID actually belongs to Teleop-Sim / uvicorn / Python
# Inspect cmdline from /proc/$PID/cmdline or ps to prevent killing recycled or unrelated PIDs
IS_TELEOP_PROCESS=false

if [ -f "/proc/$PID/cmdline" ]; then
    CMDLINE=$(tr '\0' ' ' < "/proc/$PID/cmdline")
    if [[ "$CMDLINE" == *"app.main:app"* ]] || [[ "$CMDLINE" == *"teleop-sim"* ]]; then
        IS_TELEOP_PROCESS=true
    fi
elif command -v ps >/dev/null 2>&1; then
    CMDLINE=$(ps -p "$PID" -o args= 2>/dev/null || true)
    if [[ "$CMDLINE" == *"app.main:app"* ]] || [[ "$CMDLINE" == *"teleop-sim"* ]]; then
        IS_TELEOP_PROCESS=true
    fi
fi

if [ "$IS_TELEOP_PROCESS" = false ]; then
    echo "SAFETY ERROR: Process $PID does not match Teleop-Sim command signature ('$CMDLINE')."
    echo "Refusing to send signals to unrelated process. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 1
fi

echo "Verified process $PID belongs to Teleop-Sim."
echo "Sending SIGTERM (signal 15) to Teleop-Sim process $PID..."
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

echo "Process $PID did not terminate after 10s. Verifying PID before SIGKILL..."
# Re-verify before SIGKILL in case PID was immediately re-allocated
if [ -f "/proc/$PID/cmdline" ]; then
    CMDLINE=$(tr '\0' ' ' < "/proc/$PID/cmdline")
    if [[ "$CMDLINE" != *"app.main:app"* ]] && [[ "$CMDLINE" != *"teleop-sim"* ]]; then
        echo "PID $PID is no longer Teleop-Sim. Aborting SIGKILL."
        rm -f "$PID_FILE"
        exit 1
    fi
fi

echo "Sending SIGKILL (signal 9) to process $PID..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Teleop-Sim process terminated."
