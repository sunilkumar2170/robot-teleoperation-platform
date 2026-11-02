"""
SQLAlchemy ORM Models for Teleop-Sim
------------------------------------
Defines:
  • SessionRecord: telemetry session metadata (start, end, duration, counts)
  • SessionEvent: granular time-series events (commands, state frames, safety events)
"""
from __future__ import annotations

import time
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, index=True)
    session_name = Column(String(100), nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)
    ended_at = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    command_count = Column(Integer, default=0, nullable=False)
    event_count = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    events = relationship("SessionEvent", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "session_id": self.id,
            "session_name": self.session_name,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "duration_seconds": round((self.ended_at or time.time()) - self.created_at, 2),
            "is_active": self.is_active,
            "command_count": self.command_count,
            "event_count": self.event_count,
            "notes": self.notes,
        }


class SessionEvent(Base):
    __tablename__ = "session_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    timestamp = Column(Float, default=time.time, nullable=False)
    event_type = Column(String(30), nullable=False)  # COMMAND, STATE, SAFETY, NETWORK, CONNECTION
    data_json = Column(Text, nullable=False)         # JSON payload

    session = relationship("SessionRecord", back_populates="events")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": json.loads(self.data_json),
        }
