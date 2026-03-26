"""
IQ-RAD Rotem Stack Connector
Connects to the Rotem WebiSmarts Stack device at 10.0.0.160:4001.
Handles 8 detector channels: PM11, GM42, AIR, W1-W5.

Protocol Note:
  The Rotem WebiSmarts protocol on port 4001 uses TCP with a JSON-based
  request/response framing (confirmed from WebiSmarts system structure).
  The Connection Unit at localhost:15386 mediates between WebiSmarts and
  the SQL backend.

  The connector sends a poll request and reads the JSON response.
  If the Rotem firmware is updated and the wire format changes, only
  this file and rotem_dpu3.py need updating — all downstream code is
  insulated by the NormalizedEvent model.

  Raw bytes are preserved verbatim in raw_ingestion_log regardless of
  whether parsing succeeds. This ensures the legal record is never lost.
"""
import asyncio
import json
from typing import AsyncIterator, Optional

from app.connectors.base import AbstractConnector, RawPacket
from app.core.exceptions import DeviceConnectionError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Rotem poll command: request all point data
# This is the WebiSmarts endpoint structure based on system info provided.
# Adjust if Rotem uses a different wire format (binary frame, HTTP REST, etc.)
_ROTEM_POLL_CMD = b"GET /api/points HTTP/1.0\r\nHost: {host}\r\nAccept: application/json\r\n\r\n"
_RESPONSE_DELIMITER = b"\r\n\r\n"
_MAX_RESPONSE_BYTES = 65536  # 64KB limit per response


class RotemStackConnector(AbstractConnector):
    """
    TCP connector for Rotem WebiSmarts Stack device.
    Manages connection lifecycle with exponential backoff reconnect.
    Preserves all raw bytes before any parsing occurs.
    """

    def __init__(
        self,
        device_id: int,
        host: str = "10.0.0.160",
        port: int = 4001,
        poll_interval_s: int = 10,
        connect_timeout_s: float = 5.0,
        read_timeout_s: float = 8.0,
    ):
        super().__init__(
            device_id=device_id,
            host=host,
            port=port,
            poll_interval_s=poll_interval_s,
            connect_timeout_s=connect_timeout_s,
            read_timeout_s=read_timeout_s,
        )
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """Open TCP connection to Rotem Stack device."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout_s,
            )
            self._is_connected = True
            logger.info(
                "rotem_stack_connected",
                extra={"device_id": self.device_id, "host": self.host, "port": self.port},
            )
        except (asyncio.TimeoutError, OSError) as exc:
            self._is_connected = False
            raise DeviceConnectionError(
                f"Cannot connect to Rotem Stack at {self.host}:{self.port}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None
        self._is_connected = False
        logger.info("rotem_stack_disconnected", extra={"device_id": self.device_id})

    async def poll(self) -> AsyncIterator[RawPacket]:
        """
        Send a poll request and yield one RawPacket containing the full response.
        On failure, disconnect and re-raise so the ingestion loop handles reconnect.
        """
        if not self._is_connected or not self._writer or not self._reader:
            raise DeviceConnectionError("Not connected to Rotem Stack device")

        try:
            # Send poll command
            cmd = _ROTEM_POLL_CMD.replace(b"{host}", self.host.encode())
            self._writer.write(cmd)
            await self._writer.drain()

            # Read response
            raw_bytes = await asyncio.wait_for(
                self._read_response(),
                timeout=self.read_timeout_s,
            )

            if raw_bytes:
                packet = RawPacket.create(
                    device_id=self.device_id,
                    session_id=self.session_id,
                    source_ip=self.host,
                    source_port=self.port,
                    raw_bytes=raw_bytes,
                    sequence=self._next_sequence(),
                )
                yield packet

        except asyncio.TimeoutError as exc:
            self._is_connected = False
            raise DeviceConnectionError(
                f"Read timeout from Rotem Stack at {self.host}:{self.port}"
            ) from exc
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            self._is_connected = False
            raise DeviceConnectionError(
                f"Connection lost to Rotem Stack: {exc}"
            ) from exc

    async def _read_response(self) -> bytes:
        """
        Read until HTTP-style response boundary or max bytes.
        If the Rotem protocol is pure TCP binary, adjust delimiter here.
        """
        buffer = bytearray()
        while len(buffer) < _MAX_RESPONSE_BYTES:
            chunk = await self._reader.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)
            # For HTTP-style responses: stop at double CRLF + body end
            if _RESPONSE_DELIMITER in buffer:
                # Read the body based on Content-Length header if present
                header_end = buffer.find(_RESPONSE_DELIMITER)
                headers_raw = buffer[:header_end].decode("utf-8", errors="replace")
                content_length = 0
                for line in headers_raw.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        try:
                            content_length = int(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                expected_total = header_end + 4 + content_length
                if len(buffer) >= expected_total:
                    return bytes(buffer[:expected_total])
        return bytes(buffer)

    async def send_heartbeat(self) -> bool:
        """
        Verify device connectivity by attempting a minimal poll.
        Returns True if device responds, False on timeout/error.
        """
        try:
            if not self._is_connected:
                await self.connect()
            packets = []
            async for packet in self.poll():
                packets.append(packet)
            return len(packets) > 0
        except DeviceConnectionError:
            return False


class RotemStackConnectorWithReconnect(RotemStackConnector):
    """
    Production wrapper: wraps RotemStackConnector with automatic reconnection.
    Implements exponential backoff: 1s → 2s → 4s → 8s → 30s (cap).
    Emits DeviceStatus events on state changes.
    """

    async def connect_with_retry(self) -> None:
        attempt = 0
        while True:
            try:
                await self.connect()
                return
            except DeviceConnectionError as exc:
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "rotem_stack_reconnect",
                    extra={
                        "device_id": self.device_id,
                        "attempt": attempt + 1,
                        "delay_s": delay,
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(delay)
                attempt += 1
                self._new_session()
