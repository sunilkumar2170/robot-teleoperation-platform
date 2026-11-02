"""
Session Recording & Replay Service
----------------------------------
Records live operator teleoperation sessions to SQLite:
  • Command executions
  • Robot kinematic state trajectory (downsampled to 5 Hz for efficient storage)
  • Safety events (watchdog timeouts, emergency stops, resets)
  • Network condition updates
  • WebSocket connection/disconnection events

Also provides session replay to play back a past run frame-by-frame.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import SessionEvent, SessionRecord

logger = logging.getLogger("services.session")


class SessionRecordingService:
    """Manages active session recording and retrieval."""

    def __init__(self):
        self.active_session_id: Optional[str] = None
        self.active_session_name: Optional[str] = None
        self._last_state_record_time: float = 0.0

    def is_recording(self) -> bool:
        return self.active_session_id is not None

    def start_session(self, session_name: Optional[str] = None, notes: Optional[str] = None) -> Dict:
        """Begin recording a new teleoperation session."""
        db: Session = SessionLocal()
        try:
            # End any existing active session
            if self.active_session_id:
                self.stop_session()

            session_id = f"sess-{uuid.uuid4().hex[:12]}"
            name = session_name or f"Teleop Session {time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            record = SessionRecord(
                id=session_id,
                session_name=name,
                created_at=time.time(),
                is_active=True,
                command_count=0,
                event_count=0,
                notes=notes,
            )
            db.add(record)
            db.commit()

            self.active_session_id = session_id
            self.active_session_name = name
            logger.info("Started recording session %s ('%s')", session_id, name)
            return record.to_dict()
        finally:
            db.close()

    def stop_session(self) -> Optional[Dict]:
        """Finalize and close the active session."""
        if not self.active_session_id:
            return None

        db: Session = SessionLocal()
        try:
            record = db.query(SessionRecord).filter(SessionRecord.id == self.active_session_id).first()
            if record:
                record.ended_at = time.time()
                record.is_active = False
                db.commit()
                out = record.to_dict()
            else:
                out = None

            logger.info("Stopped recording session %s", self.active_session_id)
            self.active_session_id = None
            self.active_session_name = None
            return out
        finally:
            db.close()

    def record_event(self, event_type: str, data: dict) -> None:
        """Record an event to the active session (if recording)."""
        if not self.active_session_id:
            return

        # Throttle continuous state updates to max 5 Hz (every 200 ms)
        now = time.time()
        if event_type == "STATE":
            if now - self._last_state_record_time < 0.2:
                return
            self._last_state_record_time = now

        db: Session = SessionLocal()
        try:
            event = SessionEvent(
                session_id=self.active_session_id,
                timestamp=now,
                event_type=event_type,
                data_json=json.dumps(data),
            )
            db.add(event)

            # Increment session stats
            record = db.query(SessionRecord).filter(SessionRecord.id == self.active_session_id).first()
            if record:
                record.event_count += 1
                if event_type == "COMMAND":
                    record.command_count += 1

            db.commit()
        except Exception as exc:
            logger.warning("Failed to record event %s: %s", event_type, exc)
        finally:
            db.close()

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """Return list of all recorded sessions."""
        db: Session = SessionLocal()
        try:
            records = db.query(SessionRecord).order_by(SessionRecord.created_at.desc()).limit(limit).all()
            return [r.to_dict() for r in records]
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session detail with all events."""
        db: Session = SessionLocal()
        try:
            record = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
            if not record:
                return None
            data = record.to_dict()
            events = db.query(SessionEvent).filter(SessionEvent.session_id == session_id).order_by(SessionEvent.timestamp.asc()).all()
            data["events"] = [e.to_dict() for e in events]
            return data
        finally:
            db.close()

    def get_session_replay(self, session_id: str) -> Optional[List[Dict]]:
        """Get ordered event list formatted for frontend playback."""
        detail = self.get_session(session_id)
        if not detail:
            return None
        return detail.get("events", [])


_session_service = SessionRecordingService()


def get_session_service() -> SessionRecordingService:
    return _session_service
