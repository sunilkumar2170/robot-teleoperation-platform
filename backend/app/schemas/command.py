"""
Pydantic schemas for robot command requests and acknowledgement responses.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class CommandType(str, Enum):
    MOVE_FORWARD = "MOVE_FORWARD"
    MOVE_BACKWARD = "MOVE_BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    STOP = "STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class RobotCommandSchema(BaseModel):
    """Incoming operator command. All fields are validated before processing."""

    command_id: str = Field(
        default_factory=lambda: f"cmd-{uuid.uuid4().hex[:8]}",
        description="Unique command identifier",
    )
    sequence_number: int = Field(
        ..., ge=0, description="Monotonically increasing; commands with duplicate or lower numbers are rejected"
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Client-side Unix timestamp when the command was issued",
    )
    command_type: CommandType
    speed: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Normalised speed multiplier 0.0–2.0 (capped at 2.0 for safety)",
    )

    @field_validator("speed")
    @classmethod
    def clamp_speed(cls, v: float) -> float:
        return max(0.0, min(2.0, v))

    model_config = {"use_enum_values": True}


class CommandAckStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EMERGENCY_STOP_ACTIVE = "EMERGENCY_STOP_ACTIVE"


class CommandAckSchema(BaseModel):
    """Server acknowledgement returned after processing a command."""

    command_id: str
    sequence_number: int
    status: CommandAckStatus
    reason: Optional[str] = None
    server_timestamp: float = Field(default_factory=time.time)

    model_config = {"use_enum_values": True}


class EmergencyStopResponse(BaseModel):
    acknowledged: bool
    message: str
    server_timestamp: float = Field(default_factory=time.time)


class ResetResponse(BaseModel):
    acknowledged: bool
    message: str
    server_timestamp: float = Field(default_factory=time.time)


class NetworkConditionsSchema(BaseModel):
    """Network fault injection parameters."""

    latency_ms: float = Field(0.0, ge=0.0, le=2000.0, description="Simulated one-way latency in ms")
    jitter_ms: float = Field(0.0, ge=0.0, le=500.0, description="Random jitter added to latency in ms")
    packet_loss_pct: float = Field(0.0, ge=0.0, le=50.0, description="Probability of dropping a command 0–50 %")
