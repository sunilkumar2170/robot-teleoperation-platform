# Teleop-Sim: Real-Time Robotics Teleoperation & Network Reliability Platform

Teleop-Sim is a production-grade remote robotics teleoperation simulator designed to mirror the challenges faced by **Robotics Forward Deployed Engineers (FDE)**. It simulates real-world physical and network constraints—including dynamic latency, jitter, packet loss, WebSocket disconnections, command acknowledgement, safety watchdog timeouts, and emergency stop overrides—alongside integrated Linux systems monitoring and operations.

---

## Application Screenshots

> Screenshots refresh automatically as each implementation phase completes.  
> Run `python docs/generate_screenshots.py` to regenerate after any UI change.

### 1. Robotics Operator Dashboard
<!-- Phase 2+ : HTML5 Canvas robot, WASD controls, battery & status telemetry -->
![Teleop-Sim Operator Dashboard — 2D robot canvas, direction controls, emergency stop, and live status cards](docs/images/teleop-dashboard.png)

The main operator view shows the 2D robot canvas with heading indicator, directional control buttons, an **Emergency Stop** override, and real-time telemetry cards (position, battery, connection status).  
*Robot kinematics and WebSocket control are implemented in Phase 2 & 3.*

---

### 2. Network Fault Injection & Latency Dashboard
<!-- Phase 5 : latency/jitter/packet-loss sliders, live RTT chart -->
![Network monitoring panel — latency, jitter, and packet-loss sliders with live RTT chart](docs/images/network-monitoring.png)

The network panel provides runtime sliders for **Latency (0–2000 ms)**, **Jitter (0–500 ms)**, and **Packet Loss (0–50 %)**, plus a live round-trip-time chart so operators can observe the direct impact of simulated faults on robot control.  
*Network fault engine and live telemetry charting implemented in Phase 5.*

---

### 3. Linux System Monitoring & Application Logs
<!-- Phase 9 : psutil CPU/MEM/Disk, log stream, process status -->
![Linux monitoring panel — CPU, memory, disk metrics and live application log stream](docs/images/linux-monitoring.png)

The Linux operations panel surfaces real-time host metrics (CPU %, RSS memory, disk, WebSocket connection count, uptime) pulled via `psutil` and `/proc`, alongside a live-streaming application event log (equivalent to `tail -f logs/application.log`).  
*Full Linux monitoring module implemented in Phase 9.*

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph Client["Operator Browser Dashboard"]
        UI["HTML5 / Canvas UI"]
        WSClient["WebSocket Client (Auto-Reconnect)"]
        MetricsUI["Telemetry & Latency Graphs"]
    end

    subgraph Backend["FastAPI Backend (Asyncio)"]
        Router["REST & WebSocket Endpoints"]
        FaultInjector["Network Fault Injector<br/>(Latency, Jitter, Packet Drop)"]
        CmdValidator["Command & Sequence Validator"]
        Watchdog["Safety Watchdog Service"]
        SimEngine["2D Robot Kinematics Simulator<br/>(Authoritative State)"]
        LinuxMon["Linux System Monitor<br/>(Procfs, psutil, Netstat)"]
        SessionSvc["Session Recorder & Replay Service"]
    end

    subgraph Storage["Persistence & Logs"]
        DB[("SQLite Database")]
        Logs["Rotating Structured Logs<br/>(App, Robot, Network, Security)"]
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

## 2. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, WebSockets, Pydantic v2, SQLAlchemy 2.0, SQLite, Asyncio
- **Frontend**: Vanilla JavaScript (ES6+), HTML5 Canvas, Modern CSS3 Dark Theme
- **Linux Operations**: Ubuntu / WSL2, Bash automation, `procfs`, POSIX signals (`SIGTERM`, `SIGINT`), network inspection (`ss`, `lsof`)
- **Containerization**: Docker, Docker Compose, non-root security container
- **Testing**: Pytest, FastAPI TestClient, Asyncio WebSocket tests

---

## 3. Project Directory Structure

```text
teleop-sim/
├── backend/
│   ├── app/
│   │   ├── main.py                  # Application entry point & lifespan
│   │   ├── core/                    # Settings & configuration
│   │   ├── api/                     # REST routes & WebSocket handler
│   │   ├── robot/                   # Kinematics, authoritative state & safety watchdog
│   │   ├── network/                 # Fault injector & latency metrics
│   │   ├── linux/                   # Safe Linux system monitor
│   │   ├── services/                # Session recording & structured logging
│   │   ├── database/                # SQLite connection & SQLAlchemy models
│   │   └── schemas/                 # Pydantic validation schemas
│   ├── tests/                       # Pytest automated test suite
│   ├── requirements.txt             # Python dependencies
│   └── Dockerfile                   # Production container definition
├── frontend/
│   ├── index.html                   # Teleoperation web interface
│   ├── css/
│   │   └── style.css                # Dark theme design system
│   └── js/
│       ├── app.js                   # Application bootstrap
│       ├── websocket.js             # Resilient WebSocket client with backoff
│       ├── robot.js                 # HTML5 Canvas 2D robot renderer
│       ├── dashboard.js             # UI controls & event binders
│       └── metrics.js               # Latency & telemetry tracking
├── scripts/
│   ├── start.sh                     # Service daemon launcher
│   ├── stop.sh                      # Graceful shutdown (SIGTERM -> SIGKILL)
│   ├── status.sh                    # Process & port inspector
│   └── system_diagnostics.sh        # Host & container environment diagnostics
├── logs/                            # Rotating log files directory
├── data/                            # Persistent SQLite database storage
├── docker-compose.yml               # Multi-platform container orchestration
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore rules
└── README.md                        # Documentation
```

