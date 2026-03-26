"""Alarms API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.exceptions import ResourceNotFoundError, SignatureError, ValidationError
from app.models.master import Channel
from app.models.runtime import ActiveAlarm, AlarmHistory
from app.rules_engine.alarm_manager import AlarmManager
from app.schemas.alarms import AcknowledgeAlarmRequest, AlarmResponse, AlarmStatsResponse
from app.schemas.common import AlarmState, SeverityLevel
from app.services.signature_service import SignatureService
from app.services.websocket_service import ws_manager

router = APIRouter(prefix="/alarms", tags=["Alarms"])
alarm_manager = AlarmManager()
signature_service = SignatureService()


@router.get("/active", response_model=list[AlarmResponse])
async def list_active_alarms(
    user: CurrentUser,
    channel_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ActiveAlarm, Channel)
        .join(Channel, ActiveAlarm.channel_id == Channel.channel_id)
        .where(ActiveAlarm.alarm_state.in_([AlarmState.ACTIVE, AlarmState.ACKNOWLEDGED]))
        .order_by(ActiveAlarm.triggered_at_utc.desc())
    )
    if channel_id:
        query = query.where(ActiveAlarm.channel_id == channel_id)
    if severity:
        query = query.where(ActiveAlarm.severity_level == severity)

    result = await db.execute(query)
    rows = result.all()

    return [
        _alarm_response(alarm, channel)
        for alarm, channel in rows
    ]


@router.get("/history", response_model=list[AlarmResponse])
async def alarm_history(
    user: CurrentUser,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    channel_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ActiveAlarm, Channel)
        .join(Channel, ActiveAlarm.channel_id == Channel.channel_id)
        .order_by(ActiveAlarm.triggered_at_utc.desc())
    )
    if channel_id:
        query = query.where(ActiveAlarm.channel_id == channel_id)
    if severity:
        query = query.where(ActiveAlarm.severity_level == severity)
    if from_dt:
        query = query.where(ActiveAlarm.triggered_at_utc >= from_dt)
    if to_dt:
        query = query.where(ActiveAlarm.triggered_at_utc <= to_dt)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [_alarm_response(a, ch) for a, ch in result.all()]


@router.get("/{alarm_id}", response_model=AlarmResponse)
async def get_alarm(
    alarm_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ActiveAlarm, Channel)
        .join(Channel, ActiveAlarm.channel_id == Channel.channel_id)
        .where(ActiveAlarm.alarm_id == alarm_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return _alarm_response(row[0], row[1])


@router.post("/{alarm_id}/acknowledge", response_model=AlarmResponse)
async def acknowledge_alarm(
    alarm_id: int,
    body: AcknowledgeAlarmRequest,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    alarm = await db.get(ActiveAlarm, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm not found")

    # Create e-signature (21 CFR Part 11 §11.200)
    signature_id = None
    if alarm.requires_signature:
        try:
            ip = request.headers.get("X-Forwarded-For") or (
                request.client.host if request.client else None
            )
            sig = await signature_service.create_signature(
                db=db,
                user_id=user.user_id,
                password=body.signature_password,
                item_type="ALARM_ACK",
                item_id=str(alarm_id),
                meaning=body.meaning,
                ip_address=ip,
                session_id=getattr(request.state, "session_id", None),
            )
            signature_id = sig.signature_id
        except (SignatureError, Exception) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature authentication failed: {exc}",
            ) from exc

    try:
        alarm = await alarm_manager.acknowledge(
            db=db,
            alarm_id=alarm_id,
            user_id=user.user_id,
            username=user.username,
            comment=body.comment,
            signature_id=signature_id,
        )
        await db.commit()

        # Broadcast acknowledgement
        await ws_manager.broadcast({
            "type": "alarm",
            "event_type": "alarm_acknowledged",
            "alarm_id": alarm_id,
            "channel_id": alarm.channel_id,
            "acknowledged_by": user.username,
        })

        result = await db.execute(
            select(ActiveAlarm, Channel)
            .join(Channel, ActiveAlarm.channel_id == Channel.channel_id)
            .where(ActiveAlarm.alarm_id == alarm_id)
        )
        row = result.first()
        return _alarm_response(row[0], row[1])

    except (ResourceNotFoundError, ValidationError) as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _alarm_response(alarm: ActiveAlarm, channel: Channel) -> AlarmResponse:
    return AlarmResponse(
        alarm_id=alarm.alarm_id,
        channel_id=alarm.channel_id,
        channel_code=channel.channel_code,
        channel_name=channel.channel_name,
        alarm_type=alarm.alarm_type,
        severity_level=alarm.severity_level,
        triggered_at_utc=alarm.triggered_at_utc,
        trigger_value=alarm.trigger_value,
        alarm_state=alarm.alarm_state,
        alarm_message=alarm.alarm_message,
        requires_signature=alarm.requires_signature,
        acknowledged_at_utc=alarm.acknowledged_at_utc,
        acknowledged_by_username=None,  # Enriched via join if needed
        ack_comment=alarm.ack_comment,
    )
