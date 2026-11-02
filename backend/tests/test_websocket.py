"""
Tests for WebSocket endpoint /ws/robot
"""
import pytest
from starlette.testclient import TestClient
from app.main import app

def test_websocket_connection_and_flow():
    client = TestClient(app)
    with client.websocket_connect("/ws/robot") as ws:
        # 1. Server sends initial ROBOT_STATE on connection
        init_msg = ws.receive_json()
        assert init_msg["type"] == "ROBOT_STATE"
        assert "data" in init_msg
        assert init_msg["data"]["robot_id"] is not None

        # 2. Ping-Pong Heartbeat
        ws.send_json({"type": "PING", "timestamp": 123456.0})
        pong = ws.receive_json()
        assert pong["type"] == "PONG"
        assert "server_timestamp" in pong

        # 3. Valid Command over WebSocket
        ws.send_json({
            "type": "COMMAND",
            "data": {
                "command_id": "ws-cmd-001",
                "sequence_number": 1,
                "command_type": "MOVE_FORWARD",
                "speed": 1.0,
            }
        })
        ack = ws.receive_json()
        assert ack["type"] == "COMMAND_ACK"
        assert ack["data"]["status"] == "ACCEPTED"
        assert ack["data"]["sequence_number"] == 1
