"""
Calibration Service — manage detector calibration records.
Records are immutable once created (new record supersedes old).
Creating a calibration record requires an electronic signature.
"""
from datetime import date
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import CalibrationRecord
from app.models.master import Channel


class CalibrationService:
    async def list_records(
        self,
        db: AsyncSession,
        channel_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[CalibrationRecord]:
        conditions = []
        if channel_id:
            conditions.append(CalibrationRecord.channel_id == channel_id)

        stmt = (
            select(CalibrationRecord)
            .where(and_(*conditions) if conditions else True)
            .order_by(CalibrationRecord.calibration_date.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_record(
        self,
        db: AsyncSession,
        channel_id: int,
        calibration_date: date,
        next_calibration_due: date,
        calibration_factor: float,
        reference_standard: str,
        performed_by_user_id: int,
        signature_id: int,
        notes: Optional[str] = None,
    ) -> CalibrationRecord:
        # Mark previous records for this channel as not current
        from sqlalchemy import update
        await db.execute(
            update(CalibrationRecord)
            .where(
                and_(
                    CalibrationRecord.channel_id == channel_id,
                    CalibrationRecord.is_current == True,
                )
            )
            .values(is_current=False)
        )

        record = CalibrationRecord(
            channel_id=channel_id,
            calibration_date=calibration_date,
            next_calibration_due=next_calibration_due,
            calibration_factor=calibration_factor,
            reference_standard=reference_standard,
            performed_by_user_id=performed_by_user_id,
            signature_id=signature_id,
            notes=notes,
            is_current=True,
        )
        db.add(record)
        await db.flush()
        return record

    async def get_channels_due_for_calibration(
        self,
        db: AsyncSession,
        within_days: int = 30,
    ) -> list[CalibrationRecord]:
        """Return current calibration records due within N days."""
        from datetime import date, timedelta
        threshold_date = date.today() + timedelta(days=within_days)
        stmt = (
            select(CalibrationRecord)
            .where(
                and_(
                    CalibrationRecord.is_current == True,
                    CalibrationRecord.next_calibration_due <= threshold_date,
                )
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


calibration_service = CalibrationService()
