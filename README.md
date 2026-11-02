# Teleop-Sim 🤖
### Real-Time Robotics Teleoperation & Network Reliability Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-RFC_6455-orange.svg)](https://websockets.readthedocs.io/)
[![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20WSL2-FCC624.svg?logo=linux&logoColor=black)](https://ubuntu.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-87%20Passed-brightgreen.svg)](https://pytest.org/)
[![Status](https://img.shields.io/badge/Status-Fully%20Functional-brightgreen.svg)]()

> **Building reliable remote robot control systems with Python, Linux, WebSockets and Docker.**  
> Teleop-Sim is a functional robotics teleoperation platform designed to demonstrate real-world solutions for remote robot control over unreliable networks.

The project implements real-time WebSocket communication, differential-drive kinematics, network fault injection, Linux diagnostics, process management, session replay, and deployment reliability — demonstrating the core competencies of a **Robotics Forward Deployed Engineer (FDE)**.

**Repository:** [https://github.com/sunilkumar2170/robot-teleoperation-platform](https://github.com/sunilkumar2170/robot-teleoperation-platform)

---

## 🎥 Live Simulation Demo

The animation below is generated directly by executing the underlying differential-drive kinematics simulation engine (`backend/app/robot/simulator.py`) at 20 Hz, showing forward drive, turning, velocity scaling, emergency stop latching, and home-position reset:

![Teleop-Sim 2D Robot Simulation Demo](docs/images/robot-demo.gif)

---

## 🎯 Engineering Focus

- **Real-Time Robot Control & Telemetry**: Server-authoritative 2D differential-drive kinematics with monotonic sequence numbering and WebSocket streaming.
- **Network Impairment Simulation**: Runtime fault injection for latency (0–2000 ms), jitter (0–500 ms), and packet loss (0–50%).
- **Fail-Safe Robot Safety**: Latched Emergency Stop (`E-STOP`) override and automated safety watchdog timeout (2.0s).
- **Linux Systems Operations**: Safe non-root inspection via `/proc` and `psutil`, graceful signal dispatching (`SIGTERM`/`SIGKILL`), and port auditing (`ss`/`lsof`).
- **Session Telemetry & Replay**: SQLite-backed audit trails of telemetry frames, commands, and full session replay.
- **Containerized Deployment**: Multi-stage Linux container with health probes and persistent storage volumes.

---

## 🗺️ Project Roadmap & Completion Status

All 12 phases have been fully implemented and verified:

| Phase | Description | Status |
|:---:|---|:---:|
| **Phase 1** | Project scaffolding, multi-OS configuration, Dockerfile, shell scripts | **Complete** ✅ |
| **Phase 2** | Python 2D robot kinematics engine, differential drive, REST API | **Complete** ✅ |
| **Phase 3** | WebSocket bi-directional command streaming and state broadcast (`/ws/robot`) | **Complete** ✅ |
| **Phase 4** | Interactive browser canvas dashboard, D-pad & keyboard WASD teleop | **Complete** ✅ |
| **Phase 5** | Network fault injection engine (latency, jitter, drop) & RTT telemetry | **Complete** ✅ |
| **Phase 6** | Safety watchdog server-side verification and E-stop UI workflow | **Complete** ✅ |
| **Phase 7** | Resilient auto-reconnection with exponential backoff and state recovery | **Complete** ✅ |
| **Phase 8** | SQLite session recording, audit event logging, and playback replay service | **Complete** ✅ |
| **Phase 9** | Linux system monitoring (`psutil`, `/proc`), log rotating streams, and diagnostics | **Complete** ✅ |
| **Phase 10** | Production Docker Compose multi-container deployment and volume persistence | **Complete** ✅ |
| **Phase 11** | End-to-end integration test suite (87 tests passing) | **Complete** ✅ |
| **Phase 12** | Comprehensive documentation, Mermaid architecture diagram, and demo GIF | **Complete** ✅ |

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph Client["Operator Web Client"]
        direction TB
        UI["HTML5 & Canvas UI"]
        WSClient["WebSocket Client (Auto-Reconnect)"]
        MetricsUI["Telemetry & Latency Charts"]
        UI --> WSClient
    end

    subgraph Backend["FastAPI Backend (Asyncio)"]
        direction TB
        Router["REST & WebSocket Endpoints (/ws/robot)"]
        FaultInjector["Network Fault Injector (Latency / Jitter / Drop)"]
        CmdValidator["Sequence & Command Validator"]
        SimEngine["2D Differential-Drive Kinematics Engine (20 Hz)"]
        Watchdog["Safety Watchdog Service (2.0s Inactivity)"]
        SessionSvc["Session Recorder & Replay Service"]
        LinuxMon["Linux System Monitor (psutil / /proc)"]

        Router --> FaultInjector
        FaultInjector --> CmdValidator
        CmdValidator --> SimEngine
        SimEngine --> Watchdog
        SimEngine --> SessionSvc
        LinuxMon -.-> Router
    end

    subgraph Persistence["Storage & Observability"]
        direction LR
        DB[("SQLite Database
(Sessions & Events)")]
        Logs["Rotating Structured Logs
(App, Robot, Network, Security)"]
    end

    WSClient -->|"Commands (JSON)"| Router
    SimEngine -.->|"State Broadcast (20 Hz)"| WSClient
    SessionSvc --> DB
    CmdValidator -.-> Logs
    SimEngine -.-> Logs
    Watchdog -.-> Logs
```

---

## 📁 Project System Structure

```text
teleop-sim/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI lifespan, CORS & router mounting
│   │   ├── core/
│   │   │   └── config.py            # Pydantic v2 typed settings & environment loader
│   │   ├── api/
│   │   │   ├── routes.py            # REST endpoints (state, commands, E-stop, reset, sessions)
│   │   │   └── websocket.py         # Bi-directional /ws/robot WebSocket streaming
│   │   ├── robot/
│   │   │   ├── state.py             # Authoritative mutable RobotState dataclass
│   │   │   ├── simulator.py         # 20 Hz differential-drive kinematics engine
│   │   │   └── safety.py            # Latched E-stop, 2.0s watchdog & sequence validation
│   │   ├── network/
│   │   │   ├── fault_injector.py    # Runtime latency, jitter & packet loss simulation
│   │   │   └── latency.py           # Real-time RTT & telemetry tracker
│   │   ├── linux/
│   │   │   └── system_monitor.py    # Safe non-root /proc & psutil host inspection
│   │   ├── services/
│   │   │   ├── session_service.py   # SQLite session recording & replay engine
│   │   │   └── logging_service.py   # Rotating structured logs (app, robot, net, sec)
│   │   ├── database/
│   │   │   ├── database.py          # SQLite engine & sessionmaker factory
│   │   │   └── models.py            # SQLAlchemy SessionRecord & SessionEvent ORM models
│   │   └── schemas/
│   │       ├── command.py           # Validated Pydantic command & ack schemas
│   │       └── robot.py             # Authoritative state response schema
│   ├── tests/
│   │   ├── test_environment.py      # Python 3.11+, dependency & config baseline tests
│   │   ├── test_robot.py            # Kinematics, boundaries, E-stop & REST API tests
│   │   ├── test_websocket.py        # /ws/robot connection, broadcast & command tests
│   │   ├── test_network.py          # Latency delay, jitter & deterministic packet drop tests
│   │   ├── test_sessions.py         # SQLite recording, lifecycle & replay tests
│   │   └── test_linux.py            # System introspection & resource audit tests
│   ├── Dockerfile                   # Multi-stage production container with Linux tools
│   └── requirements.txt             # Pinned production dependencies
├── frontend/
│   ├── index.html                   # Dark-themed robotics operator cockpit
│   ├── css/
│   │   └── style.css                # Polished design system (grid, telemetry cards, d-pad)
│   └── js/
│       ├── app.js                   # Client lifecycle bootstrap & component wiring
│       ├── websocket.js             # Resilient WS client with exponential backoff & state recovery
│       ├── robot.js                 # 2D Canvas arena renderer with trail & E-stop warning
│       ├── dashboard.js             # D-pad, keyboard teleop, sliders, session controls & log viewer
│       └── metrics.js               # Real-time RTT canvas chart & telemetry plotter
├── scripts/
│   ├── start.sh                     # Daemon launcher with PID tracking
│   ├── stop.sh                      # Graceful shutdown (SIGTERM -> SIGKILL) with signature verification
│   ├── status.sh                    # Process health, listening ports & health endpoint probe
│   └── system_diagnostics.sh        # Linux OS, kernel, CPU, RAM, disk & Docker diagnostics
├── docs/
│   ├── generate_demo_gif.py         # Kinematics-driven simulation GIF generator
│   └── images/
│       ├── robot-demo.gif           # Live 20 Hz simulation animation
│       ├── teleop-dashboard.png     # Operator cockpit visual preview
│       ├── network-monitoring.png   # Fault injection controls preview
│       └── linux-monitoring.png     # Linux telemetry & logs preview
├── data/                            # Persistent SQLite database storage
├── logs/                            # Rotating log files directory
├── docker-compose.yml               # Production container orchestration
├── .env.example                     # Parameterized environment template
├── .gitignore                       # Repository ignore rules
└── README.md                        # Documentation & engineering manual
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

**Verified Test Results (87 / 87 Passing)**:
```text
backend/tests/test_environment.py ....                                    [  4%]
backend/tests/test_linux.py .                                             [  5%]
backend/tests/test_network.py ...                                         [  9%]
backend/tests/test_robot.py ............................................. [ 97%]
backend/tests/test_sessions.py .                                          [ 98%]
backend/tests/test_websocket.py .                                         [100%]

============================== 87 passed in 2.60s ==============================
```

- **Environment & Scaffolding**: 4 tests
- **Linux Diagnostics & Process Introspection**: 1 test
- **Network Fault Injector & Latency Tracking**: 3 tests
- **Robot Kinematics, Boundaries, Emergency Stop & Watchdog**: 77 tests
- **SQLite Session Recording & Replay**: 1 test
- **WebSocket Streaming, State Broadcast & Ping-Pong**: 1 test

---

## 📜 License

This project is licensed under the MIT License.
