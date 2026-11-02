"""
Phase 2 Test Suite — Robot Simulation Engine
=============================================
Covers:
  - Robot state initialisation and reset
  - Kinematics: forward / backward / left / right / stop
  - Boundary enforcement
  - Emergency stop (trigger, latch, reset)
  - Safety watchdog timeout
  - Command validation (sequence numbers, speed limits, E-stop guard)
  - REST API: GET /api/robot/state, POST /api/robot/command,
              POST /api/robot/emergency-stop, POST /api/robot/reset
  - Metrics endpoint
  - Network conditions read/write
  - Health check (Phase 1 regression)

All tests are fully deterministic — no real async sleeps, no network I/O.
"""
from __future__ import annotations

import math
import time

import pytest
from starlette.testclient import TestClient

# ── App-level imports (PYTHONPATH=backend must be set or conftest handles it) ──
from app.core.config import settings
from app.main import app
from app.robot.safety import SafetySystem
from app.robot.simulator import RobotSimulator
from app.robot.state import RobotState
from app.schemas.command import CommandAckStatus, CommandType, RobotCommandSchema

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_cmd(
    seq: int,
    cmd_type: CommandType,
    speed: float = 1.0,
    cmd_id: str | None = None,
) -> RobotCommandSchema:
    return RobotCommandSchema(
        command_id=cmd_id or f"test-cmd-{seq}",
        sequence_number=seq,
        timestamp=time.time(),
        command_type=cmd_type,
        speed=speed,
    )


def _fresh_sim(
    watchdog_timeout: float = 2.0,
    tick_hz: float = 20.0,
) -> RobotSimulator:
    """Return a *new* simulator instance (not the singleton) for isolation."""
    return RobotSimulator(robot_id="test-robot", tick_hz=tick_hz, watchdog_timeout=watchdog_timeout)


@pytest.fixture()
def sim() -> RobotSimulator:
    return _fresh_sim()


@pytest.fixture()
def client() -> TestClient:
    """
    TestClient with lifespan enabled so startup/shutdown hooks execute.
    The simulator singleton is reset before each test by re-importing.
    """
    import app.robot.simulator as sim_module
    sim_module._simulator = None          # force fresh singleton per test
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    sim_module._simulator = None          # cleanup


# ─────────────────────────────────────────────────────────────────────────────
# 1. Robot State
# ─────────────────────────────────────────────────────────────────────────────

