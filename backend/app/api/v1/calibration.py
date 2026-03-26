"""Calibration records API endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.compliance import CalibrationRecord
from app.models.master import Detector
from app.schemas.calibration import (
    CalibrationResponse,
    CreateCalibrationRequest,
    ReviewCalibrationRequest,
)
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/calibrations", tags=["Calibration"])
signature_service = SignatureService()


@router.get("", response_model=list[CalibrationResponse])
async def list_calibrations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    result = await db.execute(
        select(CalibrationRecord, Detector)
        .join(Detector, CalibrationRecord.detector_id == Detector.detector_id)
        .order_by(CalibrationRecord.calibration_date.desc())
    )
    return [
        CalibrationResponse(
            cal_id=cal.cal_id,
            detector_id=cal.detector_id,
            detector_code=det.detector_code,
            calibration_date=cal.calibration_date,
            next_due_date=cal.next_due_date,
            calibration_source=cal.calibration_source,
            correction_factor=cal.correction_factor,
            pass_fail=cal.pass_fail,
            performed_by_name=cal.performed_by_name,
            certificate_ref=cal.certificate_ref,
            notes=cal.notes,
            is_overdue=cal.next_due_date < today,
        )
        for cal, det in result.all()
    ]


@router.post("", response_model=CalibrationResponse)
async def create_calibration(
    body: CreateCalibrationRequest,
    user: CurrentUser,
    _: None = require_permission("write:calibration"),
    db: AsyncSession = Depends(get_db),
):
    det_result = await db.execute(
        select(Detector).where(Detector.detector_id == body.detector_id)
    )
    det = det_result.scalar_one_or_none()
    if not det:
        raise HTTPException(status_code=404, detail="Detector not found")

    cal = CalibrationRecord(
        detector_id=body.detector_id,
        calibration_date=body.calibration_date,
        next_due_date=body.next_due_date,
        calibration_source=body.calibration_source,
        source_activity_bq=body.source_activity_bq,
        source_cert_number=body.source_cert_number,
        as_found_reading=body.as_found_reading,
        as_left_reading=body.as_left_reading,
        correction_factor=body.correction_factor,
        pass_fail=body.pass_fail,
        performed_by_name=body.performed_by_name,
        certificate_ref=body.certificate_ref,
        notes=body.notes,
        created_by=user.user_id,
    )
    db.add(cal)

    # Update detector calibration_due
    det.calibration_due = body.next_due_date
    await db.commit()
    await db.refresh(cal)

    return CalibrationResponse(
        cal_id=cal.cal_id,
        detector_id=cal.detector_id,
        detector_code=det.detector_code,
        calibration_date=cal.calibration_date,
        next_due_date=cal.next_due_date,
        calibration_source=cal.calibration_source,
        correction_factor=cal.correction_factor,
        pass_fail=cal.pass_fail,
        performed_by_name=cal.performed_by_name,
        certificate_ref=cal.certificate_ref,
        notes=cal.notes,
        is_overdue=False,
    )


@router.post("/{cal_id}/review", response_model=CalibrationResponse)
async def review_calibration(
    cal_id: int,
    body: ReviewCalibrationRequest,
    request: Request,
    user: CurrentUser,
    _: None = require_permission("sign:calibration"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CalibrationRecord, Detector)
        .join(Detector, CalibrationRecord.detector_id == Detector.detector_id)
        .where(CalibrationRecord.cal_id == cal_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Calibration record not found")

    cal, det = row
    ip = request.headers.get("X-Forwarded-For") or (
        request.client.host if request.client else None
    )
    sig = await signature_service.create_signature(
        db=db,
        user_id=user.user_id,
        password=body.signature_password,
        item_type="CALIBRATION_REVIEW",
        item_id=str(cal_id),
        meaning=body.meaning,
        ip_address=ip,
        session_id=getattr(request.state, "session_id", None),
    )

    cal.reviewed_by = user.user_id
    cal.review_signature_id = sig.signature_id
    if body.notes:
        cal.notes = (cal.notes or "") + f"\nReview note: {body.notes}"

    await db.commit()
    return CalibrationResponse(
        cal_id=cal.cal_id,
        detector_id=cal.detector_id,
        detector_code=det.detector_code,
        calibration_date=cal.calibration_date,
        next_due_date=cal.next_due_date,
        calibration_source=cal.calibration_source,
        correction_factor=cal.correction_factor,
        pass_fail=cal.pass_fail,
        performed_by_name=cal.performed_by_name,
        certificate_ref=cal.certificate_ref,
        notes=cal.notes,
        reviewed_by_username=user.username,
        is_overdue=cal.next_due_date < date.today(),
    )
