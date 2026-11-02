"""
Real-Time WebSocket Communication Module
----------------------------------------
Implements:
  • /ws/robot endpoint
  • Client connection manager (multi-client safe, broadcasting)
  • Fault injector integration (latency, jitter, drop)
  • Monotonic sequence validation & command acknowledgement
  • Server-side disconnect safety (stops robot if controlling client disconnects)
  • Ping/Pong heartbeat for round-trip time (RTT) calculation
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.linux.system_monitor import get_system_monitor
from app.network.fault_injector import get_fault_injector
from app.network.latency import get_latency_tracker
from app.robot.simulator import get_simulator
from app.schemas.command import CommandType, RobotCommandSchema
from app.services.session_service import get_session_service

logger = logging.getLogger("api.websocket")

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket operator connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            get_system_monitor().set_active_ws_count(len(self.active_connections))
        
        sim = get_simulator()
        sim.state.connection_status = "CONNECTED"
        get_session_service().record_event("CONNECTION", {"event": "CLIENT_CONNECTED", "count": len(self.active_connections)})
        logger.info("WebSocket client connected. Active connections: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)
            count = len(self.active_connections)
            get_system_monitor().set_active_ws_count(count)

        logger.info("WebSocket client disconnected. Active connections remaining: %d", count)
        get_session_service().record_event("CONNECTION", {"event": "CLIENT_DISCONNECTED", "count": count})

        # Safety watchdog: if all operator clients disconnect, stop the robot safely!
        if count == 0:
            sim = get_simulator()
            sim.state.connection_status = "DISCONNECTED"
            if sim.state.operating_mode == "MOVING":
                logger.warning("All clients disconnected while robot was moving — triggering safety stop")
                sim.process_command(
                    RobotCommandSchema(
                        sequence_number=sim.state.last_sequence_number + 1,
                        command_type=CommandType.STOP,
                    )
                )

    async def broadcast_state(self, state_dict: dict) -> None:
        """Broadcast authoritative robot state to all connected clients."""
        if not self.active_connections:
            return

        payload = {
            "type": "ROBOT_STATE",
            "timestamp": time.time(),
            "data": state_dict,
        }
        message = json.dumps(payload)

        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)

            for dead_conn in disconnected:
                self.active_connections.discard(dead_conn)
            if disconnected:
                get_system_monitor().set_active_ws_count(len(self.active_connections))


manager = ConnectionManager()


# Register the state broadcast callback with the robot simulator
def _init_simulator_callback():
    sim = get_simulator()
    sim.add_state_callback(manager.broadcast_state)


@router.websocket("/ws/robot")
async def robot_websocket_endpoint(websocket: WebSocket):
    """
    Primary WebSocket interface:
      Client -> Server:
        - {"type": "COMMAND", "data": {...RobotCommandSchema...}}
        - {"type": "PING", "timestamp": 123456789}
        - {"type": "GET_STATE"}

      Server -> Client:
        - {"type": "ROBOT_STATE", "data": {...}}
        - {"type": "COMMAND_ACK", "data": {...}}
        - {"type": "PONG", "client_timestamp": 123456789, "server_timestamp": ...}
        - {"type": "PACKET_DROPPED", "command_id": ...}
    """
    await manager.connect(websocket)
    sim = get_simulator()
    fault_injector = get_fault_injector()
    latency_tracker = get_latency_tracker()
    session_service = get_session_service()

    # Send initial state immediately upon connection
    await websocket.send_json({
        "type": "ROBOT_STATE",
        "timestamp": time.time(),
        "data": sim.get_state(),
    })

    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except Exception:
                await websocket.send_json({"type": "ERROR", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "").upper()

            # 1. PING / PONG (Round-Trip Latency measurement)
            if msg_type == "PING":
                client_ts = msg.get("timestamp", time.time())
                now = time.time()
                rtt_ms = (now - client_ts) * 1000.0 if client_ts else 0.0
                latency_tracker.record_rtt(rtt_ms)
                await websocket.send_json({
                    "type": "PONG",
                    "client_timestamp": client_ts,
                    "server_timestamp": now,
                    "rtt_ms": round(rtt_ms, 2),
                })
                continue

            # 2. Explicit State Request (for reconnection state recovery)
            elif msg_type == "GET_STATE":
                await websocket.send_json({
                    "type": "ROBOT_STATE",
                    "timestamp": time.time(),
                    "data": sim.get_state(),
                })
                continue

            # 3. Robot Command
            elif msg_type == "COMMAND":
                cmd_data = msg.get("data", {})
                latency_tracker.commands_sent += 1

                # Apply simulated network fault (latency, jitter, packet drop)
                is_dropped, delay_ms = await fault_injector.inject_fault()

                if is_dropped:
                    logger.warning("Simulated network drop for command: %s", cmd_data.get("command_id"))
                    session_service.record_event("NETWORK", {
                        "event": "PACKET_DROPPED",
                        "command_id": cmd_data.get("command_id"),
                        "sequence_number": cmd_data.get("sequence_number"),
                    })
                    await websocket.send_json({
                        "type": "PACKET_DROPPED",
                        "command_id": cmd_data.get("command_id"),
                        "sequence_number": cmd_data.get("sequence_number"),
                        "reason": "Simulated packet loss in transmission channel",
                    })
                    continue

                # Parse & validate command
                try:
                    cmd = RobotCommandSchema(**cmd_data)
                except Exception as exc:
                    latency_tracker.commands_rejected += 1
                    await websocket.send_json({
                        "type": "COMMAND_ACK",
                        "data": {
                            "command_id": cmd_data.get("command_id", "unknown"),
                            "sequence_number": cmd_data.get("sequence_number", -1),
                            "status": "REJECTED",
                            "reason": f"Validation error: {exc}",
                            "server_timestamp": time.time(),
                        },
                    })
                    continue

                # Process valid command
                ack = sim.process_command(cmd)

                if ack.status == "ACCEPTED":
                    latency_tracker.commands_acknowledged += 1
                else:
                    latency_tracker.commands_rejected += 1

                # Record event to session
                session_service.record_event("COMMAND", cmd_data)

                # Return acknowledgement
                await websocket.send_json({
                    "type": "COMMAND_ACK",
                    "data": ack.model_dump(),
                    "simulated_delay_ms": round(delay_ms, 1),
                })

            else:
                await websocket.send_json({"type": "ERROR", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket handler exception: %s", exc)
        await manager.disconnect(websocket)
