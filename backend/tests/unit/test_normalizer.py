"""
Unit tests for RotemNormalizer.
Tests JSON parsing, quality flag mapping, NTP flagging, and PointID lookup.
No DB or network calls.

Requirement: IQ-RAD-REQ-004 (Normalization)
"""
import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from app.connectors.base import RawPacket
from app.normalization.normalizer import RotemNormalizer
from app.schemas.common import QualityFlag, SeverityLevel


def _make_raw_json(points: list[dict]) -> bytes:
    """Wrap points as HTTP-over-TCP response."""
    body = json.dumps(points).encode()
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"\r\n" + body
    )


def _make_packet(points: list[dict], device_id: int = 1) -> RawPacket:
    return RawPacket(
        device_id=device_id,
        session_id="test-session-001",
        received_at_utc=datetime.now(timezone.utc),
        source_ip="10.0.0.160",
        source_port=4001,
        raw_bytes=_make_raw_json(points),
        packet_sequence=1,
    )


# Channel map: channel_id, uom_id, alarm thresholds
CHANNEL_MAP = {
    "STACK.PM11": {
        "channel_id": 1, "uom_id": 1, "uom_code": "CPS",
        "alarm_profile_id": 1,
        "low_threshold": None, "alert_threshold": Decimal("100"),
        "alarm_threshold": Decimal("500"), "danger_threshold": Decimal("1000"),
        "high_dose_threshold": Decimal("5000"),
    },
    "STACK.GM42": {
        "channel_id": 2, "uom_id": 2, "uom_code": "MR_PER_HR",
        "alarm_profile_id": 1,
        "low_threshold": None, "alert_threshold": Decimal("2"),
        "alarm_threshold": Decimal("5"), "danger_threshold": Decimal("25"),
        "high_dose_threshold": Decimal("100"),
    },
}


@pytest.fixture
def normalizer():
    return RotemNormalizer(channel_map=CHANNEL_MAP)


def test_parse_single_good_point(normalizer):
    """Parse a single PointID 2 (PM11) with quality 0 (GOOD)."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=True), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=10.0):
        events = normalizer.parse(_make_packet([
            {"PointID": 2, "Name": "StackPM11", "Rate": 123.45, "Dose": 0.0,
             "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
        ]))

    assert len(events) == 1
    e = events[0]
    assert e.channel_code == "STACK.PM11"
    assert e.normalized_value == Decimal("123.45")
    assert e.quality_flag == QualityFlag.GOOD
    assert e.rotem_point_id == 2
    assert e.ntp_offset_ms == 10.0


def test_parse_multiple_points(normalizer):
    """Parse PM11 and GM42 together."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=True), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=5.0):
        events = normalizer.parse(_make_packet([
            {"PointID": 2, "Name": "StackPM11", "Rate": 200.0, "Dose": 0.0,
             "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
            {"PointID": 3, "Name": "StackGM42", "Rate": 3.5, "Dose": 0.0,
             "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
        ]))

    codes = {e.channel_code for e in events}
    assert "STACK.PM11" in codes
    assert "STACK.GM42" in codes


def test_ntp_invalid_marks_suspect(normalizer):
    """When NTP is invalid, quality_flag becomes SUSPECT."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=False), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=600.0):
        events = normalizer.parse(_make_packet([
            {"PointID": 2, "Name": "StackPM11", "Rate": 50.0, "Dose": 0.0,
             "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
        ]))

    assert events[0].quality_flag == QualityFlag.SUSPECT


def test_rotem_quality_1_marks_bad(normalizer):
    """Rotem Quality code 1 → BAD."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=True), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=0.0):
        events = normalizer.parse(_make_packet([
            {"PointID": 2, "Name": "StackPM11", "Rate": 50.0, "Dose": 0.0,
             "AlarmState": 0, "Quality": 1, "Timestamp": "2025-03-12T10:36:28.999"},
        ]))

    assert events[0].quality_flag == QualityFlag.BAD


def test_unknown_point_id_skipped(normalizer):
    """PointID not in point_map → skipped, no event emitted."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=True), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=0.0):
        events = normalizer.parse(_make_packet([
            {"PointID": 99, "Name": "Unknown", "Rate": 50.0, "Dose": 0.0,
             "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
        ]))

    assert len(events) == 0


def test_invalid_json_returns_empty(normalizer):
    """Malformed JSON → empty list, no exception raised."""
    bad_packet = RawPacket(
        device_id=1,
        session_id="test",
        received_at_utc=datetime.now(timezone.utc),
        source_ip="10.0.0.160",
        source_port=4001,
        raw_bytes=b"NOT VALID JSON AT ALL",
        packet_sequence=1,
    )
    events = normalizer.parse(bad_packet)
    assert events == []


def test_empty_point_list(normalizer):
    """Empty points array → empty events."""
    with patch("app.normalization.normalizer.is_ntp_valid", return_value=True), \
         patch("app.normalization.normalizer.get_ntp_offset_ms", return_value=0.0):
        events = normalizer.parse(_make_packet([]))
    assert events == []
