"""WebSocket endpoint — Phase 3 placeholder."""
from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/robot")
async def robot_websocket(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for robot command streaming and state broadcast.
    Full implementation in Phase 3.
    """
    await websocket.accept()
    await websocket.send_json({
        "type": "info",
        "message": "WebSocket connected. Full teleoperation streaming implemented in Phase 3.",
    })
    await websocket.close()
