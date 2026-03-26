"""
IQ-RAD Rotem DPU3 Connector
Connects to the Rotem DPU3 unit at 10.0.0.160:5000.
Primarily handles beta detector channels W1-W5 (AdapterIDs 11-15).

Structurally identical to RotemStackConnector — same protocol family,
different port and channel set.
"""
import asyncio
from typing import AsyncIterator, Optional

from app.connectors.base import AbstractConnector, RawPacket
from app.core.exceptions import DeviceConnectionError
from app.core.logging import get_logger

logger = get_logger(__name__)

_ROTEM_DPU3_POLL_CMD = b"GET /api/points HTTP/1.0\r\nHost: {host}\r\nAccept: application/json\r\n\r\n"
_RESPONSE_DELIMITER = b"\r\n\r\n"
_MAX_RESPONSE_BYTES = 65536


class RotemDPU3Connector(AbstractConnector):
    """
    TCP connector for Rotem DPU3 unit.
    Same protocol as RotemStackConnector but on port 5000.
    Maps to channels STACK.W1 through STACK.W5.
    """

    def __init__(
        self,
        device_id: int,
        host: str = "10.0.0.160",
        port: int = 5000,
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
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout_s,
            )
            self._is_connected = True
            logger.info(
                "rotem_dpu3_connected",
                extra={"device_id": self.device_id, "host": self.host, "port": self.port},
            )
        except (asyncio.TimeoutError, OSError) as exc:
            self._is_connected = False
            raise DeviceConnectionError(
                f"Cannot connect to Rotem DPU3 at {self.host}:{self.port}: {exc}"
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

    async def poll(self) -> AsyncIterator[RawPacket]:
        if not self._is_connected or not self._writer or not self._reader:
            raise DeviceConnectionError("Not connected to Rotem DPU3 device")

        try:
            cmd = _ROTEM_DPU3_POLL_CMD.replace(b"{host}", self.host.encode())
            self._writer.write(cmd)
            await self._writer.drain()

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
                f"Read timeout from Rotem DPU3 at {self.host}:{self.port}"
            ) from exc
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            self._is_connected = False
            raise DeviceConnectionError(f"Connection lost to Rotem DPU3: {exc}") from exc

    async def _read_response(self) -> bytes:
        buffer = bytearray()
        while len(buffer) < _MAX_RESPONSE_BYTES:
            chunk = await self._reader.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)
            if _RESPONSE_DELIMITER in buffer:
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
        try:
            if not self._is_connected:
                await self.connect()
            packets = []
            async for packet in self.poll():
                packets.append(packet)
            return len(packets) > 0
        except DeviceConnectionError:
            return False


class RotemDPU3ConnectorWithReconnect(RotemDPU3Connector):
    async def connect_with_retry(self) -> None:
        attempt = 0
        while True:
            try:
                await self.connect()
                return
            except DeviceConnectionError as exc:
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "rotem_dpu3_reconnect",
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
