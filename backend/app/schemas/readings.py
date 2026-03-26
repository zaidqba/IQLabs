"""Readings request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import QualityFlag, SeverityLevel


class ReadingResponse(BaseModel):
    reading_id: int
    ingestion_id: int
    channel_id: int
    channel_code: str
    channel_name: str
    measured_at_utc: datetime
    received_at_utc: datetime
    normalized_value: Decimal
    uom_symbol: str
    quality_flag: QualityFlag
    severity_level: SeverityLevel
    ntp_offset_ms: Optional[int] = None

    class Config:
        from_attributes = True


class ReadingListResponse(BaseModel):
    readings: list[ReadingResponse]
    total: int
    page: int
    page_size: int
    data_completeness_pct: Optional[float] = None


class LatestReadingResponse(BaseModel):
    channel_id: int
    channel_code: str
    channel_name: str
    normalized_value: Optional[Decimal] = None
    uom_symbol: str
    severity_level: SeverityLevel
    quality_flag: QualityFlag
    measured_at_utc: Optional[datetime] = None
    is_stale: bool = False
    alarm_profile_id: Optional[int] = None
    alert_threshold: Optional[Decimal] = None
    alarm_threshold: Optional[Decimal] = None
    danger_threshold: Optional[Decimal] = None
