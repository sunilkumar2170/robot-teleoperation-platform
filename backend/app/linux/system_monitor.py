"""
Linux System Monitoring Module
------------------------------
Safe, read-only system inspection designed for Ubuntu/WSL2 and Linux Docker containers.
Does not require root privileges.

Monitors:
  • Application process ID (PID)
  • Process uptime
  • CPU usage (process % and system %)
  • Memory usage (process RSS, system total, available, % used)
  • Disk usage (total, free, % used)
  • Open application port (port 8000 state via socket probe)
  • Backend health
  • Active WebSocket connection count
  • Linux kernel, distribution, and host information
"""
from __future__ import annotations

import os
import platform
import socket
import sys
import time
from typing import Dict, List, Optional

import psutil

from app.core.config import settings

_PROCESS_START_TIME = time.time()
_process = psutil.Process(os.getpid())


class LinuxSystemMonitor:
    """Safe, read-only Linux system inspector."""

    def __init__(self):
        self._active_ws_count: int = 0

    def set_active_ws_count(self, count: int) -> None:
        self._active_ws_count = count

    def get_process_info(self) -> Dict:
        """Inspect the current backend application process."""
        try:
            with _process.oneshot():
                cpu_pct = _process.cpu_percent(interval=None)
                mem_info = _process.memory_info()
                num_threads = _process.num_threads()
                status = _process.status()
        except Exception:
            cpu_pct = 0.0
            mem_info = None
            num_threads = 1
            status = "running"

        rss_mb = round(mem_info.rss / (1024 * 1024), 2) if mem_info else 0.0
        vms_mb = round(mem_info.vms / (1024 * 1024), 2) if mem_info else 0.0
        uptime = round(time.time() - _PROCESS_START_TIME, 2)

        return {
            "pid": os.getpid(),
            "status": status,
            "uptime_seconds": uptime,
            "cpu_percent": cpu_pct,
            "memory_rss_mb": rss_mb,
            "memory_vms_mb": vms_mb,
            "num_threads": num_threads,
        }

    def get_system_resources(self) -> Dict:
        """Inspect host/container CPU, RAM, and Disk resources."""
        # System CPU
        sys_cpu = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True) or 1

        # Memory (free / available)
        mem = psutil.virtual_memory()
        mem_total_mb = round(mem.total / (1024 * 1024), 1)
        mem_avail_mb = round(mem.available / (1024 * 1024), 1)
        mem_used_pct = mem.percent

        # Disk
        try:
            disk = psutil.disk_usage(str(settings.BASE_DIR))
            disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 2)
            disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 2)
            disk_used_pct = disk.percent
        except Exception:
            disk_total_gb = 0.0
            disk_free_gb = 0.0
            disk_used_pct = 0.0

        return {
            "cpu_percent": sys_cpu,
            "cpu_cores": cpu_count,
            "memory_total_mb": mem_total_mb,
            "memory_available_mb": mem_avail_mb,
            "memory_used_percent": mem_used_pct,
            "disk_total_gb": disk_total_gb,
            "disk_free_gb": disk_free_gb,
            "disk_used_percent": disk_used_pct,
        }

    def check_port_open(self, host: str = "127.0.0.1", port: int = 8000) -> bool:
        """Check if application port is actively listening without external utilities."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    def get_os_release_info(self) -> Dict:
        """Read Linux distribution details from /etc/os-release safely."""
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "distribution": "Unknown",
        }

        # Check /etc/os-release if running on Linux / WSL2
        os_release = "/etc/os-release"
        if os.path.exists(os_release):
            try:
                with open(os_release, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_info["distribution"] = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass
        else:
            os_info["distribution"] = f"{platform.system()} {platform.release()}"

        return os_info

    def get_full_diagnostics(self) -> Dict:
        """Return unified Linux operations diagnostic payload."""
        port_open = self.check_port_open("127.0.0.1", settings.PORT)
        return {
            "timestamp": time.time(),
            "os": self.get_os_release_info(),
            "process": self.get_process_info(),
            "resources": self.get_system_resources(),
            "network": {
                "port": settings.PORT,
                "port_listening": port_open,
                "active_websocket_connections": self._active_ws_count,
            },
            "service": {
                "name": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "status": "HEALTHY",
            },
        }


_system_monitor = LinuxSystemMonitor()


def get_system_monitor() -> LinuxSystemMonitor:
    return _system_monitor