class TestRobotState:
    def test_initial_position_is_origin(self, sim):
        assert sim.state.x == pytest.approx(0.0)
        assert sim.state.y == pytest.approx(0.0)

    def test_initial_orientation_is_zero(self, sim):
        assert sim.state.orientation == pytest.approx(0.0)

    def test_initial_battery_full(self, sim):
        assert sim.state.battery_percentage == pytest.approx(100.0)

    def test_initial_emergency_stop_clear(self, sim):
        assert sim.state.emergency_stop is False

    def test_initial_mode_is_idle(self, sim):
        assert sim.state.operating_mode == "IDLE"

    def test_initial_sequence_number_minus_one(self, sim):
        assert sim.state.last_sequence_number == -1

    def test_reset_returns_to_home(self, sim):
        sim.state.x = 15.0
        sim.state.y = -8.0
        sim.state.orientation = 1.2
        sim.state.battery_percentage = 60.0
        sim.state.emergency_stop = True
        sim.reset()
        assert sim.state.x == pytest.approx(0.0)
        assert sim.state.y == pytest.approx(0.0)
        assert sim.state.orientation == pytest.approx(0.0)
        assert sim.state.battery_percentage == pytest.approx(100.0)
        assert sim.state.emergency_stop is False
        assert sim.state.operating_mode == "IDLE"

    def test_to_dict_contains_all_keys(self, sim):
        d = sim.state.to_dict()
        required = {
            "robot_id", "x", "y", "orientation", "linear_velocity",
            "angular_velocity", "battery_percentage", "connection_status",
            "operating_mode", "emergency_stop", "last_command_timestamp",
            "last_sequence_number",
        }
        assert required.issubset(d.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 2. Kinematics — apply command then tick
# ─────────────────────────────────────────────────────────────────────────────

class TestKinematics:
    """
    All tests inject a command then call _tick() manually so they run
    synchronously without asyncio.
    """

    def _tick_after(self, sim: RobotSimulator, cmd: RobotCommandSchema, n_ticks: int = 1) -> None:
        sim.process_command(cmd)
        for _ in range(n_ticks):
            sim._tick()

    def test_move_forward_increases_x(self, sim):
        """Facing orientation=0 (East), forward movement → +X."""
        self._tick_after(sim, _make_cmd(0, CommandType.MOVE_FORWARD, speed=1.0))
        assert sim.state.x > 0.0

    def test_move_backward_decreases_x(self, sim):
        """Facing East, backward → -X."""
        self._tick_after(sim, _make_cmd(0, CommandType.MOVE_BACKWARD, speed=1.0))
        assert sim.state.x < 0.0

    def test_move_forward_y_unchanged(self, sim):
        """Facing East, forward movement → Y stays at 0."""
        self._tick_after(sim, _make_cmd(0, CommandType.MOVE_FORWARD, speed=1.0))
        assert sim.state.y == pytest.approx(0.0, abs=1e-9)

    def test_turn_left_increases_orientation(self, sim):
        """Turn left → positive angular velocity → orientation increases."""
        self._tick_after(sim, _make_cmd(0, CommandType.TURN_LEFT, speed=1.0))
        assert sim.state.orientation > 0.0

    def test_turn_right_decreases_orientation(self, sim):
        """Turn right → negative angular velocity → orientation decreases."""
        self._tick_after(sim, _make_cmd(0, CommandType.TURN_RIGHT, speed=1.0))
        assert sim.state.orientation < 0.0

    def test_stop_zeroes_velocities(self, sim):
        # First start moving
        self._tick_after(sim, _make_cmd(0, CommandType.MOVE_FORWARD, speed=1.0))
        assert sim.state.linear_velocity != 0.0
        # Then stop
        self._tick_after(sim, _make_cmd(1, CommandType.STOP))
        assert sim.state.linear_velocity == pytest.approx(0.0)
        assert sim.state.angular_velocity == pytest.approx(0.0)

    def test_stop_sets_idle_mode(self, sim):
        self._tick_after(sim, _make_cmd(0, CommandType.MOVE_FORWARD))
        self._tick_after(sim, _make_cmd(1, CommandType.STOP))
        assert sim.state.operating_mode == "IDLE"

    def test_speed_multiplier_scales_displacement(self, sim):
        """speed=2.0 should produce ~twice the displacement of speed=1.0 per tick."""
        sim_half = _fresh_sim()
        sim_full = _fresh_sim()

        sim_half.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=1.0))
        sim_half._tick()

        sim_full.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=2.0))
        sim_full._tick()

        assert sim_full.state.x == pytest.approx(sim_half.state.x * 2.0, rel=0.01)

    def test_orientation_wraps_at_pi(self, sim):
        """Verify orientation stays in (-π, π] after many left turns."""
        sim.process_command(_make_cmd(0, CommandType.TURN_LEFT, speed=2.0))
        for _ in range(100):
            sim._tick()
        assert -math.pi < sim.state.orientation <= math.pi

    def test_facing_north_forward_increases_y(self, sim):
        """After a 90° left turn, moving forward should increase Y."""
        sim.state.orientation = math.pi / 2   # face North
        sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=1.0))
        sim._tick()
        assert sim.state.y > 0.0
        assert sim.state.x == pytest.approx(0.0, abs=1e-9)

    def test_operating_mode_becomes_moving(self, sim):
        sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD))
        sim._tick()
        assert sim.state.operating_mode == "MOVING"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Boundary Enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundaryEnforcement:
    def test_east_wall_clamps_x(self, sim):
        sim.state.x = settings.BOUNDS_MAX_X - 0.01
        sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=2.0))
        for _ in range(20):
            sim._tick()
        assert sim.state.x <= settings.BOUNDS_MAX_X

    def test_west_wall_clamps_x(self, sim):
        sim.state.x = settings.BOUNDS_MIN_X + 0.01
        sim.process_command(_make_cmd(0, CommandType.MOVE_BACKWARD, speed=2.0))
        for _ in range(20):
            sim._tick()
        assert sim.state.x >= settings.BOUNDS_MIN_X

    def test_wall_impact_zeroes_linear_velocity(self, sim):
        sim.state.x = settings.BOUNDS_MAX_X + 5.0  # force outside boundary
        sim._enforce_bounds(sim.state)
        assert sim.state.x == pytest.approx(settings.BOUNDS_MAX_X)
        assert sim.state.linear_velocity == pytest.approx(0.0)

    def test_position_exactly_at_boundary_is_valid(self, sim):
        sim.state.x = settings.BOUNDS_MAX_X
        sim._enforce_bounds(sim.state)
        assert sim.state.x == pytest.approx(settings.BOUNDS_MAX_X)

    def test_cannot_move_beyond_north_wall(self, sim):
        sim.state.orientation = math.pi / 2  # face North
        sim.state.y = settings.BOUNDS_MAX_Y - 0.01
        sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=2.0))
        for _ in range(20):
            sim._tick()
        assert sim.state.y <= settings.BOUNDS_MAX_Y


# ─────────────────────────────────────────────────────────────────────────────
# 4. Emergency Stop
# ─────────────────────────────────────────────────────────────────────────────

class TestEmergencyStop:
    def test_emergency_stop_zeros_velocity(self, sim):
        sim.state.linear_velocity = 1.5
        sim.state.angular_velocity = 0.8
        sim.safety.trigger_emergency_stop(sim.state)
        assert sim.state.linear_velocity == pytest.approx(0.0)
        assert sim.state.angular_velocity == pytest.approx(0.0)

    def test_emergency_stop_sets_flag(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        assert sim.state.emergency_stop is True

    def test_emergency_stop_sets_mode(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        assert sim.state.operating_mode == "EMERGENCY_STOP"

    def test_movement_blocked_during_estop(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        ack = sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD))
        assert ack.status == "EMERGENCY_STOP_ACTIVE"

    def test_stop_command_allowed_during_estop(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        # STOP command should be allowed (it's already stopped, but shouldn't error)
        # Actually under our rules, STOP and EMERGENCY_STOP pass validation
        accepted, status, reason = sim.safety.validate_command(
            _make_cmd(0, CommandType.STOP), sim.state
        )
        assert status != "EMERGENCY_STOP_ACTIVE"

    def test_reset_clears_emergency_stop(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        sim.reset()
        assert sim.state.emergency_stop is False
        assert sim.state.operating_mode == "IDLE"

    def test_movement_allowed_after_reset(self, sim):
        sim.safety.trigger_emergency_stop(sim.state)
        sim.reset()
        ack = sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD))
        assert ack.status == "ACCEPTED"

    def test_emergency_stop_via_command_type(self, sim):
        """Sending CommandType.EMERGENCY_STOP should latch the flag."""
        ack = sim.process_command(_make_cmd(0, CommandType.EMERGENCY_STOP))
        assert ack.status == "ACCEPTED"
        assert sim.state.emergency_stop is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. Safety Watchdog
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyWatchdog:
    def test_watchdog_stops_moving_robot(self):
        """Simulate a robot that has been moving with a stale last_command_timestamp."""
        sim = _fresh_sim(watchdog_timeout=0.1)  # very short timeout for testing
        sim.state.operating_mode = "MOVING"
        sim.state.linear_velocity = 1.0
        sim.state.last_command_timestamp = time.time() - 5.0  # 5 s stale
        fired = sim.safety.check_watchdog(sim.state)
        assert fired is True
        assert sim.state.linear_velocity == pytest.approx(0.0)
        assert sim.state.operating_mode == "IDLE"

    def test_watchdog_does_not_fire_within_timeout(self):
        sim = _fresh_sim(watchdog_timeout=5.0)
        sim.state.operating_mode = "MOVING"
        sim.state.last_command_timestamp = time.time()
        fired = sim.safety.check_watchdog(sim.state)
        assert fired is False

    def test_watchdog_does_not_fire_when_idle(self):
        """Watchdog should not override IDLE state (robot is already stopped)."""
        sim = _fresh_sim(watchdog_timeout=0.01)
        sim.state.operating_mode = "IDLE"
        sim.state.last_command_timestamp = time.time() - 10.0
        fired = sim.safety.check_watchdog(sim.state)
        assert fired is False

    def test_watchdog_does_not_override_estop(self):
        """Watchdog must not interfere with an active emergency stop."""
        sim = _fresh_sim(watchdog_timeout=0.01)
        sim.safety.trigger_emergency_stop(sim.state)
        sim.state.operating_mode = "EMERGENCY_STOP"
        fired = sim.safety.check_watchdog(sim.state)
        assert fired is False
        assert sim.state.emergency_stop is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Command Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestCommandValidation:
    def test_first_command_accepted(self, sim):
        ack = sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD))
        assert ack.status == "ACCEPTED"

    def test_duplicate_sequence_number_rejected(self, sim):
        sim.process_command(_make_cmd(5, CommandType.MOVE_FORWARD))
        ack = sim.process_command(_make_cmd(5, CommandType.STOP))
        assert ack.status == "REJECTED"

    def test_lower_sequence_number_rejected(self, sim):
        sim.process_command(_make_cmd(10, CommandType.MOVE_FORWARD))
        ack = sim.process_command(_make_cmd(3, CommandType.STOP))
        assert ack.status == "REJECTED"

    def test_strictly_increasing_sequence_accepted(self, sim):
        sim.process_command(_make_cmd(1, CommandType.MOVE_FORWARD))
        ack = sim.process_command(_make_cmd(2, CommandType.STOP))
        assert ack.status == "ACCEPTED"

    def test_sequence_counter_advances(self, sim):
        sim.process_command(_make_cmd(7, CommandType.MOVE_FORWARD))
        assert sim.state.last_sequence_number == 7

    def test_speed_zero_is_valid(self, sim):
        ack = sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=0.0))
        assert ack.status == "ACCEPTED"

    def test_speed_max_is_valid(self, sim):
        ack = sim.process_command(_make_cmd(0, CommandType.MOVE_FORWARD, speed=2.0))
        assert ack.status == "ACCEPTED"

    def test_pydantic_rejects_negative_speed(self):
        with pytest.raises(Exception):
            RobotCommandSchema(
                sequence_number=0,
                command_type=CommandType.MOVE_FORWARD,
                speed=-1.0,
            )

    def test_pydantic_rejects_excess_speed(self):
        with pytest.raises(Exception):
            RobotCommandSchema(
                sequence_number=0,
                command_type=CommandType.MOVE_FORWARD,
                speed=99.0,
            )

    def test_command_id_auto_generated(self):
        cmd = RobotCommandSchema(
            sequence_number=0,
            command_type=CommandType.STOP,
        )
        assert cmd.command_id.startswith("cmd-")


