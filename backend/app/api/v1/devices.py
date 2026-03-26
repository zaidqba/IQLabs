"""Devices and Channels API endpoints."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.master import AlarmProfile, Channel, Device, UnitOfMeasure, Vendor
from app.models.runtime import DeviceStatus
from app.schemas.devices import (
    AlarmProfileResponse,
    ChannelResponse,
    DeviceResponse,
    UpdateThresholdRequest,
)
from app.services.signature_service import SignatureService

router = APIRouter(tags=["Devices & Channels"])
signature_service = SignatureService()


@router.get("/devices", response_model=list[DeviceResponse], tags=["Devices & Channels"])
async def list_devices(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Device, Vendor).join(Vendor, Device.vendor_id == Vendor.vendor_id)
        .where(Device.is_active == True)
    )
    return [
        DeviceResponse(
            device_id=d.device_id,
            device_code=d.device_code,
            device_name=d.device_name,
            device_type=d.device_type,
            ip_address=d.ip_address,
            port=d.port,
            protocol=d.protocol,
            poll_interval_s=d.poll_interval_s,
            is_active=d.is_active,
            vendor_code=v.vendor_code,
        )
        for d, v in result.all()
    ]


@router.get("/channels", response_model=list[ChannelResponse], tags=["Devices & Channels"])
async def list_channels(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Channel, Device, UnitOfMeasure)
        .join(Device, Channel.device_id == Device.device_id)
        .join(UnitOfMeasure, Channel.uom_id == UnitOfMeasure.uom_id)
        .where(Channel.is_active == True)
    )
    return [
        ChannelResponse(
            channel_id=ch.channel_id,
            channel_code=ch.channel_code,
            channel_name=ch.channel_name,
            rotem_point_id=ch.rotem_point_id,
            device_code=dev.device_code,
            detector_code=None,
            uom_symbol=uom.uom_symbol,
            uom_code=uom.uom_code,
            expected_update_s=ch.expected_update_s,
            stale_threshold_s=ch.stale_threshold_s,
            is_active=ch.is_active,
        )
        for ch, dev, uom in result.all()
    ]


@router.get("/channels/{channel_id}/thresholds", response_model=AlarmProfileResponse)
async def get_channel_thresholds(
    channel_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlarmProfile)
        .where(AlarmProfile.channel_id == channel_id, AlarmProfile.is_current == True)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No current alarm profile for channel")
    return AlarmProfileResponse.model_validate(profile)


@router.patch("/channels/{channel_id}/thresholds", response_model=AlarmProfileResponse)
async def update_channel_thresholds(
    channel_id: int,
    body: UpdateThresholdRequest,
    request: Request,
    user: CurrentUser,
    _: None = require_permission("sign:thresholds"),
    db: AsyncSession = Depends(get_db),
):
    """Update alarm thresholds for a channel. Requires e-signature and creates versioned record."""
    # Get current profile
    result = await db.execute(
        select(AlarmProfile)
        .where(AlarmProfile.channel_id == channel_id, AlarmProfile.is_current == True)
    )
    current_profile = result.scalar_one_or_none()

    # Create electronic signature
    ip = request.headers.get("X-Forwarded-For") or (
        request.client.host if request.client else None
    )
    sig = await signature_service.create_signature(
        db=db,
        user_id=user.user_id,
        password=body.signature_password,
        item_type="THRESHOLD_CHANGE",
        item_id=f"channel_{channel_id}",
        meaning=body.meaning,
        ip_address=ip,
        session_id=getattr(request.state, "session_id", None),
    )

    # Invalidate current profile
    if current_profile:
        from datetime import datetime, timezone
        current_profile.is_current = False
        current_profile.effective_to = datetime.now(timezone.utc)

    new_version = (current_profile.profile_version + 1) if current_profile else 1

    new_profile = AlarmProfile(
        channel_id=channel_id,
        profile_version=new_version,
        low_threshold=body.low_threshold,
        alert_threshold=body.alert_threshold,
        alarm_threshold=body.alarm_threshold,
        danger_threshold=body.danger_threshold,
        high_dose_threshold=body.high_dose_threshold,
        change_reason=body.change_reason,
        approved_by=user.user_id,
        approval_signature_id=sig.signature_id,
        created_by=user.user_id,
    )
    db.add(new_profile)
    await db.flush()

    # Record in threshold_change_log
    from app.models.compliance import ThresholdChangeLog
    db.add(ThresholdChangeLog(
        channel_id=channel_id,
        old_profile_id=current_profile.profile_id if current_profile else None,
        new_profile_id=new_profile.profile_id,
        change_reason=body.change_reason,
        risk_assessment=body.risk_assessment,
        changed_by=user.user_id,
        approved_by=user.user_id,
        approval_signature_id=sig.signature_id,
    ))

    # Attach audit detail
    request.state.audit_detail = json.dumps({
        "before": {"alert": str(current_profile.alert_threshold) if current_profile else None,
                   "alarm": str(current_profile.alarm_threshold) if current_profile else None,
                   "danger": str(current_profile.danger_threshold) if current_profile else None},
        "after": {"alert": str(body.alert_threshold),
                  "alarm": str(body.alarm_threshold),
                  "danger": str(body.danger_threshold)},
    })

    await db.commit()
    return AlarmProfileResponse.model_validate(new_profile)
