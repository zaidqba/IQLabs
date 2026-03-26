"""Report request/response schemas."""
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(DAILY|WEEKLY|MONTHLY|INCIDENT|CALIBRATION)$")
    period_start: date
    period_end: date
    site_id: int
    channel_ids: Optional[list[int]] = None  # None = all channels
    title: Optional[str] = None


class ReportResponse(BaseModel):
    report_id: int
    report_type: str
    report_title: str
    period_start: date
    period_end: date
    report_state: str
    generated_at_utc: datetime
    generated_by_username: str
    approved_by_username: Optional[str] = None
    approved_at_utc: Optional[datetime] = None
    file_hash_sha256: Optional[str] = None

    class Config:
        from_attributes = True


class ApproveReportRequest(BaseModel):
    signature_password: str
    meaning: str = "I approve this report as accurate and complete."
    comment: Optional[str] = None
