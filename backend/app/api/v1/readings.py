"""Readings API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.master import Channel, UnitOfMeasure
from app.models.runtime import NormalizedReading
from app.schemas.readings import (
    LatestReadingResponse,
    ReadingListResponse,
    ReadingResponse,
)
from app.schemas.common import QualityFlag, SeverityLevel

router = APIRouter(prefix="/readings", tags=["Readings"])


@router.get("", response_model=ReadingListResponse)
async def list_readings(
    user: CurrentUser,
    channel_id: Optional[int] = Query(None),
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    quality_flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(NormalizedReading, Channel, UnitOfMeasure)
        .join(Channel, NormalizedReading.channel_id == Channel.channel_id)
        .join(UnitOfMeasure, NormalizedReading.uom_id == UnitOfMeasure.uom_id)
    )

    if channel_id is not None:
        query = query.where(NormalizedReading.channel_id == channel_id)
    if from_dt is not None:
        query = query.where(NormalizedReading.measured_at_utc >= from_dt)
    if to_dt is not None:
        query = query.where(NormalizedReading.measured_at_utc <= to_dt)
    if quality_flag:
        query = query.where(NormalizedReading.quality_flag == quality_flag)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    query = query.order_by(NormalizedReading.measured_at_utc.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    readings = [
        ReadingResponse(
            reading_id=r.reading_id,
            ingestion_id=r.ingestion_id,
            channel_id=r.channel_id,
            channel_code=ch.channel_code,
            channel_name=ch.channel_name,
            measured_at_utc=r.measured_at_utc,
            received_at_utc=r.received_at_utc,
            normalized_value=r.normalized_value,
            uom_symbol=uom.uom_symbol,
            quality_flag=r.quality_flag,
            severity_level=r.severity_level,
            ntp_offset_ms=r.ntp_offset_ms,
        )
        for r, ch, uom in rows
    ]

    return ReadingListResponse(readings=readings, total=total, page=page, page_size=page_size)


@router.get("/latest", response_model=list[LatestReadingResponse])
async def get_latest_readings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent reading for every active channel. Used by live dashboard."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            c.channel_id, c.channel_code, c.channel_name,
            nr.normalized_value, u.uom_symbol,
            nr.severity_level, nr.quality_flag, nr.measured_at_utc,
            ap.alert_threshold, ap.alarm_threshold, ap.danger_threshold,
            ap.profile_id
        FROM channels c
        JOIN units_of_measure u ON c.uom_id = u.uom_id
        LEFT JOIN alarm_profiles ap ON ap.channel_id = c.channel_id AND ap.is_current = 1
        OUTER APPLY (
            SELECT TOP 1 normalized_value, severity_level, quality_flag, measured_at_utc
            FROM normalized_readings
            WHERE channel_id = c.channel_id
            ORDER BY measured_at_utc DESC
        ) nr
        WHERE c.is_active = 1
    """))
    rows = result.fetchall()
    from datetime import timezone
    now = datetime.now(timezone.utc)

    return [
        LatestReadingResponse(
            channel_id=row[0],
            channel_code=row[1],
            channel_name=row[2],
            normalized_value=row[3],
            uom_symbol=row[4],
            severity_level=row[5] or SeverityLevel.NORMAL,
            quality_flag=row[6] or QualityFlag.GOOD,
            measured_at_utc=row[7],
            is_stale=(
                (now - row[7]).total_seconds() > 60
                if row[7] else True
            ),
            alarm_profile_id=row[11],
            alert_threshold=row[8],
            alarm_threshold=row[9],
            danger_threshold=row[10],
        )
        for row in rows
    ]