# ─────────────────────────────────────────────────────────────────────────────
# 7. REST API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRobotStateEndpoint:
    def test_get_state_returns_200(self, client):
        resp = client.get("/api/robot/state")
        assert resp.status_code == 200

    def test_get_state_schema(self, client):
        data = client.get("/api/robot/state").json()
        required = {
            "robot_id", "x", "y", "orientation", "linear_velocity",
            "angular_velocity", "battery_percentage", "connection_status",
            "operating_mode", "emergency_stop",
        }
        assert required.issubset(data.keys())

    def test_initial_position_is_origin(self, client):
        data = client.get("/api/robot/state").json()
        assert data["x"] == pytest.approx(0.0, abs=0.1)
        assert data["y"] == pytest.approx(0.0, abs=0.1)

    def test_initial_battery_full(self, client):
        data = client.get("/api/robot/state").json()
        assert data["battery_percentage"] == pytest.approx(100.0, abs=1.0)

    def test_emergency_stop_initially_clear(self, client):
        data = client.get("/api/robot/state").json()
        assert data["emergency_stop"] is False


class TestCommandEndpoint:
    def test_post_command_returns_200(self, client):
        payload = {
            "sequence_number": 1,
            "command_type": "MOVE_FORWARD",
            "speed": 1.0,
        }
        resp = client.post("/api/robot/command", json=payload)
        assert resp.status_code == 200

    def test_post_command_accepted(self, client):
        payload = {"sequence_number": 1, "command_type": "MOVE_FORWARD", "speed": 1.0}
        data = client.post("/api/robot/command", json=payload).json()
        assert data["status"] == "ACCEPTED"

    def test_post_command_returns_command_id(self, client):
        payload = {
            "command_id": "my-cmd-abc",
            "sequence_number": 1,
            "command_type": "STOP",
            "speed": 1.0,
        }
        data = client.post("/api/robot/command", json=payload).json()
        assert data["command_id"] == "my-cmd-abc"

    def test_duplicate_sequence_rejected_via_api(self, client):
        payload = {"sequence_number": 5, "command_type": "MOVE_FORWARD", "speed": 1.0}
        client.post("/api/robot/command", json=payload)
        resp2 = client.post("/api/robot/command", json=payload)
        assert resp2.json()["status"] == "REJECTED"

    def test_all_command_types_accepted(self, client):
        for seq, cmd in enumerate([
            "MOVE_FORWARD", "MOVE_BACKWARD",
            "TURN_LEFT", "TURN_RIGHT",
            "STOP",
        ]):
            resp = client.post("/api/robot/command", json={
                "sequence_number": seq,
                "command_type": cmd,
                "speed": 1.0,
            })
            assert resp.status_code == 200

    def test_invalid_command_type_returns_422(self, client):
        payload = {"sequence_number": 99, "command_type": "FLY", "speed": 1.0}
        resp = client.post("/api/robot/command", json=payload)
        assert resp.status_code == 422

    def test_speed_out_of_range_returns_422(self, client):
        payload = {"sequence_number": 99, "command_type": "MOVE_FORWARD", "speed": 99.0}
        resp = client.post("/api/robot/command", json=payload)
        assert resp.status_code == 422


