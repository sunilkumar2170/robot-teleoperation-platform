import sys
import pytest
from starlette.testclient import TestClient

def test_python_version():
    """Verify runtime Python version is at least 3.11."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, current: {sys.version}"

def test_core_dependencies_importable():
    """Verify all core dependencies can be imported successfully."""
    import fastapi
    import uvicorn
    import pydantic
    import sqlalchemy
    import websockets
    import psutil
    import httpx
    
    assert fastapi.__version__ is not None
    assert pydantic.__version__ is not None
    assert sqlalchemy.__version__ is not None
    assert psutil.__version__ is not None

def test_app_health_endpoint():
    """Verify FastAPI application boots and /health endpoint returns HTTP 200."""
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Teleop-Sim"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data

def test_settings_initialization():
    """Verify core Settings load defaults properly."""
    from app.core.config import settings
    assert settings.PROJECT_NAME == "Teleop-Sim"
    assert settings.SIMULATION_FREQUENCY_HZ > 0
    assert settings.WATCHDOG_TIMEOUT_SECONDS > 0
    assert settings.BOUNDS_MIN_X < settings.BOUNDS_MAX_X
    assert settings.BOUNDS_MIN_Y < settings.BOUNDS_MAX_Y
