"""
Teleop-Sim FastAPI Application
--------------------------------
Main application entry point. Coordinates:
  • Startup/shutdown lifespans
  • Database initialization (SQLite)
  • Structured rotating logging
  • 20 Hz differential-drive simulation engine loop
  • WebSocket broadcast synchronization
  • Linux process signal handlers (SIGTERM, SIGINT)
  • REST API routes and static frontend serving
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
from app.api.websocket import _init_simulator_callback
from app.core.config import settings
from app.database.database import init_db
from app.robot.simulator import get_simulator
from app.services.logging_service import setup_structured_logging

_START_TIME = time.time()
logger = logging.getLogger("teleop_sim")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # 1. Initialize rotating logs
    setup_structured_logging()
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.VERSION)

    # 2. Initialize database
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Database initialized at %s", settings.DATA_DIR / "teleop_sim.db")

    # 3. Register POSIX signal handlers on non-Windows platforms
    loop = asyncio.get_running_loop()

    def _handle_signal(sig_num: int) -> None:
        logger.warning("Received signal %d — initiating graceful shutdown", sig_num)
        loop.stop()

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _handle_signal, sig)

    # 4. Wire simulator broadcast to WebSocket manager
    _init_simulator_callback()

    # 5. Start robot simulation loop
    sim = get_simulator()
    await sim.start()
    logger.info(
        "Simulation loop started at %.1f Hz. Boundary: [%.1f, %.1f] x [%.1f, %.1f]",
        settings.SIMULATION_FREQUENCY_HZ,
        settings.BOUNDS_MIN_X,
        settings.BOUNDS_MAX_X,
        settings.BOUNDS_MIN_Y,
        settings.BOUNDS_MAX_Y,
    )

    yield  # Application runs here

    # Graceful shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    await sim.stop()
    logger.info("Simulation loop stopped. Shutdown complete.")


# ── Create FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time Robotics Teleoperation, Network Reliability and Linux Operations Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(routes.router)
app.include_router(websocket.router)


# ── Liveness Health Check Endpoint ────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="System health probe")
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


# ── Mount Frontend Static Assets ──────────────────────────────────────────────

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