class TestEmergencyStopEndpoint:
    def test_emergency_stop_returns_200(self, client):
        resp = client.post("/api/robot/emergency-stop")
        assert resp.status_code == 200

    def test_emergency_stop_acknowledged(self, client):
        data = client.post("/api/robot/emergency-stop").json()
        assert data["acknowledged"] is True

    def test_state_shows_estop_after_trigger(self, client):
        client.post("/api/robot/emergency-stop")
        state = client.get("/api/robot/state").json()
        assert state["emergency_stop"] is True
        assert state["operating_mode"] == "EMERGENCY_STOP"

    def test_command_rejected_after_estop(self, client):
        client.post("/api/robot/emergency-stop")
        ack = client.post("/api/robot/command", json={
            "sequence_number": 1,
            "command_type": "MOVE_FORWARD",
            "speed": 1.0,
        }).json()
        assert ack["status"] == "EMERGENCY_STOP_ACTIVE"


class TestResetEndpoint:
    def test_reset_returns_200(self, client):
        resp = client.post("/api/robot/reset")
        assert resp.status_code == 200

    def test_reset_acknowledged(self, client):
        data = client.post("/api/robot/reset").json()
        assert data["acknowledged"] is True

    def test_reset_clears_estop_in_state(self, client):
        client.post("/api/robot/emergency-stop")
        client.post("/api/robot/reset")
        state = client.get("/api/robot/state").json()
        assert state["emergency_stop"] is False
        assert state["operating_mode"] == "IDLE"

    def test_movement_allowed_after_reset(self, client):
        client.post("/api/robot/emergency-stop")
        client.post("/api/robot/reset")
        ack = client.post("/api/robot/command", json={
            "sequence_number": 1,
            "command_type": "MOVE_FORWARD",
            "speed": 1.0,
        }).json()
        assert ack["status"] == "ACCEPTED"


class TestNetworkConditionsEndpoint:
    def test_get_conditions_returns_defaults(self, client):
        data = client.get("/api/network/conditions").json()
        assert "latency_ms" in data
        assert "jitter_ms" in data
        assert "packet_loss_pct" in data

    def test_post_conditions_accepted(self, client):
        payload = {"latency_ms": 200.0, "jitter_ms": 50.0, "packet_loss_pct": 5.0}
        resp = client.post("/api/network/conditions", json=payload)
        assert resp.status_code == 200

    def test_post_conditions_out_of_range_rejected(self, client):
        payload = {"latency_ms": 9999.0, "jitter_ms": 0.0, "packet_loss_pct": 0.0}
        resp = client.post("/api/network/conditions", json=payload)
        assert resp.status_code == 422

    def test_conditions_persist_after_update(self, client):
        payload = {"latency_ms": 100.0, "jitter_ms": 25.0, "packet_loss_pct": 10.0}
        client.post("/api/network/conditions", json=payload)
        data = client.get("/api/network/conditions").json()
        assert data["latency_ms"] == pytest.approx(100.0)
        assert data["jitter_ms"] == pytest.approx(25.0)


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        assert client.get("/api/metrics").status_code == 200

    def test_metrics_has_required_fields(self, client):
        data = client.get("/api/metrics").json()
        for field in ("commands_received", "commands_accepted", "commands_rejected",
                      "emergency_stops", "resets", "uptime_seconds", "robot", "network"):
            assert field in data, f"Missing field: {field}"

    def test_metrics_counters_increment(self, client):
        client.post("/api/robot/command", json={
            "sequence_number": 1, "command_type": "MOVE_FORWARD", "speed": 1.0,
        })
        data = client.get("/api/metrics").json()
        assert data["commands_received"] >= 1
        assert data["commands_accepted"] >= 1


class TestHealthCheck:
    """Phase 1 regression — health endpoint must still work."""

    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_status_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_includes_simulation_running(self, client):
        data = client.get("/health").json()
        assert "simulation_running" in data
        assert data["simulation_running"] is True

    def test_health_includes_robot_id(self, client):
        data = client.get("/health").json()
        assert "robot_id" in data
