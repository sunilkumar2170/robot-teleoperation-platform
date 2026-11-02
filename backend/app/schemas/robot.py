"""
Pydantic schemas for robot state responses.
"""
from __future__ import annotations

import time
from enum import Enum
from pydantic import BaseModel, Field


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class OperatingMode(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class RobotStateSchema(BaseModel):
    """Complete robot state returned by the API and broadcast over WebSocket."""

    robot_id: str = Field(..., description="Unique robot identifier")
    x: float = Field(..., description="X position in metres within simulation boundary")
    y: float = Field(..., description="Y position in metres within simulation boundary")
    orientation: float = Field(..., description="Heading in radians (0 = +X axis, π/2 = +Y axis)")
    linear_velocity: float = Field(..., description="Current linear speed m/s")
    angular_velocity: float = Field(..., description="Current angular speed rad/s")
    battery_percentage: float = Field(..., ge=0.0, le=100.0, description="Battery level 0–100 %")
    connection_status: ConnectionStatus
    operating_mode: OperatingMode
    emergency_stop: bool = Field(..., description="True when emergency stop is latched")
    last_command_timestamp: float = Field(..., description="Unix timestamp of last accepted command")
    last_sequence_number: int = Field(..., description="Sequence number of last accepted command")

    model_config = {"use_enum_values": True}


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: float
