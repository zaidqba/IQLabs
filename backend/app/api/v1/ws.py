"""WebSocket live data endpoint."""
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.exceptions import AuthenticationError
from app.core.security import decode_token
from app.services.websocket_service import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/live")
async def websocket_live(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    Live data WebSocket endpoint.
    Authenticate via ?token=<jwt> query parameter.
    Broadcasts: readings, alarms, device_status, heartbeat events.

    Message format:
      {"type": "reading", "channel_code": "STACK.PM11", "value": "123.4", ...}
      {"type": "alarm", "event_type": "alarm_triggered", "alarm_id": 5, ...}
      {"type": "device_status", "device_id": 1, "status_code": "ONLINE"}
      {"type": "heartbeat", "device_id": 1, "ntp_offset_ms": 12, ...}
    """
    # Validate JWT before accepting connection
    try:
        payload = decode_token(token)
        if payload.get("token_type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
    except AuthenticationError:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await ws_manager.connect(websocket)
    try:
        # Keep connection open until client disconnects
        while True:
            await websocket.receive_text()  # Consume any client messages (ping/pong)
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)
