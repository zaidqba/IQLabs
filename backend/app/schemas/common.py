"""
IQ-RAD Common/Canonical Schemas
NormalizedEvent is the internal API contract between connectors,
normalization, rules engine, persistence, and WebSocket broadcast.
All four layers must agree on this schema — it is the critical interface.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class QualityFlag(str, Enum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    BAD = "BAD"
    SIMULATED = "SIMULATED"
    CORRECTED = "CORRECTED"


class SeverityLevel(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    ALERT = "ALERT"
    ALARM = "ALARM"
    DANGER = "DANGER"
    HIGH_DOSE = "HIGH_DOSE"


class AlarmType(str, Enum):
    LOW = "LOW"
    ALERT = "ALERT"
    ALARM = "ALARM"
    DANGER = "DANGER"
    HIGH_DOSE = "HIGH_DOSE"
    SYSTEM = "SYSTEM"
    STALE = "STALE"
    COMM_FAIL = "COMM_FAIL"


class AlarmState(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SUPPRESSED = "SUPPRESSED"
    CLEARED = "CLEARED"


class DeviceStatusCode(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    RECONNECTING = "RECONNECTING"


class ChannelStatusCode(str, Enum):
    OK = "OK"
    NO_DATA = "NO_DATA"
    STALE = "STALE"
    SATURATED = "SATURATED"
    FAULT = "FAULT"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"
    EMISSIONS = "EMISSIONS"
    DEVELOPER = "DEVELOPER"


class NormalizedEvent(BaseModel):
    """
    Canonical event model — the contract between all system layers.
    Every connector produces this; every downstream consumer reads this.
    Vendor field names are never exposed beyond the normalization layer.
    """
    # Provenance (required for 21 CFR Part 11 traceability)
    ingestion_id: int
    device_id: int
    channel_id: int
    channel_code: str                               # e.g. 'STACK.PM11'
    rotem_point_id: Optional[int] = None            # 1-9 from Rotem system

    # Timing (always UTC, NTP-validated)
    measured_at_utc: datetime
    received_at_utc: datetime

    # Measurement
    raw_value: Decimal
    normalized_value: Decimal
    uom_code: str                                   # 'CPS', 'MR_PER_HR', 'M3_PER_S'
    uom_id: int

    # Quality
    quality_flag: QualityFlag = QualityFlag.GOOD
    quality_detail: Optional[str] = None
    ntp_offset_ms: Optional[int] = None

    # Threshold context (active alarm_profile at time of reading)
    alarm_profile_id: Optional[int] = None
    low_threshold: Optional[Decimal] = None
    alert_threshold: Optional[Decimal] = None
    alarm_threshold: Optional[Decimal] = None
    danger_threshold: Optional[Decimal] = None
    high_dose_threshold: Optional[Decimal] = None

    # Rules engine output (populated after evaluate())
    severity_level: SeverityLevel = SeverityLevel.NORMAL
    threshold_exceeded: Optional[str] = None        # Which threshold name was crossed

    # WebSocket broadcast envelope
    event_type: str = "READING"
    sequence_num: Optional[int] = None

    class Config:
        json_encoders = {Decimal: str}


class WSMessage(BaseModel):
    """WebSocket broadcast message envelope."""
    type: str           # 'reading', 'alarm', 'device_status', 'heartbeat', 'system'
    payload: dict
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    sequence: Optional[int] = None
