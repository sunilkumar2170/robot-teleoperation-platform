"""
Robot Safety System
-------------------
Implements:
  A. Emergency stop — immediately zeros velocities and latches a flag.
  B. Safety watchdog — stops the robot if no valid command arrives within
     WATCHDOG_TIMEOUT_SECONDS.
  C. Command validation — rejects invalid types, out-of-range speeds,
     duplicate / out-of-order sequence numbers, and commands issued while
     emergency stop is active.

All safety decisions are synchronous and run inside the simulation loop
so they are never subject to race conditions between asyncio tasks.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from app.robot.state import RobotState
from app.schemas.command import CommandAckStatus, CommandType, RobotCommandSchema

logger = logging.getLogger("robot.safety")


class SafetySystem:
    """Stateless helper whose methods operate on a RobotState object."""

    def __init__(self, watchdog_timeout: float = 2.0):
        self.watchdog_timeout = watchdog_timeout
        self._watchdog_triggered_at: Optional[float] = None

    # ── Emergency Stop ────────────────────────────────────────────────────

    def trigger_emergency_stop(self, state: RobotState) -> None:
        """Immediately halt the robot and latch the emergency-stop flag."""
        state.linear_velocity = 0.0
        state.angular_velocity = 0.0
        state.emergency_stop = True
        state.operating_mode = "EMERGENCY_STOP"
        logger.warning(
            "EMERGENCY STOP triggered for robot %s at (%.2f, %.2f)",
            state.robot_id,
            state.x,
            state.y,
        )

    def reset_emergency_stop(self, state: RobotState) -> None:
        """Clear the emergency-stop latch. Robot transitions to IDLE."""
        state.emergency_stop = False
        state.operating_mode = "IDLE"
        self._watchdog_triggered_at = None
        logger.info("Emergency stop cleared for robot %s", state.robot_id)

    # ── Watchdog ──────────────────────────────────────────────────────────

    def check_watchdog(self, state: RobotState) -> bool:
        """
        Called every simulation tick.
        Returns True if the watchdog fired and the robot was stopped.
        """
        if state.emergency_stop:
            return False  # already stopped — watchdog does not override E-stop

        elapsed = time.time() - state.last_command_timestamp
        if elapsed > self.watchdog_timeout and state.operating_mode == "MOVING":
            logger.warning(
                "Watchdog timeout (%.1f s > %.1f s) — stopping robot %s",
                elapsed,
                self.watchdog_timeout,
                state.robot_id,
            )
            state.linear_velocity = 0.0
            state.angular_velocity = 0.0
            state.operating_mode = "IDLE"
            self._watchdog_triggered_at = time.time()
            return True
        return False

    # ── Command Validation ────────────────────────────────────────────────

    def validate_command(
        self,
        cmd: RobotCommandSchema,
        state: RobotState,
    ) -> Tuple[bool, CommandAckStatus, Optional[str]]:
        """
        Returns (accepted: bool, status: CommandAckStatus, reason: str | None).

        Rules:
          1. Emergency stop is active → reject all movement commands.
          2. Sequence number must be strictly greater than the last accepted one.
          3. Speed must be within [0, 2.0] (already enforced by Pydantic, but
             checked here as a defence-in-depth layer).
        """
        # Rule 1 — E-stop blocks movement
        if state.emergency_stop and cmd.command_type not in (
            CommandType.STOP,
            CommandType.EMERGENCY_STOP,
        ):
            reason = (
                f"Emergency stop is active. Reset the robot before issuing '{cmd.command_type}'."
            )
            logger.warning("Rejected cmd %s: %s", cmd.command_id, reason)
            return False, CommandAckStatus.EMERGENCY_STOP_ACTIVE, reason

        # Rule 2 — Sequence number check
        if cmd.sequence_number <= state.last_sequence_number:
            reason = (
                f"Stale sequence number {cmd.sequence_number} "
                f"(last accepted: {state.last_sequence_number}). Command ignored."
            )
            logger.debug("Rejected cmd %s: %s", cmd.command_id, reason)
            return False, CommandAckStatus.REJECTED, reason

        # Rule 3 — Speed range (defence-in-depth)
        if not (0.0 <= cmd.speed <= 2.0):
            reason = f"Speed {cmd.speed} is out of the allowed range [0.0, 2.0]."
            logger.warning("Rejected cmd %s: %s", cmd.command_id, reason)
            return False, CommandAckStatus.REJECTED, reason

        return True, CommandAckStatus.ACCEPTED, None
