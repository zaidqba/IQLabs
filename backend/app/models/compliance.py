"""
IQ-RAD Compliance & Quality ORM Models
AuditTrail, ElectronicSignature, ConfigVersion, ThresholdChangeLog,
CalibrationRecord, MaintenanceRecord, ReviewRecord, ReportArchive
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DATETIME,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AuditTrail(Base, TimestampMixin):
    """
    IMMUTABLE — protected by DDL trigger trg_audit_trail_immutable.
    Every system action is recorded here permanently.
    Satisfies 21 CFR Part 11 §11.10(e).
    """
    __tablename__ = "audit_trail"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    user_name: Mapped[Optional[str]] = mapped_column(String(100))
    user_role: Mapped[Optional[str]] = mapped_column(String(50))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    http_method: Mapped[Optional[str]] = mapped_column(String(10))
    endpoint: Mapped[Optional[str]] = mapped_column(String(500))
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))
    action_detail: Mapped[Optional[str]] = mapped_column(Text)
    result_code: Mapped[Optional[int]] = mapped_column(Integer)
    result_status: Mapped[Optional[str]] = mapped_column(String(20))
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)


class ElectronicSignature(Base, TimestampMixin):
    """
    21 CFR Part 11 §11.50 signature manifestations.
    §11.200(a)(1): two-component auth (JWT session_id + password re-entry).
    """
    __tablename__ = "electronic_signatures"

    signature_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_role: Mapped[str] = mapped_column(String(50), nullable=False)
    signed_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    meaning: Mapped[str] = mapped_column(String(500), nullable=False)
    signed_item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    signed_item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    authentication_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PASSWORD"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(500))

    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]


class ConfigVersion(Base, TimestampMixin):
    __tablename__ = "config_versions"

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    config_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    changed_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    approval_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ThresholdChangeLog(Base, TimestampMixin):
    """IMMUTABLE — protected by DDL trigger."""
    __tablename__ = "threshold_change_log"

    change_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.channel_id"), nullable=False)
    changed_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    old_profile_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("alarm_profiles.profile_id")
    )
    new_profile_id: Mapped[int] = mapped_column(
        ForeignKey("alarm_profiles.profile_id"), nullable=False
    )
    change_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    risk_assessment: Mapped[Optional[str]] = mapped_column(String(1000))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    approval_signature_id: Mapped[int] = mapped_column(
        ForeignKey("electronic_signatures.signature_id"), nullable=False
    )


class CalibrationRecord(Base, TimestampMixin):
    __tablename__ = "calibration_records"

    cal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    detector_id: Mapped[int] = mapped_column(ForeignKey("detectors.detector_id"), nullable=False)
    calibration_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    calibration_source: Mapped[Optional[str]] = mapped_column(String(200))
    source_activity_bq: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    source_cert_number: Mapped[Optional[str]] = mapped_column(String(100))
    as_found_reading: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    as_left_reading: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    correction_factor: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=1.0)
    pass_fail: Mapped[str] = mapped_column(String(15), nullable=False)
    performed_by_name: Mapped[str] = mapped_column(String(100), nullable=False)
    performed_by_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    review_signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )
    certificate_ref: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    detector: Mapped["Detector"] = relationship("Detector")  # type: ignore[name-defined]


class ReviewRecord(Base, TimestampMixin):
    __tablename__ = "review_records"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)
    review_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    review_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.site_id"), nullable=False)
    review_state: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING_REVIEW"
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    reviewed_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text)
    reviewer_signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    approved_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    approver_comment: Mapped[Optional[str]] = mapped_column(Text)
    approver_signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )
    data_completeness_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    total_readings_expected: Mapped[Optional[int]] = mapped_column(Integer)
    total_readings_received: Mapped[Optional[int]] = mapped_column(Integer)
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alarm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)


class ReportArchive(Base, TimestampMixin):
    __tablename__ = "report_archive"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    report_title: Mapped[str] = mapped_column(String(200), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.site_id"), nullable=False)
    generated_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    report_state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_hash_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    approved_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    approval_signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )
    review_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("review_records.review_id")
    )
