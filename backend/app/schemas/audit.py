"""Audit Trail request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditTrailResponse(BaseModel):
    audit_id: int
    event_at_utc: datetime
    user_id: Optional[int]
    user_name: Optional[str]
    user_role: Optional[str]
    ip_address: Optional[str]
    http_method: Optional[str]
    endpoint: Optional[str]
    action_type: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    action_detail: Optional[str]
    result_code: Optional[int]
    result_status: Optional[str]
    duration_ms: Optional[int]
    request_id: str

    class Config:
        from_attributes = True


class AuditTrailListResponse(BaseModel):
    records: list[AuditTrailResponse]
    total: int
    page: int
    page_size: int
