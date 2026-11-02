"""
REST API Routes — Phase 2
--------------------------
Endpoints implemented in this phase:

  GET  /health                          — system liveness check
  GET  /api/robot/state                 — current authoritative robot state
  POST /api/robot/command               — submit a movement command
  POST /api/robot/emergency-stop        — trigger immediate emergency stop
  POST /api/robot/reset                 — clear emergency stop & return to home
  GET  /api/network/conditions          — read current network fault settings
  POST /api/network/conditions          — update network fault settings
  GET  /api/metrics                     — lightweight telemetry summary

WebSocket  /ws/robot  is reserved for Phase 3.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, status

from app.robot.simulator import get_simulator
from app.schemas.command import (
    CommandAckSchema,
    EmergencyStopResponse,
    NetworkConditionsSchema,
    ResetResponse,
    RobotCommandSchema,
)
from app.schemas.robot import RobotStateSchema

logger = logging.getLogger("api.routes")

router = APIRouter()

# ── In-memory network fault settings (replaced by fault injector in Phase 5) ──
_network_conditions: Dict[str, float] = {
    "latency_ms": 0.0,
    "jitter_ms": 0.0,
    "packet_loss_pct": 0.0,
}

# ── Simple in-memory metrics counters ─────────────────────────────────────────
_metrics: Dict[str, Any] = {
    "commands_received": 0,
    "commands_accepted": 0,
    "commands_rejected": 0,
    "emergency_stops": 0,
    "resets": 0,
    "started_at": time.time(),
}


# ── Robot State ────────────────────────────────────────────────────────────────

@router.get(
    "/api/robot/state",
    response_model=RobotStateSchema,
    summary="Get current robot state",
    tags=["Robot"],
)
async def get_robot_state() -> RobotStateSchema:
    """Return the authoritative server-side robot state."""
    sim = get_simulator()
    return RobotStateSchema(**sim.get_state())


# ── Command ────────────────────────────────────────────────────────────────────

@router.post(
    "/api/robot/command",
    response_model=CommandAckSchema,
    summary="Submit a movement command",
    tags=["Robot"],
)
async def post_robot_command(cmd: RobotCommandSchema) -> CommandAckSchema:
    """
    Submit a validated movement command to the robot simulation engine.
    Commands with duplicate or lower sequence numbers are silently rejected.
    """
    _metrics["commands_received"] += 1
    sim = get_simulator()

    try:
        ack = sim.process_command(cmd)
    except Exception as exc:
        logger.exception("Unexpected error processing command: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal simulation error",
        )

    if ack.status == "ACCEPTED":
        _metrics["commands_accepted"] += 1
    else:
        _metrics["commands_rejected"] += 1

    return ack


# ── Emergency Stop ─────────────────────────────────────────────────────────────

@router.post(
    "/api/robot/emergency-stop",
    response_model=EmergencyStopResponse,
    summary="Trigger immediate emergency stop",
    tags=["Robot"],
)
async def post_emergency_stop() -> EmergencyStopResponse:
    """
    Immediately halt all robot movement and latch the emergency-stop flag.
    A subsequent POST /api/robot/reset is required before movement resumes.
    """
    sim = get_simulator()
    sim.emergency_stop()
    _metrics["emergency_stops"] += 1
    logger.warning("Emergency stop triggered via REST endpoint")
    return EmergencyStopResponse(
        acknowledged=True,
        message="Emergency stop acknowledged. Robot is now stationary.",
    )


# ── Reset ──────────────────────────────────────────────────────────────────────

@router.post(
    "/api/robot/reset",
    response_model=ResetResponse,
    summary="Reset robot to home position",
    tags=["Robot"],
)
async def post_robot_reset() -> ResetResponse:
    """
    Clear the emergency-stop latch and return the robot to its home position
    (0, 0, orientation=0). All velocity is zeroed and sequence counter is reset.
    """
    sim = get_simulator()
    sim.reset()
    _metrics["resets"] += 1
    logger.info("Robot reset to home position via REST endpoint")
    return ResetResponse(
        acknowledged=True,
        message="Robot reset complete. Emergency stop cleared. Position: (0, 0).",
    )


# ── Network Conditions ─────────────────────────────────────────────────────────

@router.get(
    "/api/network/conditions",
    response_model=NetworkConditionsSchema,
    summary="Read current network fault settings",
    tags=["Network"],
)
async def get_network_conditions() -> NetworkConditionsSchema:
    return NetworkConditionsSchema(**_network_conditions)


@router.post(
    "/api/network/conditions",
    response_model=NetworkConditionsSchema,
    summary="Update network fault settings",
    tags=["Network"],
)
async def post_network_conditions(conditions: NetworkConditionsSchema) -> NetworkConditionsSchema:
    """
    Update simulated network impairment parameters.
    The actual fault injection engine (Phase 5) will read these at runtime.
    """
    _network_conditions.update(conditions.model_dump())
    logger.info("Network conditions updated: %s", _network_conditions)
    return NetworkConditionsSchema(**_network_conditions)


# ── Metrics ────────────────────────────────────────────────────────────────────

@router.get(
    "/api/metrics",
    summary="Lightweight telemetry summary",
    tags=["Monitoring"],
)
async def get_metrics() -> Dict[str, Any]:
    """Return command counters, uptime, and current robot snapshot."""
    sim = get_simulator()
    uptime = round(time.time() - _metrics["started_at"], 2)
    return {
        **_metrics,
        "uptime_seconds": uptime,
        "robot": sim.get_state(),
        "network": _network_conditions,
        "timestamp": time.time(),
    }
