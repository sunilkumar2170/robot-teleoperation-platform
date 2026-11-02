"""
Tests for Linux System Monitoring and Diagnostics
"""
import pytest
from app.linux.system_monitor import LinuxSystemMonitor

def test_linux_system_monitor():
    monitor = LinuxSystemMonitor()
    proc_info = monitor.get_process_info()
    assert "pid" in proc_info
    assert proc_info["pid"] > 0
    assert "uptime_seconds" in proc_info
    assert "memory_rss_mb" in proc_info

    sys_resources = monitor.get_system_resources()
    assert "cpu_percent" in sys_resources
    assert "memory_total_mb" in sys_resources
    assert "memory_available_mb" in sys_resources
    assert sys_resources["memory_total_mb"] > 0

    diag = monitor.get_full_diagnostics()
    assert "os" in diag
    assert "process" in diag
    assert "resources" in diag
    assert "network" in diag
    assert "service" in diag
