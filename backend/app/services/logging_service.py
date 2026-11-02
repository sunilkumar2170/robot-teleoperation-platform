"""
Logging Service for Teleop-Sim
------------------------------
Manages structured, rotating log files for:
  • logs/application.log — general server events and lifecycle
  • logs/robot.log       — kinematics, movement commands, bounds
  • logs/network.log     — latency, jitter, packet loss, WebSocket drops
  • logs/security.log    — emergency stop, sequence number violations, unauthorized requests

Also maintains an in-memory circular buffer of recent log records for
real-time dashboard streaming via GET /api/logs.
"""
from __future__ import annotations

import collections
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings

# In-memory buffer of recent log records for the UI
MAX_EVENT_BUFFER = 200
_log_buffer: collections.deque = collections.deque(maxlen=MAX_EVENT_BUFFER)


class InMemoryLogHandler(logging.Handler):
    """Custom handler that appends structured log events to an in-memory deque."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": record.created,
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            _log_buffer.append(entry)
        except Exception:
            self.handleError(record)


def setup_structured_logging() -> None:
    """Initialize rotating file handlers and console logging."""
    logs_dir = settings.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-18s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # In-memory handler for live UI streaming
    mem_handler = InMemoryLogHandler()
    mem_handler.setLevel(logging.DEBUG)

    # 1. Application log (general)
    app_handler = RotatingFileHandler(
        filename=logs_dir / "application.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    # 2. Robot log
    robot_handler = RotatingFileHandler(
        filename=logs_dir / "robot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    robot_handler.setFormatter(formatter)
    robot_handler.setLevel(logging.DEBUG)

    # 3. Network log
    net_handler = RotatingFileHandler(
        filename=logs_dir / "network.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    net_handler.setFormatter(formatter)
    net_handler.setLevel(logging.DEBUG)

    # 4. Security log
    sec_handler = RotatingFileHandler(
        filename=logs_dir / "security.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    sec_handler.setFormatter(formatter)
    sec_handler.setLevel(logging.INFO)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(app_handler)
    root.addHandler(mem_handler)

    # Specific category loggers
    robot_logger = logging.getLogger("robot")
    robot_logger.addHandler(robot_handler)

    net_logger = logging.getLogger("network")
    net_logger.addHandler(net_handler)

    sec_logger = logging.getLogger("security")
    sec_logger.addHandler(sec_handler)


def get_recent_logs(limit: int = 50, level: Optional[str] = None) -> List[Dict]:
    """Retrieve recent log events from the in-memory circular buffer."""
    events = list(_log_buffer)
    if level:
        level_upper = level.upper()
        events = [e for e in events if e["level"] == level_upper]
    return events[-limit:]


def log_security_event(message: str, severity: str = "WARNING") -> None:
    sec_logger = logging.getLogger("security")
    if severity == "ERROR":
        sec_logger.error(message)
    elif severity == "CRITICAL":
        sec_logger.critical(message)
    else:
        sec_logger.warning(message)
