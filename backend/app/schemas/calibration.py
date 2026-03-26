"""Calibration record request/response schemas."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CalibrationResponse(BaseModel):
    cal_id: int
    detector_id: int
    detector_code: str
    calibration_date: date
    next_due_date: date
    calibration_source: Optional[str]
    correction_factor: Decimal
    pass_fail: str
    performed_by_name: str
    certificate_ref: Optional[str]
    notes: Optional[str]
    reviewed_by_username: Optional[str] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True


class CreateCalibrationRequest(BaseModel):
    detector_id: int
    calibration_date: date
    next_due_date: date
    calibration_source: Optional[str] = None
    source_activity_bq: Optional[Decimal] = None
    source_cert_number: Optional[str] = None
    as_found_reading: Optional[Decimal] = None
    as_left_reading: Optional[Decimal] = None
    correction_factor: Decimal = Field(default=Decimal("1.0"))
    pass_fail: str = Field(..., pattern="^(PASS|FAIL|CONDITIONAL)$")
    performed_by_name: str
    certificate_ref: Optional[str] = None
    notes: Optional[str] = None


class ReviewCalibrationRequest(BaseModel):
    pass_fail: str = Field(..., pattern="^(PASS|FAIL|CONDITIONAL)$")
    notes: Optional[str] = None
    signature_password: str
    meaning: str = "I have reviewed this calibration record and confirm its accuracy."
