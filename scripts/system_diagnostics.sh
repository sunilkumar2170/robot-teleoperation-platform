#!/usr/bin/env bash
# Teleop-Sim Linux Diagnostics Script
# Safe, read-only system inspection without requiring root permissions.
set -e

echo "============================================="
echo "   Teleop-Sim Linux System Diagnostics       "
echo "============================================="
echo "Date/Time: $(date -u)"
echo ""

echo "--- 1. Linux Distribution ---"
if [ -f /etc/os-release ]; then
    grep -E '^(PRETTY_NAME|NAME|VERSION)=' /etc/os-release || cat /etc/os-release
elif command -v lsb_release >/dev/null 2>&1; then
    lsb_release -a
else
    uname -s
fi
echo ""

echo "--- 2. Kernel Version ---"
uname -srmo
echo ""

echo "--- 3. CPU Information ---"
if [ -f /proc/cpuinfo ]; then
    echo "Model: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^[ \t]*//')"
    echo "Cores: $(grep -c '^processor' /proc/cpuinfo)"
elif command -v lscpu >/dev/null 2>&1; then
    lscpu | grep -E 'Model name|CPU\(s\):'
else
    echo "CPU info not directly accessible."
fi
echo ""

echo "--- 4. Memory Usage ---"
if command -v free >/dev/null 2>&1; then
    free -m
else
    echo "free command not found."
fi
echo ""

echo "--- 5. Disk Usage ---"
df -h . || df -h
echo ""

echo "--- 6. Backend Process Status ---"
if command -v pgrep >/dev/null 2>&1; then
    PIDS=$(pgrep -f "uvicorn.*app.main:app" || true)
    if [ -n "$PIDS" ]; then
        echo "Backend process detected running with PID(s): $PIDS"
        ps -fp $PIDS || true
    else
        echo "No Teleop-Sim backend process currently running."
    fi
else
    ps aux | grep "[u]vicorn app.main:app" || echo "No Teleop-Sim backend process detected."
fi
echo ""

echo "--- 7. Port 8000 Availability ---"
if command -v ss >/dev/null 2>&1; then
    ss -tlpn | grep ':8000 ' || echo "Port 8000 is free (not listening)"
elif command -v netstat >/dev/null 2>&1; then
    netstat -tlpn 2>/dev/null | grep ':8000 ' || echo "Port 8000 is free (not listening)"
else
    echo "Neither ss nor netstat found."
fi
echo ""

echo "--- 8. Docker Status ---"
if command -v docker >/dev/null 2>&1; then
    docker --version 2>&1 || true
    if docker info >/dev/null 2>&1; then
        echo "Docker daemon: Active & Reachable"
    else
        echo "Docker daemon: Not reachable or WSL integration not activated."
    fi
else
    echo "Docker is not installed."
fi
echo "============================================="
exit 0
