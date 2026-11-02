"""
REST API Routes for Teleop-Sim
------------------------------
Endpoints:
  • /health                          — System health & simulation liveness
  • /api/robot/state                 — Current authoritative robot state
  • /api/robot/command               — Submit movement command
  • /api/robot/emergency-stop        — Emergency stop trigger
  • /api/robot/reset                 — Clear E-stop and return to origin
  • /api/network/conditions          — Read/Update simulated latency, jitter, loss
  • /api/metrics                     — Comprehensive telemetry & RTT stats
  • /api/system/diagnostics          — Linux processes, memory, CPU, ports
  • /api/logs                        — Real-time structured log events
  • /api/sessions                    — List recorded teleoperation sessions
  • /api/sessions/start              — Start recording a new session
  • /api/sessions/stop               — Stop recording current session
  • /api/sessions/{session_id}       — Get session details and event log
  • /api/sessions/{session_id}/replay— Get trajectory events for session replay
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.linux.system_monitor import get_system_monitor
from app.network.fault_injector import get_fault_injector
from app.network.latency import get_latency_tracker
from app.robot.simulator import get_simulator
from app.schemas.command import (
    CommandAckSchema,
    EmergencyStopResponse,
    NetworkConditionsSchema,
    ResetResponse,
    RobotCommandSchema,
)
from app.schemas.robot import RobotStateSchema
from app.services.logging_service import get_recent_logs, log_security_event
from app.services.session_service import get_session_service

logger = logging.getLogger("api.routes")
router = APIRouter()


class StartSessionRequest(BaseModel):
    session_name: Optional[str] = None
    notes: Optional[str] = None


_metrics_counters = {
    "emergency_stops": 0,
    "resets": 0,
}

# ── Robot Control Endpoints ───────────────────────────────────────────────────

@router.get("/api/robot/state", response_model=RobotStateSchema, tags=["Robot"])
async def get_robot_state() -> RobotStateSchema:
    """Return authoritative robot state."""
    sim = get_simulator()
    return RobotStateSchema(**sim.get_state())


@router.post("/api/robot/command", response_model=CommandAckSchema, tags=["Robot"])
async def post_robot_command(cmd: RobotCommandSchema) -> CommandAckSchema:
    """Submit a movement command."""
    sim = get_simulator()
    latency_tracker = get_latency_tracker()
    latency_tracker.commands_sent += 1

    ack = sim.process_command(cmd)
    if ack.status == "ACCEPTED":
        latency_tracker.commands_acknowledged += 1
    else:
        latency_tracker.commands_rejected += 1

    get_session_service().record_event("COMMAND", cmd.model_dump())
    return ack


@router.post("/api/robot/emergency-stop", response_model=EmergencyStopResponse, tags=["Robot"])
async def post_emergency_stop() -> EmergencyStopResponse:
    """Trigger immediate emergency stop."""
    sim = get_simulator()
    sim.emergency_stop()
    _metrics_counters["emergency_stops"] += 1
    log_security_event(f"Emergency stop triggered via REST on robot {sim.state.robot_id}", "WARNING")
    get_session_service().record_event("SAFETY", {"event": "EMERGENCY_STOP", "robot_id": sim.state.robot_id})
    return EmergencyStopResponse(
        acknowledged=True,
        message="Emergency stop acknowledged. Robot is stationary.",
    )


@router.post("/api/robot/reset", response_model=ResetResponse, tags=["Robot"])
async def post_robot_reset() -> ResetResponse:
    """Clear emergency stop and return robot to origin."""
    sim = get_simulator()
    sim.reset()
    _metrics_counters["resets"] += 1
    log_security_event(f"Robot {sim.state.robot_id} reset to home position", "INFO")
    get_session_service().record_event("SAFETY", {"event": "ROBOT_RESET", "robot_id": sim.state.robot_id})
    return ResetResponse(
        acknowledged=True,
        message="Robot reset complete. Emergency stop cleared. Position: (0, 0).",
    )


# ── Network Simulation Endpoints ──────────────────────────────────────────────

@router.get("/api/network/conditions", response_model=NetworkConditionsSchema, tags=["Network"])
async def get_network_conditions() -> NetworkConditionsSchema:
    """Get active simulated network parameters."""
    fault_injector = get_fault_injector()
    return NetworkConditionsSchema(
        latency_ms=fault_injector.latency_ms,
        jitter_ms=fault_injector.jitter_ms,
        packet_loss_pct=fault_injector.packet_loss_pct,
    )


@router.post("/api/network/conditions", response_model=NetworkConditionsSchema, tags=["Network"])
async def post_network_conditions(conditions: NetworkConditionsSchema) -> NetworkConditionsSchema:
    """Update active simulated network parameters."""
    fault_injector = get_fault_injector()
    fault_injector.configure(
        latency_ms=conditions.latency_ms,
        jitter_ms=conditions.jitter_ms,
        packet_loss_pct=conditions.packet_loss_pct,
    )
    get_session_service().record_event("NETWORK", conditions.model_dump())
    return conditions


# ── Linux System Operations & Diagnostics ────────────────────────────────────

@router.get("/api/system/diagnostics", tags=["Linux Operations"])
async def get_system_diagnostics() -> Dict[str, Any]:
    """Retrieve full Linux system, process, memory, and port diagnostics."""
    monitor = get_system_monitor()
    return monitor.get_full_diagnostics()


@router.get("/api/logs", tags=["Observability"])
async def get_application_logs(
    limit: int = Query(50, ge=1, le=200),
    level: Optional[str] = Query(None),
) -> List[Dict]:
    """Retrieve recent application event log records."""
    return get_recent_logs(limit=limit, level=level)


# ── Metrics & Telemetry ───────────────────────────────────────────────────────

@router.get("/api/metrics", tags=["Observability"])
async def get_metrics() -> Dict[str, Any]:
    """Retrieve combined telemetry, network RTT, and system stats."""
    sim = get_simulator()
    latency_stats = get_latency_tracker().get_stats()
    fault_stats = get_fault_injector().get_conditions()
    monitor = get_system_monitor()

    return {
        "timestamp": time.time(),
        "commands_received": latency_stats["commands_sent"],
        "commands_accepted": latency_stats["commands_acknowledged"],
        "commands_rejected": latency_stats["commands_rejected"],
        "emergency_stops": _metrics_counters["emergency_stops"],
        "resets": _metrics_counters["resets"],
        "uptime_seconds": monitor.get_process_info()["uptime_seconds"],
        "robot": sim.get_state(),
        "network": fault_stats,
        "latency": latency_stats,
        "fault_injection": fault_stats,
        "system": monitor.get_process_info(),
        "session": {
            "is_recording": get_session_service().is_recording(),
            "active_session_id": get_session_service().active_session_id,
        },
    }


# ── Session Recording & Replay ────────────────────────────────────────────────

@router.get("/api/sessions", tags=["Sessions"])
async def list_sessions(limit: int = Query(50, ge=1, le=100)) -> List[Dict]:
    """List recorded teleoperation sessions."""
    return get_session_service().list_sessions(limit=limit)


@router.post("/api/sessions/start", tags=["Sessions"])
async def start_session(body: StartSessionRequest) -> Dict:
    """Start recording a new session."""
    return get_session_service().start_session(
        session_name=body.session_name,
        notes=body.notes,
    )


@router.post("/api/sessions/stop", tags=["Sessions"])
async def stop_session() -> Dict:
    """Stop the current recording session."""
    record = get_session_service().stop_session()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No session is currently being recorded.",
        )
    return record


@router.get("/api/sessions/{session_id}", tags=["Sessions"])
async def get_session_detail(session_id: str) -> Dict:
    """Get complete session event history."""
    detail = get_session_service().get_session(session_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return detail


@router.get("/api/sessions/{session_id}/replay", tags=["Sessions"])
async def get_session_replay(session_id: str) -> List[Dict]:
    """Get time-ordered telemetry events to replay a session."""
    events = get_session_service().get_session_replay(session_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return events
