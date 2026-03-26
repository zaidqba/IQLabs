"""
IQ-RAD Abstract Connector Base
Every vendor connector implements AbstractConnector.
RawPacket is the immutable output of any connector — exact bytes received.
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Optional


@dataclass(frozen=True)
class RawPacket:
    """
    Immutable representation of exactly what was received from a device.
    raw_bytes are stored verbatim in raw_ingestion_log.
    session_id groups packets from one TCP session for reconnect tracking.
    """
    device_id: int
    session_id: str
    received_at_utc: datetime
    source_ip: str
    source_port: int
    raw_bytes: bytes
    packet_sequence: int = 0

    @property
    def payload_length(self) -> int:
        return len(self.raw_bytes)

    @classmethod
    def create(
        cls,
        device_id: int,
        session_id: str,
        source_ip: str,
        source_port: int,
        raw_bytes: bytes,
        sequence: int = 0,
    ) -> "RawPacket":
        return cls(
            device_id=device_id,
            session_id=session_id,
            received_at_utc=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=source_port,
            raw_bytes=raw_bytes,
            packet_sequence=sequence,
        )


class AbstractConnector(ABC):
    """
    Contract that all device connectors must satisfy.
    Connectors are responsible for:
    - Maintaining a TCP/UDP/HTTP connection to the device
    - Yielding RawPacket objects with exact bytes received
    - Emitting device status events on connection state changes
    - Implementing exponential backoff reconnect logic
    - Tracking heartbeat/sequence numbers
    """

    def __init__(
        self,
        device_id: int,
        host: str,
        port: int,
        poll_interval_s: int = 10,
        connect_timeout_s: float = 5.0,
        read_timeout_s: float = 8.0,
        max_reconnect_attempts: int = 0,  # 0 = unlimited
    ):
        self.device_id = device_id
        self.host = host
        self.port = port
        self.poll_interval_s = poll_interval_s
        self.connect_timeout_s = connect_timeout_s
        self.read_timeout_s = read_timeout_s
        self.max_reconnect_attempts = max_reconnect_attempts
        self._session_id: str = str(uuid.uuid4())
        self._packet_sequence: int = 0
        self._is_connected: bool = False
        self._running: bool = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def session_id(self) -> str:
        return self._session_id

    def _new_session(self) -> str:
        """Generate new session ID on reconnect."""
        self._session_id = str(uuid.uuid4())
        self._packet_sequence = 0
        return self._session_id

    def _next_sequence(self) -> int:
        self._packet_sequence += 1
        return self._packet_sequence

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to device. Raise DeviceConnectionError on failure."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly close connection."""
        ...

    @abstractmethod
    async def poll(self) -> AsyncIterator[RawPacket]:
        """
        Poll device for current data.
        Yields one or more RawPacket per call.
        Must handle partial reads, timeout, and protocol framing.
        """
        ...

    @abstractmethod
    async def send_heartbeat(self) -> bool:
        """
        Send a heartbeat/ping to verify device is alive.
        Returns True if device responded within read_timeout_s.
        """
        ...

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff: 1s → 2s → 4s → 8s → 30s (capped)."""
        return min(2 ** attempt, 30)
