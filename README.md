# Teleop-Sim 🤖
### Real-Time Robotics Teleoperation & Network Reliability Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-RFC_6455-orange.svg)](https://websockets.readthedocs.io/)
[![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20WSL2-FCC624.svg?logo=linux&logoColor=black)](https://ubuntu.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-81%20Passed-brightgreen.svg)](https://pytest.org/)
[![Status](https://img.shields.io/badge/Status-Actively%20Under%20Development-yellow.svg)]()

> **Building reliable remote robot control systems with Python, Linux, WebSockets and Docker.**  
> Teleop-Sim is a robotics teleoperation simulator under development designed to explore the engineering challenges of remotely controlling robots over unreliable networks.

The project focuses on real-time communication, robot state synchronization, network fault injection, Linux diagnostics, process management, and deployment reliability — mirroring the core competencies of a **Robotics Forward Deployed Engineer (FDE)**.

**Repository:** [https://github.com/sunilkumar2170/robot-teleoperation-platform](https://github.com/sunilkumar2170/robot-teleoperation-platform)

---

## 🎥 Live Simulation Demo

The animation below is generated directly by executing the underlying differential-drive kinematics simulation engine (`backend/app/robot/simulator.py`) at 20 Hz, showing forward drive, turning, velocity scaling, emergency stop latching, and home-position reset:

![Teleop-Sim 2D Robot Simulation Demo](docs/images/robot-demo.gif)

---

## 🎯 Engineering Focus

- **Real-Time Robot Control & Telemetry**: Server-authoritative 2D differential-drive kinematics with monotonic sequence numbering.
- **Network Impairment Simulation**: Planned runtime fault injection for latency (0–2000 ms), jitter (0–500 ms), and packet loss (0–50%).
- **Fail-Safe Robot Safety**: Latched Emergency Stop (`E-STOP`) override and automated safety watchdog timeout (2.0s).
- **Linux Systems Operations**: Safe non-root inspection via `/proc` and `psutil`, graceful signal dispatching (`SIGTERM`/`SIGKILL`), and port auditing (`ss`/`lsof`).
- **Session Telemetry & Replay**: SQLite-backed audit trails of telemetry frames and operator commands.
- **Containerized Deployment**: Multi-stage Linux container with health probes and persistent storage volumes.

---



---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client["Operator Web Client"]
        UI["HTML5 / Canvas Dashboard"]
        WSClient["WebSocket Client (Auto-Reconnect)"]
        MetricsUI["Telemetry & Latency Charts"]
    end

    subgraph Backend["FastAPI Backend (Asyncio)"]
        Router["REST & WebSocket Endpoints"]
        FaultInjector["Network Fault Injector (Phase 5)"]
        CmdValidator["Sequence & Command Validator"]
        Watchdog["Safety Watchdog Service"]
        SimEngine["2D Differential-Drive Simulator (20 Hz)"]
        LinuxMon["Linux System Monitor (Phase 9)"]
        SessionSvc["Session Recorder (Phase 8)"]
    end

    subgraph Persistence["Storage & Observability"]
        DB[("SQLite Database")]
        Logs["Rotating Structured Logs"]
    end

    UI --> WSClient
    WSClient <-->|/ws/robot (JSON)| Router
    Router --> FaultInjector
    FaultInjector --> CmdValidator
    CmdValidator --> SimEngine
    SimEngine --> Watchdog
    SimEngine -.->|State Broadcast| WSClient
    SimEngine --> SessionSvc
    SessionSvc --> DB
    LinuxMon -.-> Router
    CmdValidator -.-> Logs
    SimEngine -.-> Logs
```

---

## 📸 Interface Previews

> **Note on Visual Previews**: These panels represent the planned UI architecture and design system. As upcoming phases are implemented and connected to backend data feeds, they will be refreshed with live browser captures.

### 1. Robotics Operator Dashboard (Phase 2 Baseline)
![Teleop-Sim Operator Dashboard Preview](docs/images/teleop-dashboard.png)
*Displays the 2D robot arena, directional teleop controls, emergency stop trigger, and kinematic telemetry cards.*

---

### 2. Network Fault Injection & Latency Monitor (Design Preview — Phase 5)
![Network Fault Injection Preview](docs/images/network-monitoring.png)
*Operator controls to artificially induce latency (0–2000 ms), jitter (0–500 ms), and packet loss (0–50%) to stress-test control loops.*

---

### 3. Linux Systems & Event Log Stream (Design Preview — Phase 9)
![Linux System Monitoring Preview](docs/images/linux-monitoring.png)
*Real-time server telemetry (`psutil` CPU/RAM/Disk metrics) and application log streams.*

---

## ⚙️ Implemented Robot Engine & API (Phase 2)

### Robot Coordinate System

```text
                    +Y (North)
                     |
                     |
  -X (West) ---------+--------- +X (East)   [orientation = 0.0 rad faces East]
                     |
                     |
                    -Y (South)

Simulation Boundary: X ∈ [-50.0, 50.0] m, Y ∈ [-50.0, 50.0] m
Base Linear Velocity: 1.0 m/s (scaled by command speed 0.0–2.0)
Base Angular Velocity: 1.5 rad/s (left: +CCW, right: -CW)
Simulation Frequency: 20 Hz (50 ms tick interval)
Watchdog Timeout: 2.0 s inactivity threshold
```

### REST API Endpoints

| Method | Endpoint | Description | Phase |
|---|---|---|:---:|
| `GET` | `/health` | System liveness probe and simulation status | Phase 1 |
| `GET` | `/api/robot/state` | Retrieve authoritative 2D kinematic robot state | Phase 2 |
| `POST` | `/api/robot/command` | Submit validated movement command | Phase 2 |
| `POST` | `/api/robot/emergency-stop` | Trigger latched Emergency Stop (zeros velocities) | Phase 2 |
| `POST` | `/api/robot/reset` | Clear E-stop latch and return robot to origin `(0, 0)` | Phase 2 |
| `GET` | `/api/network/conditions` | Read current network fault parameters | Phase 2 |
| `POST` | `/api/network/conditions` | Update network fault parameters | Phase 2 |
| `GET` | `/api/metrics` | High-level telemetry counters and uptime | Phase 2 |
| `WS` | `/ws/robot` | Real-time bi-directional WebSocket interface | Phase 3 |

### Command & State Payload Samples

**Submit Movement Command (`POST /api/robot/command`)**:
```json
{
  "command_id": "cmd-001",
  "sequence_number": 1,
  "timestamp": 1793652000.0,
  "command_type": "MOVE_FORWARD",
  "speed": 1.0
}
```

**Acknowledgement Response**:
```json
{
  "command_id": "cmd-001",
  "sequence_number": 1,
  "status": "ACCEPTED",
  "reason": null,
  "server_timestamp": 1793652000.05
}
```

---

## 🐧 Linux Operations & System Inspection

The platform is engineered to run in native Linux, WSL2 (Ubuntu), or Linux containers, providing operations scripts in `scripts/`:

```bash
# Inspect system environment, CPU, RAM, disk, process, and port availability
bash scripts/system_diagnostics.sh

# Start backend as background daemon (PID recorded to logs/teleop-sim.pid)
bash scripts/start.sh

# Check process status and inspect open ports (ss / netstat)
bash scripts/status.sh

# Send graceful SIGTERM (15) with strict process-signature verification
bash scripts/stop.sh
```

Key Linux tools demonstrated in this project:
- **Process Management**: `ps -fp <PID>`, `pgrep`, `kill -15`, `kill -9` (with process signature guards).
- **Networking**: `ss -tulnp`, `curl -f http://localhost:8000/health`.
- **System Information**: `uname -srmo`, `free -m`, `df -h`.
- **Logs**: Structured rotating log files in `logs/`.

---

## 🚀 Quickstart & Installation

### Option 1: Native Linux / Windows WSL2

```bash
# 1. Clone the repository
git clone https://github.com/sunilkumar2170/robot-teleoperation-platform.git
cd robot-teleoperation-platform

# 2. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Start the application
PYTHONPATH=backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Docker & Docker Compose

```bash
# Build and run backend container in background
docker compose up --build -d

# Check container health and status
docker compose ps
docker compose logs -f

# Shutdown container
docker compose down
```

---

## 🧪 Automated Testing & Verification

The project enforces strict test-driven development using Pytest.

```bash
# Run full test suite
PYTHONPATH=backend python -m pytest backend/tests/ -v
```

**Verified Test Results (81 / 81 Passing)**:
```text
backend/tests/test_environment.py ....                                    [  4%]
backend/tests/test_robot.py ............................................. [100%]

============================== 81 passed in 2.80s ==============================
```

- **Environment & Scaffolding**: 4 tests
- **Robot Kinematics & Bounds**: 16 tests
- **Emergency Stop & Reset**: 8 tests
- **Safety Watchdog (2.0s Inactivity)**: 4 tests
- **Sequence Number & Command Validation**: 10 tests
- **REST Endpoints & Metrics**: 39 tests

---

## 📜 License

This project is licensed under the MIT License.
