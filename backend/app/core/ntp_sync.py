"""
IQ-RAD NTP Synchronization Validation
Monitors system clock drift against NTP reference.
Readings are flagged SUSPECT if abs(drift) > MAX_NTP_DRIFT_MS.
This satisfies the GMP requirement for controlled, traceable time across
all devices, servers, and application logs.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

import ntplib

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_latest_offset_ms: Optional[int] = None
_ntp_valid: bool = True


def get_ntp_offset_ms() -> Optional[int]:
    """Return the most recently measured NTP offset in milliseconds."""
    return _latest_offset_ms


def is_ntp_valid() -> bool:
    """True if the last NTP check was within the allowed drift threshold."""
    return _ntp_valid


def check_ntp_sync() -> tuple[Optional[int], bool]:
    """
    Synchronously check NTP offset.
    Returns (offset_ms, is_valid).
    offset_ms is positive if local clock is ahead of NTP.
    """
    global _latest_offset_ms, _ntp_valid
    try:
        client = ntplib.NTPClient()
        response = client.request(settings.ntp_server, version=3, timeout=5)
        offset_ms = int(response.offset * 1000)
        is_valid = abs(offset_ms) <= settings.max_ntp_drift_ms
        _latest_offset_ms = offset_ms
        _ntp_valid = is_valid
        if not is_valid:
            logger.warning(
                "ntp_drift_exceeded",
                extra={
                    "ntp_offset_ms": offset_ms,
                    "max_allowed_ms": settings.max_ntp_drift_ms,
                },
            )
        return offset_ms, is_valid
    except Exception as exc:
        logger.error("ntp_check_failed", extra={"error": str(exc)})
        _ntp_valid = False
        return None, False


async def ntp_monitor_loop(interval_s: int = 60) -> None:
    """
    Background task: periodically check NTP drift.
    Run as asyncio.create_task() from ingestion_service startup.
    """
    while True:
        await asyncio.get_event_loop().run_in_executor(None, check_ntp_sync)
        await asyncio.sleep(interval_s)


def get_trusted_utc_now() -> datetime:
    """
    Return current UTC time from system clock.
    Caller should check is_ntp_valid() to determine if timestamps are reliable.
    """
    return datetime.now(timezone.utc)
