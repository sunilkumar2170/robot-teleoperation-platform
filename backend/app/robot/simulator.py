"""
2D Robot Simulation Engine
--------------------------
Implements a differential-drive kinematic model running inside an asyncio
background task.

Coordinate system
    • +X  →  East
    • +Y  →  North
    • orientation = 0 rad  →  robot faces East (+X)
    • orientation = π/2   →  robot faces North (+Y)
    • positive angular velocity  →  counter-clockwise (left turn)
    • negative angular velocity  →  clockwise (right turn)

Boundary enforcement
    The robot is clamped to [BOUNDS_MIN_X, BOUNDS_MAX_X] × [BOUNDS_MIN_Y, BOUNDS_MAX_Y].
    Velocities are zeroed when a wall is hit so the next MOVE command starts cleanly.

Battery
    Drains at BATTERY_DRAIN_PER_SECOND when moving, BATTERY_IDLE_DRAIN when idle.
    Movement is blocked at 0 % (emergency stop equivalent).
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Callable, List, Optional

from app.core.config import settings
from app.robot.safety import SafetySystem
from app.robot.state import RobotState
from app.schemas.command import CommandAckSchema, CommandAckStatus, CommandType, RobotCommandSchema

logger = logging.getLogger("robot.simulator")

# Physics constants
BASE_LINEAR_SPEED: float = settings.ROBOT_DEFAULT_LINEAR_SPEED  # m/s at speed=1.0
BASE_ANGULAR_SPEED: float = settings.ROBOT_DEFAULT_ANGULAR_SPEED  # rad/s at speed=1.0
BATTERY_DRAIN_MOVING: float = 0.01   # % per second while moving
BATTERY_DRAIN_IDLE: float = 0.001    # % per second while idle


class RobotSimulator:
    """
    Runs an asyncio background task that ticks the robot physics at a
    configurable frequency.  REST and WebSocket handlers interact with
    this instance via thread-safe calls.
    """

    def __init__(
        self,
        robot_id: str = "robot-1",
        tick_hz: float = settings.SIMULATION_FREQUENCY_HZ,
        watchdog_timeout: float = settings.WATCHDOG_TIMEOUT_SECONDS,
    ) -> None:
        self.state = RobotState(robot_id=robot_id)
        self.safety = SafetySystem(watchdog_timeout=watchdog_timeout)
        self._tick_interval: float = 1.0 / tick_hz
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

        # Callbacks invoked after every state update (e.g. WebSocket broadcast)
        self._state_callbacks: List[Callable] = []

        # Pending command — set by API handlers, consumed by simulation loop
        self._pending_command: Optional[RobotCommandSchema] = None

        logger.info(
            "RobotSimulator created: id=%s tick_hz=%.1f watchdog=%.1f s",
            robot_id,
            tick_hz,
            watchdog_timeout,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the simulation loop as an asyncio background task."""
        if self._running:
            logger.warning("Simulator already running — ignoring start request")
            return
        self._running = True
        self.state.connection_status = "CONNECTED"
        self.state.last_command_timestamp = time.time()
        self._task = asyncio.create_task(self._simulation_loop(), name="robot-sim-loop")
        logger.info("Simulation loop started for robot %s", self.state.robot_id)

    async def stop(self) -> None:
        """Gracefully stop the simulation loop and halt the robot."""
        if not self._running:
            return
        self._running = False
        self.state.linear_velocity = 0.0
        self.state.angular_velocity = 0.0
        self.state.connection_status = "DISCONNECTED"
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Simulation loop stopped for robot %s", self.state.robot_id)

    # ── Command Interface ─────────────────────────────────────────────────

    def process_command(self, cmd: RobotCommandSchema) -> CommandAckSchema:
        """
        Validate and queue a command.  Called by the REST/WS layer.
        Returns an acknowledgement immediately; execution happens in the loop.
        """
        accepted, status, reason = self.safety.validate_command(cmd, self.state)

        if not accepted:
            return CommandAckSchema(
                command_id=cmd.command_id,
                sequence_number=cmd.sequence_number,
                status=status,
                reason=reason,
            )

        # Special case: EMERGENCY_STOP is handled synchronously for minimum latency
        if cmd.command_type == CommandType.EMERGENCY_STOP:
            self.safety.trigger_emergency_stop(self.state)
            self._update_sequence(cmd)
            logger.info("EMERGENCY_STOP accepted (cmd %s)", cmd.command_id)
            return CommandAckSchema(
                command_id=cmd.command_id,
                sequence_number=cmd.sequence_number,
                status=CommandAckStatus.ACCEPTED,
            )

        # Queue the command for the next simulation tick
        self._pending_command = cmd
        self._update_sequence(cmd)
        logger.debug("Command %s (%s) accepted", cmd.command_id, cmd.command_type)
        return CommandAckSchema(
            command_id=cmd.command_id,
            sequence_number=cmd.sequence_number,
            status=CommandAckStatus.ACCEPTED,
        )

    def emergency_stop(self) -> None:
        """External E-stop trigger (e.g. from watchdog or REST endpoint)."""
        self.safety.trigger_emergency_stop(self.state)

    def reset(self) -> None:
        """Reset robot to home position and clear emergency stop."""
        self.state.reset()
        self._pending_command = None
        logger.info("Robot %s reset to home position", self.state.robot_id)

    # ── State Access ──────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Return an immutable snapshot of the current robot state."""
        return self.state.to_dict()

    def add_state_callback(self, cb: Callable) -> None:
        """Register a coroutine callback invoked after every state update."""
        self._state_callbacks.append(cb)

    # ── Simulation Loop ───────────────────────────────────────────────────

    async def _simulation_loop(self) -> None:
        logger.debug("Simulation tick loop running at %.1f Hz", 1.0 / self._tick_interval)
        while self._running:
            t_start = time.monotonic()
            try:
                self._tick()
            except Exception as exc:
                logger.exception("Unhandled error in simulation tick: %s", exc)

            # Invoke registered callbacks (e.g. WebSocket broadcast — Phase 3)
            for cb in self._state_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(self.state.to_dict())
                    else:
                        cb(self.state.to_dict())
                except Exception as exc:
                    logger.warning("State callback error: %s", exc)

            elapsed = time.monotonic() - t_start
            sleep_for = max(0.0, self._tick_interval - elapsed)
            await asyncio.sleep(sleep_for)

    def _tick(self) -> None:
        """
        Single physics tick:
          1. Consume pending command → update target velocities.
          2. Safety watchdog check.
          3. Integrate kinematics.
          4. Enforce boundaries.
          5. Drain battery.
        """
        dt = self._tick_interval
        state = self.state

        # 1. Apply pending command
        if self._pending_command is not None:
            cmd = self._pending_command
            self._pending_command = None
            self._apply_command_velocities(cmd, state)
            state.last_command_timestamp = time.time()

        # 2. Watchdog
        self.safety.check_watchdog(state)

        # 3. Integrate kinematics (differential-drive)
        if state.linear_velocity != 0.0 or state.angular_velocity != 0.0:
            state.x += state.linear_velocity * math.cos(state.orientation) * dt
            state.y += state.linear_velocity * math.sin(state.orientation) * dt
            state.orientation += state.angular_velocity * dt
            # Normalise orientation to (-π, π]
            state.orientation = (state.orientation + math.pi) % (2 * math.pi) - math.pi

        # 4. Boundary enforcement
        self._enforce_bounds(state)

        # 5. Battery drain
        if state.operating_mode == "MOVING":
            state.battery_percentage = max(0.0, state.battery_percentage - BATTERY_DRAIN_MOVING * dt)
        else:
            state.battery_percentage = max(0.0, state.battery_percentage - BATTERY_DRAIN_IDLE * dt)

        # Block movement on battery flat
        if state.battery_percentage <= 0.0 and state.operating_mode == "MOVING":
            logger.warning("Battery exhausted — emergency stop on robot %s", state.robot_id)
            self.safety.trigger_emergency_stop(state)

    def _apply_command_velocities(self, cmd: RobotCommandSchema, state: RobotState) -> None:
        """Translate a command type + speed into target velocities."""
        speed = cmd.speed
        command = cmd.command_type

        if command == CommandType.MOVE_FORWARD:
            state.linear_velocity = BASE_LINEAR_SPEED * speed
            state.angular_velocity = 0.0
            state.operating_mode = "MOVING"

        elif command == CommandType.MOVE_BACKWARD:
            state.linear_velocity = -BASE_LINEAR_SPEED * speed
            state.angular_velocity = 0.0
            state.operating_mode = "MOVING"

        elif command == CommandType.TURN_LEFT:
            state.linear_velocity = 0.0
            state.angular_velocity = BASE_ANGULAR_SPEED * speed
            state.operating_mode = "MOVING"

        elif command == CommandType.TURN_RIGHT:
            state.linear_velocity = 0.0
            state.angular_velocity = -BASE_ANGULAR_SPEED * speed
            state.operating_mode = "MOVING"

        elif command == CommandType.STOP:
            state.linear_velocity = 0.0
            state.angular_velocity = 0.0
            state.operating_mode = "IDLE"

    def _enforce_bounds(self, state: RobotState) -> None:
        """Clamp position to simulation boundaries, zero velocity on impact."""
        hit_wall = False

        if state.x < settings.BOUNDS_MIN_X:
            state.x = settings.BOUNDS_MIN_X
            state.linear_velocity = 0.0
            hit_wall = True
        elif state.x > settings.BOUNDS_MAX_X:
            state.x = settings.BOUNDS_MAX_X
            state.linear_velocity = 0.0
            hit_wall = True

        if state.y < settings.BOUNDS_MIN_Y:
            state.y = settings.BOUNDS_MIN_Y
            state.linear_velocity = 0.0
            hit_wall = True
        elif state.y > settings.BOUNDS_MAX_Y:
            state.y = settings.BOUNDS_MAX_Y
            state.linear_velocity = 0.0
            hit_wall = True

        if hit_wall and state.operating_mode == "MOVING":
            state.operating_mode = "IDLE"
            logger.debug(
                "Robot %s hit boundary at (%.2f, %.2f)", state.robot_id, state.x, state.y
            )

    # ── Private helpers ───────────────────────────────────────────────────

    def _update_sequence(self, cmd: RobotCommandSchema) -> None:
        self.state.last_sequence_number = cmd.sequence_number
        self.state.last_command_timestamp = time.time()


# ── Module-level singleton accessed by FastAPI app ────────────────────────
_simulator: Optional[RobotSimulator] = None


def get_simulator() -> RobotSimulator:
    """Return the application-wide RobotSimulator singleton."""
    global _simulator
    if _simulator is None:
        _simulator = RobotSimulator()
    return _simulator
