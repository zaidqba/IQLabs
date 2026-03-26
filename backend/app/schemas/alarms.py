"""Alarm request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import AlarmState, AlarmType, SeverityLevel


class AlarmResponse(BaseModel):
    alarm_id: int
    channel_id: int
    channel_code: str
    channel_name: str
    alarm_type: AlarmType
    severity_level: SeverityLevel
    triggered_at_utc: datetime
    trigger_value: Optional[Decimal]
    alarm_state: AlarmState
    alarm_message: Optional[str]
    requires_signature: bool
    acknowledged_at_utc: Optional[datetime]
    acknowledged_by_username: Optional[str]
    ack_comment: Optional[str]

    class Config:
        from_attributes = True


class AcknowledgeAlarmRequest(BaseModel):
    comment: str = Field(..., min_length=10, max_length=1000)
    signature_password: str = Field(
        ...,
        description="Re-authentication password per 21 CFR Part 11 §11.200(a)(1)",
    )
    meaning: str = Field(
        default="I acknowledge this alarm and confirm I have reviewed the associated data.",
        description="Electronic signature meaning statement per 21 CFR Part 11 §11.50",
    )


class AlarmStatsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_alarms: int
    by_severity: dict[str, int]
    by_channel: dict[str, int]
    unacknowledged_count: int
    mean_time_to_acknowledge_min: Optional[float]
