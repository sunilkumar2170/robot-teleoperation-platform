"""
Tests for SQLite Session Recording and Replay Service
"""
import pytest
from app.services.session_service import SessionRecordingService

def test_session_lifecycle():
    service = SessionRecordingService()
    # 1. Start session
    session = service.start_session("Test Session", notes="Testing replay")
    assert service.is_recording()
    session_id = session["session_id"]
    
    # 2. Record events
    service.record_event("COMMAND", {"command_type": "MOVE_FORWARD", "speed": 1.0})
    service.record_event("SAFETY", {"event": "EMERGENCY_STOP"})
    
    # 3. Stop session
    stopped = service.stop_session()
    assert not service.is_recording()
    assert stopped["session_id"] == session_id
    assert stopped["command_count"] >= 1
    assert stopped["event_count"] >= 2
    
    # 4. Replay
    replay = service.get_session_replay(session_id)
    assert len(replay) >= 2
    assert replay[0]["event_type"] in ("COMMAND", "SAFETY")
