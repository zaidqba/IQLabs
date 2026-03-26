"""
Unit tests for ThresholdEvaluator.
45 parametrized tests: 5 severity levels × 9 channels.
All tests are pure; no DB or network calls.

Requirement: IQ-RAD-REQ-007 (Threshold Evaluation)
10 CFR Part 20 — radiation protection thresholds must evaluate correctly.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.rules_engine.threshold_evaluator import ThresholdEvaluator
from app.schemas.common import NormalizedEvent, QualityFlag, SeverityLevel


def _make_event(
    channel_code: str,
    value: float,
    low: float | None = None,
    alert: float = 100.0,
    alarm: float = 500.0,
    danger: float = 1000.0,
    high_dose: float | None = 5000.0,
    quality: QualityFlag = QualityFlag.GOOD,
) -> NormalizedEvent:
    return NormalizedEvent(
        ingestion_id=None,
        device_id=1,
        channel_id=1,
        channel_code=channel_code,
        rotem_point_id=2,
        measured_at_utc=datetime.now(timezone.utc),
        received_at_utc=datetime.now(timezone.utc),
        raw_value=Decimal(str(value)),
        normalized_value=Decimal(str(value)),
        uom_code="CPS",
        uom_id=1,
        quality_flag=quality,
        ntp_offset_ms=None,
        alarm_profile_id=1,
        low_threshold=Decimal(str(low)) if low is not None else None,
        alert_threshold=Decimal(str(alert)),
        alarm_threshold=Decimal(str(alarm)),
        danger_threshold=Decimal(str(danger)),
        high_dose_threshold=Decimal(str(high_dose)) if high_dose is not None else None,
        severity_level=SeverityLevel.NORMAL,
        threshold_exceeded=None,
        event_type="READING",
    )


CHANNEL_CODES = [
    "STACK.PM11",
    "STACK.GM42",
    "STACK.AIR",
    "STACK.W1",
    "STACK.W2",
    "STACK.W3",
    "STACK.W4",
    "STACK.W5",
    "TEST.CHANNEL",
]

evaluator = ThresholdEvaluator()


@pytest.mark.parametrize("channel_code", CHANNEL_CODES)
def test_normal_below_all_thresholds(channel_code: str):
    """Value below all thresholds → NORMAL."""
    event = _make_event(channel_code, value=50.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.NORMAL
    assert crossed is None


@pytest.mark.parametrize("channel_code", CHANNEL_CODES)
def test_alert_threshold(channel_code: str):
    """Value at or above alert (100) but below alarm (500) → ALERT."""
    event = _make_event(channel_code, value=200.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.ALERT
    assert crossed == "alert_threshold"


@pytest.mark.parametrize("channel_code", CHANNEL_CODES)
def test_alarm_threshold(channel_code: str):
    """Value at or above alarm (500) but below danger (1000) → ALARM."""
    event = _make_event(channel_code, value=750.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.ALARM
    assert crossed == "alarm_threshold"


@pytest.mark.parametrize("channel_code", CHANNEL_CODES)
def test_danger_threshold(channel_code: str):
    """Value at or above danger (1000) but below high_dose (5000) → DANGER."""
    event = _make_event(channel_code, value=2000.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.DANGER
    assert crossed == "danger_threshold"


@pytest.mark.parametrize("channel_code", CHANNEL_CODES)
def test_high_dose_threshold(channel_code: str):
    """Value at or above high_dose (5000) → HIGH_DOSE."""
    event = _make_event(channel_code, value=6000.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.HIGH_DOSE
    assert crossed == "high_dose_threshold"


# Additional edge-case tests

def test_bad_quality_forces_alarm():
    """BAD quality flag forces ALARM regardless of value."""
    event = _make_event("STACK.PM11", value=10.0, quality=QualityFlag.BAD)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.ALARM
    assert crossed == "DATA_QUALITY"


def test_suspect_quality_normal_value():
    """SUSPECT quality with normal value → evaluates normally."""
    event = _make_event("STACK.PM11", value=50.0, quality=QualityFlag.SUSPECT)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.NORMAL


def test_low_threshold():
    """Value at or below low threshold → LOW."""
    event = _make_event("STACK.PM11", value=5.0, low=10.0)
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.LOW
    assert crossed == "low_threshold"


def test_no_alarm_profile():
    """No alarm thresholds configured → NORMAL."""
    event = NormalizedEvent(
        ingestion_id=None,
        device_id=1,
        channel_id=1,
        channel_code="STACK.PM11",
        rotem_point_id=2,
        measured_at_utc=datetime.now(timezone.utc),
        received_at_utc=datetime.now(timezone.utc),
        raw_value=Decimal("9999"),
        normalized_value=Decimal("9999"),
        uom_code="CPS",
        uom_id=1,
        quality_flag=QualityFlag.GOOD,
        ntp_offset_ms=None,
        alarm_profile_id=None,
        low_threshold=None,
        alert_threshold=None,
        alarm_threshold=None,
        danger_threshold=None,
        high_dose_threshold=None,
        severity_level=SeverityLevel.NORMAL,
        threshold_exceeded=None,
        event_type="READING",
    )
    severity, crossed = evaluator.evaluate(event)
    assert severity == SeverityLevel.NORMAL


def test_exact_boundary_alert():
    """Value exactly at alert threshold → ALERT."""
    event = _make_event("STACK.GM42", value=100.0)
    severity, _ = evaluator.evaluate(event)
    assert severity == SeverityLevel.ALERT


def test_exact_boundary_alarm():
    """Value exactly at alarm threshold → ALARM."""
    event = _make_event("STACK.GM42", value=500.0)
    severity, _ = evaluator.evaluate(event)
    assert severity == SeverityLevel.ALARM


def test_requires_signature_danger():
    assert evaluator.requires_signature(SeverityLevel.DANGER) is True


def test_requires_signature_high_dose():
    assert evaluator.requires_signature(SeverityLevel.HIGH_DOSE) is True


def test_no_signature_required_alarm():
    assert evaluator.requires_signature(SeverityLevel.ALARM) is False


def test_no_signature_required_alert():
    assert evaluator.requires_signature(SeverityLevel.ALERT) is False


def test_escalation_minutes():
    assert evaluator.escalation_minutes(SeverityLevel.ALERT) == 15
    assert evaluator.escalation_minutes(SeverityLevel.ALARM) == 5
    assert evaluator.escalation_minutes(SeverityLevel.DANGER) == 2
    assert evaluator.escalation_minutes(SeverityLevel.HIGH_DOSE) == 1
    assert evaluator.escalation_minutes(SeverityLevel.NORMAL) is None
