"""
Reading Service — query normalized readings from the historian.
All queries are read-only; normalized_readings is immutable.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime import NormalizedReading


class ReadingService:
    async def get_channel_readings(
        self,
        db: AsyncSession,
        channel_id: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
        quality_filter: Optional[str] = None,
    ) -> list[NormalizedReading]:
        conditions = [NormalizedReading.channel_id == channel_id]
        if start:
            conditions.append(NormalizedReading.measured_at_utc >= start)
        if end:
            conditions.append(NormalizedReading.measured_at_utc <= end)
        if quality_filter:
            conditions.append(NormalizedReading.quality_flag == quality_filter)

        stmt = (
            select(NormalizedReading)
            .where(and_(*conditions))
            .order_by(NormalizedReading.measured_at_utc.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        # Return in ascending order for charting
        return list(reversed(rows))

    async def get_latest_readings(
        self,
        db: AsyncSession,
        channel_ids: Optional[list[int]] = None,
    ) -> list[NormalizedReading]:
        """Get the most recent reading per channel using a subquery."""
        from sqlalchemy import func

        subq = (
            select(
                NormalizedReading.channel_id,
                func.max(NormalizedReading.measured_at_utc).label("max_ts"),
            )
            .group_by(NormalizedReading.channel_id)
            .subquery()
        )

        stmt = select(NormalizedReading).join(
            subq,
            and_(
                NormalizedReading.channel_id == subq.c.channel_id,
                NormalizedReading.measured_at_utc == subq.c.max_ts,
            ),
        )
        if channel_ids:
            stmt = stmt.where(NormalizedReading.channel_id.in_(channel_ids))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_reading_by_ingestion_id(
        self,
        db: AsyncSession,
        ingestion_id: int,
    ) -> Optional[NormalizedReading]:
        stmt = select(NormalizedReading).where(NormalizedReading.ingestion_id == ingestion_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


reading_service = ReadingService()
