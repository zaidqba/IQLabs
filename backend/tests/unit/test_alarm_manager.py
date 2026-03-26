"""
Unit tests for AlarmManager state machine.
Uses mock DB sessions — no real database required.

Requirement: IQ-RAD-REQ-008 (Alarm State Machine)
10 CFR Part 20 — alarm transitions must be auditable and immutable.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.rules_engine.alarm_manager import AlarmManager
from app.schemas.common import NormalizedEvent, QualityFlag, SeverityLevel


def _make_event(
    channel_id: int = 1,
    channel_code: str = "STACK.PM11",
    severity: SeverityLevel = SeverityLevel.ALARM,
    value: float = 750.0,
) -> NormalizedEvent:
    return NormalizedEvent(
        ingestion_id=100,
        device_id=1,
        channel_id=channel_id,
        channel_code=channel_code,
        rotem_point_id=2,
        measured_at_utc=datetime.now(timezone.utc),
        received_at_utc=datetime.now(timezone.utc),
        raw_value=Decimal(str(value)),
        normalized_value=Decimal(str(value)),
        uom_code="CPS",
        uom_id=1,
        quality_flag=QualityFlag.GOOD,
        ntp_offset_ms=0.0,
        alarm_profile_id=1,
        low_threshold=None,
        alert_threshold=Decimal("100"),
        alarm_threshold=Decimal("500"),
        danger_threshold=Decimal("1000"),
        high_dose_threshold=Decimal("5000"),
        severity_level=severity,
        threshold_exceeded="alarm_threshold",
        event_type="READING",
    )


@pytest.fixture
def manager():
    return AlarmManager()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_creates_new_alarm_when_threshold_exceeded(manager, mock_db):
    """New ALARM severity with no existing alarm → creates ActiveAlarm + AlarmHistory row."""
    # No existing alarm
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    event = _make_event(severity=SeverityLevel.ALARM)
    alarm = await manager.handle_event(mock_db, event)

    assert alarm is not None
    assert mock_db.add.call_count == 2  # ActiveAlarm + AlarmHistory


@pytest.mark.asyncio
async def test_normal_reading_no_alarm(manager, mock_db):
    """NORMAL severity → no alarm created."""
    event = _make_event(severity=SeverityLevel.NORMAL, value=50.0)
    event = event.model_copy(update={"severity_level": SeverityLevel.NORMAL, "threshold_exceeded": None})

    alarm = await manager.handle_event(mock_db, event)
    assert alarm is None
    assert mock_db.add.call_count == 0


@pytest.mark.asyncio
async def test_escalates_existing_alarm(manager, mock_db):
    """Existing ALERT alarm escalated to ALARM when higher severity reading arrives."""
    from app.models.runtime import ActiveAlarm

    existing = MagicMock(spec=ActiveAlarm)
    existing.alarm_id = 1
    existing.severity_level = "ALERT"
    existing.alarm_state = "ACTIVE"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = mock_result

    event = _make_event(severity=SeverityLevel.ALARM)
    await manager.handle_event(mock_db, event)

    # AlarmHistory row added for escalation
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_clears_alarm_on_normal(manager, mock_db):
    """When reading is NORMAL and existing ACKNOWLEDGED alarm exists → clear it."""
    from app.models.runtime import ActiveAlarm

    existing = MagicMock(spec=ActiveAlarm)
    existing.alarm_id = 1
    existing.severity_level = "ALARM"
    existing.alarm_state = "ACKNOWLEDGED"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = mock_result

    event = _make_event(severity=SeverityLevel.NORMAL, value=50.0)
    event = event.model_copy(update={"severity_level": SeverityLevel.NORMAL, "threshold_exceeded": None})
    await manager.handle_event(mock_db, event)

    # AlarmHistory transition row added
    assert existing.alarm_state == "CLEARED"
