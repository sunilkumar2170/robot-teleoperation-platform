"""
Database Connection & Session Engine
------------------------------------
SQLAlchemy SQLite database setup with WAL mode and autocommit session factory.
"""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

db_path = settings.DATA_DIR / "teleop_sim.db"
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for API endpoints to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables."""
    from app.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
