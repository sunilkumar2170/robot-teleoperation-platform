# Teleop-Sim: Real-Time Robotics Teleoperation & Network Reliability Platform

Teleop-Sim is a production-grade remote robotics teleoperation simulator designed to mirror the challenges faced by **Robotics Forward Deployed Engineers (FDE)**. It simulates real-world physical and network constraints—including dynamic latency, jitter, packet loss, WebSocket disconnections, command acknowledgement, safety watchdog timeouts, and emergency stop overrides—alongside integrated Linux systems monitoring and operations.

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
