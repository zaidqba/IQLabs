"""
IQ-RAD Rotem Connection Unit Connector
Monitors the Rotem WebiSmarts Connection Unit at localhost:15386.
The Connection Unit is a local service that manages the Rotem SQL backend
(MEDIDATA database) and device connections.

This connector is used for:
- Device health polling (is the Connection Unit alive?)
- Supplementary system metadata
- NOT used as primary data acquisition path
"""
import asyncio
from typing import Optional

import httpx

from app.core.exceptions import DeviceConnectionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionUnitMonitor:
    """
    HTTP health monitor for the Rotem Connection Unit (localhost:15386).
    Polls the Connection Unit status endpoint to determine if the
    WebiSmarts backend is operational.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 15386,
        timeout_s: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self._base_url = f"http://{host}:{port}"
        self._is_alive: bool = False
        self._last_check_utc: Optional[float] = None

    @property
    def is_alive(self) -> bool:
        return self._is_alive

    async def check_health(self) -> tuple[bool, Optional[str]]:
        """
        Check if the Connection Unit is alive.
        Returns (is_alive, status_detail).
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(f"{self._base_url}/health")
                self._is_alive = response.status_code == 200
                return self._is_alive, response.text[:500] if self._is_alive else f"HTTP {response.status_code}"
        except httpx.ConnectError:
            self._is_alive = False
            return False, "Connection refused"
        except httpx.TimeoutException:
            self._is_alive = False
            return False, "Timeout"
        except Exception as exc:
            self._is_alive = False
            return False, str(exc)[:200]

    async def monitor_loop(self, interval_s: int = 60) -> None:
        """Background task: periodically check Connection Unit health."""
        while True:
            is_alive, detail = await self.check_health()
            if not is_alive:
                logger.warning(
                    "connection_unit_unreachable",
                    extra={"host": self.host, "port": self.port, "detail": detail},
                )
            await asyncio.sleep(interval_s)
