"""Audit Trail API — read-only, immutable records."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.compliance import AuditTrail
from app.schemas.audit import AuditTrailListResponse, AuditTrailResponse

router = APIRouter(prefix="/audit-trail", tags=["Audit Trail"])


@router.get("", response_model=AuditTrailListResponse)
async def query_audit_trail(
    user: CurrentUser,
    _: None = require_permission("read:audit"),
    user_id: Optional[int] = Query(None),
    action_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditTrail)

    if user_id:
        query = query.where(AuditTrail.user_id == user_id)
    if action_type:
        query = query.where(AuditTrail.action_type == action_type)
    if resource_type:
        query = query.where(AuditTrail.resource_type == resource_type)
    if from_dt:
        query = query.where(AuditTrail.event_at_utc >= from_dt)
    if to_dt:
        query = query.where(AuditTrail.event_at_utc <= to_dt)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    query = query.order_by(AuditTrail.event_at_utc.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return AuditTrailListResponse(
        records=[AuditTrailResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )
