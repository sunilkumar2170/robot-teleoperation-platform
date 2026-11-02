"""
Teleop-Sim FastAPI Application
--------------------------------
Wires together:
  • Robot simulation engine lifecycle (startup / graceful shutdown)
  • REST API routes
  • Phase 3 WebSocket endpoint placeholder
  • Static frontend file serving
  • CORS, SIGTERM/SIGINT handlers
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes, websocket
from app.core.config import settings
from app.robot.simulator import get_simulator

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("teleop_sim")

_START_TIME = time.time()


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:  ensure data/logs directories exist, start simulation loop.
    Shutdown: gracefully stop the simulation loop and flush logs.
    """
    # Create runtime directories
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Register SIGTERM / SIGINT handlers so `kill -15 <pid>` works correctly
    loop = asyncio.get_running_loop()

    def _handle_signal(sig_num: int) -> None:
        logger.warning("Received signal %d — initiating graceful shutdown", sig_num)
        loop.stop()

    # Only register on POSIX systems (Linux / macOS / WSL2 container)
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _handle_signal, sig)

    # Start robot simulation loop
    sim = get_simulator()
    await sim.start()
    logger.info(
        "%s v%s started in %s environment — simulation loop active at %.1f Hz",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
        settings.SIMULATION_FREQUENCY_HZ,
    )

    yield  # ← application runs here ────────────────────────────────────────

    # Graceful shutdown
    logger.info("Shutdown initiated — stopping simulation loop")
    await sim.stop()
    logger.info("%s shutdown complete", settings.PROJECT_NAME)


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Real-Time Robotics Teleoperation, Network Reliability and Linux Operations Platform. "
        "Demonstrates skills relevant to a Robotics Forward Deployed Engineer."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(routes.router)
app.include_router(websocket.router)


# ── Health check (top-level for Docker HEALTHCHECK compatibility) ─────────────

@app.get("/health", tags=["System"], summary="Liveness probe")
async def health_check():
    uptime = time.time() - _START_TIME
    sim = get_simulator()
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 2),
        "simulation_running": sim._running,
        "robot_id": sim.state.robot_id,
        "timestamp": time.time(),
    }


# ── Static frontend ───────────────────────────────────────────────────────────

_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


# ── Direct entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
