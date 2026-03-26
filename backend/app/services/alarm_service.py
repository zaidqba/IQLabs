"""
Alarm Service — query layer for alarm data.
Business logic (state machine) lives in rules_engine/alarm_manager.py.
"""
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime import ActiveAlarm, AlarmHistory


class AlarmService:
    async def get_active_alarms(
        self,
        db: AsyncSession,
        states: Optional[list[str]] = None,
        severity: Optional[str] = None,
        channel_id: Optional[int] = None,
    ) -> list[ActiveAlarm]:
        conditions = []
        if states:
            conditions.append(ActiveAlarm.alarm_state.in_(states))
        if severity:
            conditions.append(ActiveAlarm.severity_level == severity)
        if channel_id:
            conditions.append(ActiveAlarm.channel_id == channel_id)

        stmt = (
            select(ActiveAlarm)
            .where(and_(*conditions) if conditions else True)
            .order_by(ActiveAlarm.triggered_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_alarm_by_id(self, db: AsyncSession, alarm_id: int) -> Optional[ActiveAlarm]:
        stmt = select(ActiveAlarm).where(ActiveAlarm.alarm_id == alarm_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_alarm_history(
        self,
        db: AsyncSession,
        channel_id: Optional[int] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AlarmHistory]:
        conditions = []
        if channel_id:
            conditions.append(AlarmHistory.channel_id == channel_id)

        stmt = (
            select(AlarmHistory)
            .where(and_(*conditions) if conditions else True)
            .order_by(AlarmHistory.event_timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


alarm_service = AlarmService()