---

## 4. Environment & Installation

### Option A: Native Linux / Windows WSL2 (Ubuntu)

1. **Verify Python 3.11+ & prerequisites**:
   ```bash
   python3 --version
   ```

2. **Create and activate a virtual environment**:
   ```bash
   cd teleop-sim
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Run backend**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
   ```

### Option B: Docker & Docker Compose

1. **Build and start container**:
   ```bash
   docker compose up --build -d
   ```

2. **Inspect logs**:
   ```bash
   docker compose logs -f
   ```

3. **Stop container**:
   ```bash
   docker compose down
   ```

---

## 5. Linux Diagnostic Scripts

The `scripts/` directory provides operational tooling:

- `bash scripts/system_diagnostics.sh`: Gathers distribution, kernel, CPU, memory, disk, process, and port diagnostics.
- `bash scripts/start.sh`: Launches the backend in the background and writes PID to `logs/teleop-sim.pid`.
- `bash scripts/status.sh`: Checks process status and verifies port 8000 is accepting connections.
- `bash scripts/stop.sh`: Sends a graceful `SIGTERM` (signal 15), verifies process termination, and cleans up PID tracking.

---

## 6. Running Tests

Run the test suite with Pytest:

```bash
cd teleop-sim/backend
pytest -v
```

---

## Phase 2: Robot Simulation Engine

**Status**: Complete ✅

### What Was Built

| Component | File | Description |
|-----------|------|-------------|
| Robot State | `backend/app/robot/state.py` | Mutable authoritative state dataclass (x, y, orientation, battery, mode) |
| Kinematics Engine | `backend/app/robot/simulator.py` | 20 Hz differential-drive asyncio simulation loop with boundary enforcement |
| Safety System | `backend/app/robot/safety.py` | Emergency stop, safety watchdog, command validation |
| Command Schema | `backend/app/schemas/command.py` | Pydantic v2 validated command + acknowledgement models |
| Robot Schema | `backend/app/schemas/robot.py` | Pydantic v2 robot state response model |
| REST API | `backend/app/api/routes.py` | 7 endpoints for state, commands, E-stop, reset, network, metrics |
| WebSocket stub | `backend/app/api/websocket.py` | Phase 3 placeholder at `/ws/robot` |
| Tests | `backend/tests/test_robot.py` | 77 Pytest tests (81 total including Phase 1) |

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe with simulation status |
| `GET` | `/api/robot/state` | Authoritative robot state |
| `POST` | `/api/robot/command` | Submit movement command |
| `POST` | `/api/robot/emergency-stop` | Immediate halt + latch |
| `POST` | `/api/robot/reset` | Clear E-stop, return to (0,0) |
| `GET` | `/api/network/conditions` | Read network fault settings |
| `POST` | `/api/network/conditions` | Update network fault settings |
| `GET` | `/api/metrics` | Command counters + robot snapshot |

### Command Message Format

```json
{
  "command_id": "cmd-928079e9",
  "sequence_number": 1,
  "timestamp": 1793652000.0,
  "command_type": "MOVE_FORWARD",
  "speed": 1.0
}
```

Valid `command_type` values: `MOVE_FORWARD`, `MOVE_BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `EMERGENCY_STOP`

### Acknowledgement Response

```json
{
  "command_id": "cmd-928079e9",
  "sequence_number": 1,
  "status": "ACCEPTED",
  "reason": null,
  "server_timestamp": 1793652000.05
}
```

Possible `status` values: `ACCEPTED`, `REJECTED`, `EMERGENCY_STOP_ACTIVE`

### Live API Demonstration

```
STEP 1: Initial state          x=0.0  y=0.0  orientation=0.0  mode=IDLE
STEP 2: MOVE_FORWARD seq=1     → ACCEPTED
STEP 3: Position after tick    x=0.25 y=0.0  orientation=0.0  mode=MOVING
STEP 4: TURN_LEFT seq=2        → ACCEPTED
STEP 5: Orientation after tick x=0.25 y=0.0  orientation=0.375 mode=MOVING
STEP 6: EMERGENCY STOP         → acknowledged=True
STEP 7: MOVE_FORWARD blocked   → EMERGENCY_STOP_ACTIVE
STEP 8: RESET                  → acknowledged=True
STEP 9: State after reset      x=0.0  y=0.0  emergency_stop=False mode=IDLE
STEP 10: MOVE after reset      → ACCEPTED
STEP 11: Metrics               received=4 accepted=3 rejected=1 estops=1 resets=1
```

### Robot Coordinate System

```
                    +Y (North)
                     |
                     |
  -X (West) ---------+--------- +X (East)   ← orientation=0.0 faces East
                     |
                     |
                    -Y (South)

Boundary: X ∈ [-50, 50]  Y ∈ [-50, 50]
Speed range: 0.0 – 2.0 (normalised multiplier)
Simulation frequency: 20 Hz (configurable via SIMULATION_FREQUENCY_HZ)
Watchdog timeout: 2.0 s (configurable via WATCHDOG_TIMEOUT_SECONDS)
```

### Run Tests

```bash
cd teleop-sim
PYTHONPATH=backend python -m pytest backend/tests/ -v
# → 81 passed in ~3s
```

---

## 7. Regenerate Screenshots

Screenshots are generated programmatically from the real application UI using Pillow. Run this whenever the frontend changes:

```bash
# From the teleop-sim/ root
python docs/generate_screenshots.py
```

Each subsequent implementation phase will replace the placeholder panels with genuine live-captured application views.
