"""
Robot state dataclass — the single authoritative source of truth.

Kept as a plain dataclass (not a Pydantic model) so it can be mutated
in-place by the simulation engine without copying overhead each tick.
The RobotStateSchema (Pydantic) is used only at API boundaries.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class RobotState:
    """Mutable, authoritative robot state held by the simulation engine."""

    robot_id: str = "robot-1"
    x: float = 0.0                        # metres
    y: float = 0.0                        # metres
    orientation: float = 0.0              # radians (0 = +X axis, π/2 = +Y axis)
    linear_velocity: float = 0.0          # m/s (+ = forward, - = backward)
    angular_velocity: float = 0.0         # rad/s (+ = CCW / left, - = CW / right)
    battery_percentage: float = 100.0     # 0–100
    connection_status: str = "DISCONNECTED"
    operating_mode: str = "IDLE"
    emergency_stop: bool = False
    last_command_timestamp: float = field(default_factory=time.time)
    last_sequence_number: int = -1

    # ── snapshot helpers ─────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "orientation": round(self.orientation, 6),
            "linear_velocity": round(self.linear_velocity, 4),
            "angular_velocity": round(self.angular_velocity, 4),
            "battery_percentage": round(self.battery_percentage, 2),
            "connection_status": self.connection_status,
            "operating_mode": self.operating_mode,
            "emergency_stop": self.emergency_stop,
            "last_command_timestamp": self.last_command_timestamp,
            "last_sequence_number": self.last_sequence_number,
        }

    def reset(self) -> None:
        """Return the robot to its home position and clear all latched flags."""
        self.x = 0.0
        self.y = 0.0
        self.orientation = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.battery_percentage = 100.0
        self.emergency_stop = False
        self.operating_mode = "IDLE"
        self.last_command_timestamp = time.time()
        self.last_sequence_number = -1
