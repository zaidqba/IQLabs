"""
Reports API — generate and approve compliance reports.
Report approval requires electronic signature (21 CFR Part 11).
"""
import hashlib
import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.compliance import ReportArchive, ReviewRecord
from app.models.master import User
from app.schemas.reports import ApproveReportRequest, GenerateReportRequest, ReportResponse
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/reports", tags=["Reports"])
signature_service = SignatureService()

REPORTS_DIR = os.environ.get("REPORTS_DIR", "/app/reports")


def _report_to_response(report: ReportArchive, generated_by_username: str = "", approved_by_username: str | None = None) -> ReportResponse:
    return ReportResponse(
        report_id=report.report_id,
        report_type=report.report_type,
        report_title=report.report_title,
        period_start=report.period_start,
        period_end=report.period_end,
        report_state=report.report_state,
        generated_at_utc=report.generated_at_utc,
        generated_by_username=generated_by_username,
        approved_by_username=approved_by_username,
        approved_at_utc=report.approved_at_utc,
        file_hash_sha256=report.file_hash_sha256,
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    user: CurrentUser,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ReportArchive, User)
        .join(User, ReportArchive.generated_by == User.user_id)
        .order_by(ReportArchive.generated_at_utc.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        _report_to_response(r, gen_user.username)
        for r, gen_user in result.all()
    ]


@router.post("", response_model=ReportResponse, status_code=201)
async def generate_report(
    body: GenerateReportRequest,
    request: Request,
    user: CurrentUser,
    _: None = require_permission("write:reports"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new compliance report PDF and store it."""
    from app.models.runtime import NormalizedReading
    from sqlalchemy import func, and_

    # Build PDF content
    pdf_bytes = await _build_pdf(db, body, user.username)
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # Ensure reports directory exists
    os.makedirs(REPORTS_DIR, exist_ok=True)

    title = body.title or f"{body.report_type.replace('_', ' ').title()} {body.period_start}–{body.period_end}"
    filename = f"report_{body.report_type}_{body.period_start}_{body.period_end}_{sha256[:8]}.pdf"
    file_path = os.path.join(REPORTS_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    report = ReportArchive(
        report_type=body.report_type,
        report_title=title,
        period_start=body.period_start,
        period_end=body.period_end,
        site_id=body.site_id,
        generated_by=user.user_id,
        report_state="PENDING_REVIEW",
        file_path=file_path,
        file_hash_sha256=sha256,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return _report_to_response(report, user.username)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ReportArchive, User)
        .join(User, ReportArchive.generated_by == User.user_id)
        .where(ReportArchive.report_id == report_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    report, gen_user = row
    return _report_to_response(report, gen_user.username)


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ReportArchive).where(ReportArchive.report_id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    def file_stream():
        with open(report.file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        file_stream(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'},
    )


@router.post("/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: int,
    body: ApproveReportRequest,
    request: Request,
    user: CurrentUser,
    _: None = require_permission("sign:reports"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReportArchive, User)
        .join(User, ReportArchive.generated_by == User.user_id)
        .where(ReportArchive.report_id == report_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    report, gen_user = row

    if report.report_state not in ("PENDING_REVIEW", "REVIEWED"):
        raise HTTPException(status_code=409, detail=f"Report is already {report.report_state}")

    ip = request.headers.get("X-Forwarded-For") or (
        request.client.host if request.client else None
    )
    sig = await signature_service.create_signature(
        db=db,
        user_id=user.user_id,
        password=body.signature_password,
        item_type="REPORT_APPROVAL",
        item_id=str(report_id),
        meaning=body.meaning,
        ip_address=ip,
        session_id=getattr(request.state, "session_id", None),
    )

    report.report_state = "APPROVED"
    report.approved_by = user.user_id
    report.approved_at_utc = datetime.now(timezone.utc)
    report.approval_signature_id = sig.signature_id

    await db.commit()
    await db.refresh(report)
    return _report_to_response(report, gen_user.username, user.username)


async def _build_pdf(db: AsyncSession, body: GenerateReportRequest, generated_by: str) -> bytes:
    """Generate PDF report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("IQ-RAD Radiation Monitoring System", styles["Title"]))
        story.append(Paragraph(body.report_type.replace("_", " ").title(), styles["Heading1"]))
        story.append(Spacer(1, 0.15 * inch))

        meta = [
            ["Period:", f"{body.period_start} to {body.period_end}"],
            ["Generated:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Generated By:", generated_by],
            ["System:", "IQ-RAD v1.0 — Ionetix PET Facility USA56"],
            ["Compliance:", "21 CFR Part 11 / 21 CFR Part 212 / 10 CFR Part 20"],
        ]
        meta_tbl = Table(meta, colWidths=[1.5 * inch, 4.5 * inch])
        meta_tbl.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_tbl)
        story.append(Spacer(1, 0.25 * inch))

        # Channel summary
        from app.models.runtime import NormalizedReading
        from app.models.master import Channel, UnitOfMeasure
        from sqlalchemy import func, and_
        from datetime import datetime as dt

        start_dt = dt.combine(body.period_start, dt.min.time()).replace(tzinfo=timezone.utc)
        end_dt = dt.combine(body.period_end, dt.max.time()).replace(tzinfo=timezone.utc)

        ch_stmt = select(Channel, UnitOfMeasure).join(UnitOfMeasure, Channel.uom_id == UnitOfMeasure.uom_id).where(Channel.is_active == True)
        if body.channel_ids:
            ch_stmt = ch_stmt.where(Channel.channel_id.in_(body.channel_ids))
        ch_result = await db.execute(ch_stmt)
        channels = ch_result.all()

        table_data = [["Channel", "UOM", "Count", "Min", "Max", "Avg", "BAD/SUSPECT"]]
        for ch, uom in channels:
            stats = await db.execute(
                select(
                    func.count(NormalizedReading.ingestion_id),
                    func.min(NormalizedReading.normalized_value),
                    func.max(NormalizedReading.normalized_value),
                    func.avg(NormalizedReading.normalized_value),
                    func.sum(
                        func.iif(NormalizedReading.quality_flag.in_(["BAD", "SUSPECT"]), 1, 0)
                    ),
                ).where(and_(
                    NormalizedReading.channel_id == ch.channel_id,
                    NormalizedReading.measured_at_utc >= start_dt,
                    NormalizedReading.measured_at_utc <= end_dt,
                ))
            )
            cnt, mn, mx, avg, bad = stats.first() or (0, None, None, None, 0)
            table_data.append([
                ch.channel_code, uom.uom_symbol, str(cnt or 0),
                f"{mn:.4f}" if mn is not None else "—",
                f"{mx:.4f}" if mx is not None else "—",
                f"{avg:.4f}" if avg is not None else "—",
                str(bad or 0),
            ])

        story.append(Paragraph("Channel Reading Summary", styles["Heading2"]))
        t = Table(table_data, colWidths=[1.1 * inch, 0.7 * inch, 0.7 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t)

        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(
            "CONFIDENTIAL — 21 CFR Part 11 Electronic Record — Pending Review",
            styles["Normal"]
        ))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        return (
            f"IQ-RAD Report\n{body.report_type}\n{body.period_start} to {body.period_end}\n"
            "Generated by IQ-RAD v1.0\n[ReportLab not available]"
        ).encode()
