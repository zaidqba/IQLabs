"""
IQ-RAD Compliance Watchdog
Background compliance checks — run every 60 seconds by ingestion_service.

Checks performed:
1. NTP drift: flag readings SUSPECT if abs(ntp_offset_ms) > MAX_NTP_DRIFT_MS
2. Heartbeat timeout: COMM_FAIL alarm if device silent > 2× poll_interval
3. Calibration due: advisory if detector calibration_due_date ≤ today + 30 days
4. Stale data: STALE alarm if channel has no reading for stale_threshold_s
5. Pending review deadline: escalate if pending_review > 24 hours old
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.ntp_sync import get_ntp_offset_ms, is_ntp_valid
from app.models.compliance import ReviewRecord
from app.models.master import Channel, Detector
from app.models.runtime import ActiveAlarm, AlarmHistory, DeviceStatus, HeartbeatLog

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class ComplianceAlert:
    alert_type: str
    severity: str       # 'INFO', 'WARNING', 'CRITICAL'
    message: str
    channel_id: Optional[int] = None
    device_id: Optional[int] = None
    detector_id: Optional[int] = None


class ComplianceWatchdog:
    """
    Runs periodic compliance checks and creates system alarms as needed.
    All alarms written to active_alarms + alarm_history (immutable).
    """

    def __init__(self, device_poll_intervals: dict[int, int]):
        """
        device_poll_intervals: {device_id: poll_interval_s}
        """
        self._device_poll_intervals = device_poll_intervals

    async def run_checks(self, db: AsyncSession) -> list[ComplianceAlert]:
        """Run all compliance checks and return list of alerts."""
        alerts: list[ComplianceAlert] = []
        alerts.extend(await self._check_ntp_drift(db))
        alerts.extend(await self._check_heartbeat_timeouts(db))
        alerts.extend(await self._check_stale_channels(db))
        alerts.extend(await self._check_calibration_due(db))
        alerts.extend(await self._check_pending_reviews(db))
        return alerts

    async def _check_ntp_drift(self, db: AsyncSession) -> list[ComplianceAlert]:
        alerts = []
        if not is_ntp_valid():
            offset = get_ntp_offset_ms()
            alerts.append(ComplianceAlert(
                alert_type="NTP_DRIFT",
                severity="WARNING",
                message=f"NTP clock drift exceeds threshold: offset={offset}ms, max={settings.max_ntp_drift_ms}ms. All readings will be flagged SUSPECT.",
            ))
        return alerts

    async def _check_heartbeat_timeouts(self, db: AsyncSession) -> list[ComplianceAlert]:
        alerts = []
        now = datetime.now(timezone.utc)

        for device_id, poll_interval in self._device_poll_intervals.items():
            timeout = timedelta(seconds=poll_interval * 2)
            cutoff = now - timeout

            result = await db.execute(
                select(HeartbeatLog)
                .where(
                    HeartbeatLog.device_id == device_id,
                    HeartbeatLog.beat_at_utc >= cutoff,
                )
                .limit(1)
            )
            last_beat = result.scalar_one_or_none()

            if last_beat is None:
                alerts.append(ComplianceAlert(
                    alert_type="COMM_FAIL",
                    severity="CRITICAL",
                    message=f"Device {device_id}: No heartbeat received within {poll_interval*2}s",
                    device_id=device_id,
                ))
                await self._ensure_comm_fail_alarm(db, device_id)

        return alerts

    async def _check_stale_channels(self, db: AsyncSession) -> list[ComplianceAlert]:
        alerts = []
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = result.scalars().all()

        for channel in channels:
            cutoff = now - timedelta(seconds=channel.stale_threshold_s)
            reading_result = await db.execute(
                text(
                    "SELECT TOP 1 measured_at_utc FROM normalized_readings "
                    "WHERE channel_id = :cid ORDER BY measured_at_utc DESC"
                ),
                {"cid": channel.channel_id},
            )
            row = reading_result.first()

            if row is None or row[0] < cutoff:
                age_s = int((now - row[0]).total_seconds()) if row else None
                alerts.append(ComplianceAlert(
                    alert_type="STALE",
                    severity="WARNING",
                    message=f"Channel {channel.channel_code}: No data for {age_s or 'unknown'}s (threshold={channel.stale_threshold_s}s)",
                    channel_id=channel.channel_id,
                ))

        return alerts

    async def _check_calibration_due(self, db: AsyncSession) -> list[ComplianceAlert]:
        alerts = []
        today = datetime.now(timezone.utc).date()
        warning_threshold = today + timedelta(days=30)

        result = await db.execute(
            select(Detector).where(
                Detector.is_active == True,
                Detector.calibration_due <= warning_threshold,
            )
        )
        detectors = result.scalars().all()

        for det in detectors:
            days_remaining = (det.calibration_due - today).days if det.calibration_due else -1
            severity = "CRITICAL" if days_remaining < 0 else "WARNING"
            alerts.append(ComplianceAlert(
                alert_type="CALIBRATION_DUE",
                severity=severity,
                message=f"Detector {det.detector_code}: Calibration {'OVERDUE' if days_remaining < 0 else f'due in {days_remaining} days'} (due={det.calibration_due})",
                detector_id=det.detector_id,
            ))

        return alerts

    async def _check_pending_reviews(self, db: AsyncSession) -> list[ComplianceAlert]:
        alerts = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        result = await db.execute(
            select(ReviewRecord).where(
                ReviewRecord.review_state == "PENDING_REVIEW",
                ReviewRecord.created_at <= cutoff,
            )
        )
        overdue = result.scalars().all()

        for review in overdue:
            alerts.append(ComplianceAlert(
                alert_type="REVIEW_OVERDUE",
                severity="WARNING",
                message=f"Review record {review.review_id} ({review.review_type}) has been pending for >24h",
            ))

        return alerts

    async def _ensure_comm_fail_alarm(self, db: AsyncSession, device_id: int) -> None:
        """Create a SYSTEM/COMM_FAIL alarm if one isn't already active for this device."""
        from app.models.master import Channel
        result = await db.execute(
            select(Channel.channel_id).where(
                Channel.device_id == device_id,
                Channel.is_active == True,
            ).limit(1)
        )
        channel_row = result.first()
        if channel_row is None:
            return

        channel_id = channel_row[0]

        existing = await db.execute(
            select(ActiveAlarm).where(
                ActiveAlarm.channel_id == channel_id,
                ActiveAlarm.alarm_type == "COMM_FAIL",
                ActiveAlarm.alarm_state == "ACTIVE",
            )
        )
        if existing.scalar_one_or_none():
            return  # Already active

        alarm = ActiveAlarm(
            channel_id=channel_id,
            alarm_type="COMM_FAIL",
            severity_level="ALARM",
            alarm_state="ACTIVE",
            alarm_message=f"Device {device_id}: Communication failure — no heartbeat received",
            requires_signature=False,
        )
        db.add(alarm)
        await db.flush()

        db.add(AlarmHistory(
            alarm_id=alarm.alarm_id,
            channel_id=channel_id,
            event_type="TRIGGERED",
            new_state="ACTIVE",
            severity_level="ALARM",
            comment="Auto-generated by compliance watchdog: communication failure",
        ))
