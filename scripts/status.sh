#!/usr/bin/env bash
# Teleop-Sim Status Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/teleop-sim.pid"

echo "=== Teleop-Sim Service Status ==="
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Status: RUNNING (PID: $PID)"
        echo "Port 8000 Check:"
        if command -v ss >/dev/null 2>&1; then
            ss -tulpn | grep 8000 || echo "Port 8000 listening"
        elif command -v netstat >/dev/null 2>&1; then
            netstat -tuln | grep 8000 || echo "Port 8000 listening"
        fi
        echo "Health Endpoint:"
        if command -v curl >/dev/null 2>&1; then
            curl -s http://localhost:8000/health || echo "Endpoint unreachable"
            echo ""
        fi
        exit 0
    else
        echo "Status: STOPPED (Stale PID file found)"
        exit 1
    fi
else
    echo "Status: STOPPED"
    exit 3
fi
