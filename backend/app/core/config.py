import os
from pathlib import Path
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Teleop-Sim"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/teleop_sim.db")
    
    # Simulation settings
    SIMULATION_FREQUENCY_HZ: float = float(os.getenv("SIMULATION_FREQUENCY_HZ", "20.0"))
    ROBOT_DEFAULT_LINEAR_SPEED: float = float(os.getenv("ROBOT_DEFAULT_LINEAR_SPEED", "1.0"))
    ROBOT_DEFAULT_ANGULAR_SPEED: float = float(os.getenv("ROBOT_DEFAULT_ANGULAR_SPEED", "1.5"))
    BOUNDS_MIN_X: float = float(os.getenv("BOUNDS_MIN_X", "-50.0"))
    BOUNDS_MAX_X: float = float(os.getenv("BOUNDS_MAX_X", "50.0"))
    BOUNDS_MIN_Y: float = float(os.getenv("BOUNDS_MIN_Y", "-50.0"))
    BOUNDS_MAX_Y: float = float(os.getenv("BOUNDS_MAX_Y", "50.0"))
    
    # Safety settings
    WATCHDOG_TIMEOUT_SECONDS: float = float(os.getenv("WATCHDOG_TIMEOUT_SECONDS", "2.0"))
    EMERGENCY_STOP_LOCKOUT: bool = os.getenv("EMERGENCY_STOP_LOCKOUT", "true").lower() == "true"
    
    # Network fault injection defaults
    DEFAULT_LATENCY_MS: float = float(os.getenv("DEFAULT_LATENCY_MS", "0.0"))
    DEFAULT_JITTER_MS: float = float(os.getenv("DEFAULT_JITTER_MS", "0.0"))
    DEFAULT_PACKET_LOSS_PCT: float = float(os.getenv("DEFAULT_PACKET_LOSS_PCT", "0.0"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
