"""Device and Channel request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ChannelStatusCode, DeviceStatusCode


class DeviceResponse(BaseModel):
    device_id: int
    device_code: str
    device_name: str
    device_type: str
    ip_address: Optional[str]
    port: Optional[int]
    protocol: str
    poll_interval_s: int
    is_active: bool
    vendor_code: str
    current_status: Optional[DeviceStatusCode] = None
    last_heartbeat_utc: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChannelResponse(BaseModel):
    channel_id: int
    channel_code: str
    channel_name: str
    rotem_point_id: Optional[int]
    device_code: str
    detector_code: Optional[str]
    uom_symbol: str
    uom_code: str
    expected_update_s: int
    stale_threshold_s: int
    is_active: bool
    current_status: Optional[ChannelStatusCode] = None
    current_profile: Optional["AlarmProfileResponse"] = None


class AlarmProfileResponse(BaseModel):
    profile_id: int
    channel_id: int
    profile_version: int
    low_threshold: Optional[Decimal]
    alert_threshold: Decimal
    alarm_threshold: Decimal
    danger_threshold: Decimal
    high_dose_threshold: Optional[Decimal]
    is_current: bool
    effective_from: datetime
    effective_to: Optional[datetime]
    change_reason: str


class UpdateThresholdRequest(BaseModel):
    alert_threshold: Decimal
    alarm_threshold: Decimal
    danger_threshold: Decimal
    low_threshold: Optional[Decimal] = None
    high_dose_threshold: Optional[Decimal] = None
    change_reason: str
    risk_assessment: Optional[str] = None
    signature_password: str
    meaning: str = "I approve this threshold change and confirm it has been properly risk-assessed."
