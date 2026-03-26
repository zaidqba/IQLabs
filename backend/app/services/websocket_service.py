"""
IQ-RAD WebSocket Fan-out Service
Manages connected WebSocket clients and broadcasts live events.
Clients receive: readings, alarms, device_status, heartbeat messages.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional
from weakref import WeakSet

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Central manager for all connected WebSocket clients.
    Uses WeakSet so disconnected clients are garbage-collected automatically.
    Thread-safe via asyncio single-threaded event loop.
    """

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info(
            "ws_client_connected",
            extra={"total_clients": len(self._connections)},
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info(
            "ws_client_disconnected",
            extra={"total_clients": len(self._connections)},
        )

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        dead = set()

        async with self._lock:
            clients = set(self._connections)

        for websocket in clients:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(payload)
            except Exception:
                dead.add(websocket)

        if dead:
            async with self._lock:
                self._connections -= dead

    async def broadcast_reading(
        self,
        channel_code: str,
        channel_name: str,
        value: str,
        uom: str,
        severity: str,
        quality_flag: str,
        measured_at: datetime,
        channel_id: int,
    ) -> None:
        await self.broadcast({
            "type": "reading",
            "channel_id": channel_id,
            "channel_code": channel_code,
            "channel_name": channel_name,
            "value": value,
            "uom": uom,
            "severity": severity,
            "quality_flag": quality_flag,
            "measured_at": measured_at.isoformat(),
        })

    async def broadcast_device_status(
        self,
        device_id: int,
        device_code: str,
        status_code: str,
        detail: Optional[str] = None,
    ) -> None:
        await self.broadcast({
            "type": "device_status",
            "device_id": device_id,
            "device_code": device_code,
            "status_code": status_code,
            "detail": detail,
        })

    async def broadcast_heartbeat(
        self,
        device_id: int,
        ntp_offset_ms: Optional[int],
        is_ntp_valid: bool,
        sequence_num: int,
    ) -> None:
        await self.broadcast({
            "type": "heartbeat",
            "device_id": device_id,
            "ntp_offset_ms": ntp_offset_ms,
            "is_ntp_valid": is_ntp_valid,
            "sequence_num": sequence_num,
        })

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Global singleton instance
ws_manager = WebSocketManager()
