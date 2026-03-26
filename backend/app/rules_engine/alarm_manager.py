"""
IQ-RAD Alarm Manager
Stateful alarm lifecycle management.
All state transitions write immutable records to alarm_history.

State Machine per channel:
  (no alarm) ──threshold crossed──→ ACTIVE
  ACTIVE ──user ack──→ ACKNOWLEDGED
  ACKNOWLEDGED ──value returns to NORMAL──→ CLEARED
  ACTIVE ──unacked, value still high──→ ESCALATED (still ACTIVE)
  ACTIVE/ACKNOWLEDGED ──operator suppress──→ SUPPRESSED
  CLEARED → removed from active_alarms, full record in alarm_history

21 CFR Part 11: acknowledgement of DANGER/HIGH_DOSE requires e-signature.
All transitions preserved in alarm_history (immutable).
"""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.runtime import ActiveAlarm, AlarmHistory, NormalizedReading
from app.rules_engine.threshold_evaluator import ThresholdEvaluator
from app.schemas.common import AlarmState, AlarmType, NormalizedEvent, SeverityLevel

logger = get_logger(__name__)

evaluator = ThresholdEvaluator()


class AlarmManager:
    """
    Manages alarm creation, state transitions, and alarm_history writes.
    All methods require a DB session — they do not commit; the caller commits.
    """

    async def handle_event(
        self,
        db: AsyncSession,
        event: NormalizedEvent,
        reading_id: int,
    ) -> list[dict]:
        """
        Evaluate a NormalizedEvent and update alarm state accordingly.
        Returns list of alarm events to broadcast via WebSocket.

        Steps:
        1. Evaluate severity
        2. If severity > NORMAL: create or escalate active alarm
        3. If severity == NORMAL: auto-clear any active alarm on this channel
        4. Write alarm_history for every transition
        """
        ws_events = []
        severity, threshold_name = evaluator.evaluate(event)

        # Update severity on the event
        event = event.model_copy(
            update={"severity_level": severity, "threshold_exceeded": threshold_name}
        )

        # Check for existing active alarm on this channel
        existing = await self._get_active_alarm(db, event.channel_id)

        if severity == SeverityLevel.NORMAL:
            if existing and existing.alarm_state in (
                AlarmState.ACKNOWLEDGED, AlarmState.ACTIVE
            ):
                # Auto-clear if value returned to normal
                await self._clear_alarm(db, existing, event)
                ws_events.append(self._ws_event("alarm_cleared", existing, event))
        else:
            if existing is None:
                # New alarm
                alarm = await self._create_alarm(db, event, severity, threshold_name, reading_id)
                ws_events.append(self._ws_event("alarm_triggered", alarm, event))
            else:
                # Severity changed — update alarm type if escalating
                if self._is_escalation(existing.severity_level, severity.value):
                    await self._escalate_alarm(db, existing, event, severity)
                    ws_events.append(self._ws_event("alarm_escalated", existing, event))

        return ws_events

    async def acknowledge(
        self,
        db: AsyncSession,
        alarm_id: int,
        user_id: int,
        username: str,
        comment: str,
        signature_id: Optional[int] = None,
    ) -> ActiveAlarm:
        """
        Acknowledge an active alarm.
        DANGER/HIGH_DOSE require signature_id (verified by caller).
        Writes alarm_history entry.
        """
        alarm = await db.get(ActiveAlarm, alarm_id)
        if alarm is None:
            from app.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(f"Alarm {alarm_id} not found")

        if alarm.alarm_state != AlarmState.ACTIVE:
            from app.core.exceptions import ValidationError
            raise ValidationError(
                f"Alarm {alarm_id} is in state {alarm.alarm_state}, cannot acknowledge"
            )

        prev_state = alarm.alarm_state
        alarm.alarm_state = AlarmState.ACKNOWLEDGED
        alarm.acknowledged_at_utc = datetime.now(timezone.utc)
        alarm.acknowledged_by = user_id
        alarm.ack_comment = comment
        alarm.ack_signature_id = signature_id

        history = AlarmHistory(
            alarm_id=alarm.alarm_id,
            channel_id=alarm.channel_id,
            event_type="ACKNOWLEDGED",
            previous_state=prev_state,
            new_state=AlarmState.ACKNOWLEDGED,
            actor_user_id=user_id,
            actor_username=username,
            comment=comment,
            signature_id=signature_id,
        )
        db.add(history)
        return alarm

    async def _get_active_alarm(
        self, db: AsyncSession, channel_id: int
    ) -> Optional[ActiveAlarm]:
        result = await db.execute(
            select(ActiveAlarm).where(
                ActiveAlarm.channel_id == channel_id,
                ActiveAlarm.alarm_state.in_([AlarmState.ACTIVE, AlarmState.ACKNOWLEDGED]),
            )
        )
        return result.scalar_one_or_none()

    async def _create_alarm(
        self,
        db: AsyncSession,
        event: NormalizedEvent,
        severity: SeverityLevel,
        threshold_name: Optional[str],
        reading_id: int,
    ) -> ActiveAlarm:
        alarm_type = self._severity_to_alarm_type(severity, threshold_name)
        requires_sig = evaluator.requires_signature(severity)

        alarm = ActiveAlarm(
            channel_id=event.channel_id,
            alarm_type=alarm_type,
            severity_level=severity,
            trigger_value=event.normalized_value,
            trigger_reading_id=reading_id,
            alarm_state=AlarmState.ACTIVE,
            alarm_message=evaluator.alarm_message(
                event.channel_code, severity, event.normalized_value, event.uom_code
            ),
            requires_signature=requires_sig,
        )
        db.add(alarm)
        await db.flush()  # Get alarm_id

        history = AlarmHistory(
            alarm_id=alarm.alarm_id,
            channel_id=event.channel_id,
            event_type="TRIGGERED",
            previous_state=None,
            new_state=AlarmState.ACTIVE,
            reading_value=event.normalized_value,
            severity_level=severity,
        )
        db.add(history)
        logger.info(
            "alarm_triggered",
            extra={
                "alarm_id": alarm.alarm_id,
                "channel_id": event.channel_id,
                "channel_code": event.channel_code,
                "severity": severity,
                "value": str(event.normalized_value),
            },
        )
        return alarm

    async def _clear_alarm(
        self, db: AsyncSession, alarm: ActiveAlarm, event: NormalizedEvent
    ) -> None:
        prev_state = alarm.alarm_state
        alarm.alarm_state = AlarmState.CLEARED
        alarm.cleared_at_utc = datetime.now(timezone.utc)

        history = AlarmHistory(
            alarm_id=alarm.alarm_id,
            channel_id=alarm.channel_id,
            event_type="AUTO_CLEARED",
            previous_state=prev_state,
            new_state=AlarmState.CLEARED,
            reading_value=event.normalized_value,
            severity_level=SeverityLevel.NORMAL,
        )
        db.add(history)

    async def _escalate_alarm(
        self,
        db: AsyncSession,
        alarm: ActiveAlarm,
        event: NormalizedEvent,
        new_severity: SeverityLevel,
    ) -> None:
        alarm.severity_level = new_severity
        alarm.alarm_type = self._severity_to_alarm_type(new_severity, None)
        alarm.escalated_at_utc = datetime.now(timezone.utc)
        alarm.requires_signature = evaluator.requires_signature(new_severity)

        history = AlarmHistory(
            alarm_id=alarm.alarm_id,
            channel_id=alarm.channel_id,
            event_type="ESCALATED",
            previous_state=alarm.alarm_state,
            new_state=alarm.alarm_state,
            reading_value=event.normalized_value,
            severity_level=new_severity,
        )
        db.add(history)

    @staticmethod
    def _severity_to_alarm_type(
        severity: SeverityLevel, threshold_name: Optional[str]
    ) -> str:
        if threshold_name == "DATA_QUALITY":
            return AlarmType.SYSTEM
        return {
            SeverityLevel.LOW: AlarmType.LOW,
            SeverityLevel.ALERT: AlarmType.ALERT,
            SeverityLevel.ALARM: AlarmType.ALARM,
            SeverityLevel.DANGER: AlarmType.DANGER,
            SeverityLevel.HIGH_DOSE: AlarmType.HIGH_DOSE,
        }.get(severity, AlarmType.SYSTEM)

    @staticmethod
    def _is_escalation(current_severity: str, new_severity: str) -> bool:
        order = ["NORMAL", "LOW", "ALERT", "ALARM", "DANGER", "HIGH_DOSE"]
        return order.index(new_severity) > order.index(current_severity)

    @staticmethod
    def _ws_event(event_type: str, alarm: ActiveAlarm, event: NormalizedEvent) -> dict:
        return {
            "type": "alarm",
            "event_type": event_type,
            "alarm_id": alarm.alarm_id,
            "channel_id": event.channel_id,
            "channel_code": event.channel_code,
            "severity": str(event.severity_level),
            "alarm_type": str(alarm.alarm_type),
            "message": alarm.alarm_message,
            "value": str(event.normalized_value),
            "uom": event.uom_code,
            "triggered_at": alarm.triggered_at_utc.isoformat(),
            "requires_signature": alarm.requires_signature,
        }
