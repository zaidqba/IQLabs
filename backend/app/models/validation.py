"""IQ-RAD Validation & QMS ORM Models"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import DATETIME, BigInteger, Date, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RequirementsTraceability(Base, TimestampMixin):
    __tablename__ = "requirements_traceability"

    req_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    req_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    req_category: Mapped[str] = mapped_column(String(50), nullable=False)
    regulation_ref: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(String(1000), nullable=False)
    test_script_ids: Mapped[Optional[str]] = mapped_column(String(500))
    implementation_ref: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)


class TestScript(Base, TimestampMixin):
    __tablename__ = "test_scripts"

    script_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    script_type: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    preconditions: Mapped[Optional[str]] = mapped_column(Text)
    test_steps: Mapped[str] = mapped_column(Text, nullable=False)
    expected_results: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    req_codes: Mapped[Optional[str]] = mapped_column(String(500))
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)


class TestExecutionLog(Base, TimestampMixin):
    __tablename__ = "test_execution_log"

    exec_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    script_code: Mapped[str] = mapped_column(String(30), nullable=False)
    executed_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    executed_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    system_version: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    actual_result: Mapped[Optional[str]] = mapped_column(Text)
    deviation_ref: Mapped[Optional[str]] = mapped_column(String(20))
    evidence_path: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    signature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("electronic_signatures.signature_id")
    )


class DeviationLog(Base, TimestampMixin):
    __tablename__ = "deviation_log"

    deviation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dev_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    deviation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    detected_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    detected_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    impact_assessment: Mapped[Optional[str]] = mapped_column(Text)
    immediate_action: Mapped[Optional[str]] = mapped_column(Text)
    capa_id: Mapped[Optional[int]] = mapped_column(Integer)
    closed_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    closed_by: Mapped[Optional[int]] = mapped_column(Integer)
    closure_signature_id: Mapped[Optional[int]] = mapped_column(Integer)


class CapaLog(Base, TimestampMixin):
    __tablename__ = "capa_log"

    capa_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capa_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    capa_type: Mapped[str] = mapped_column(String(20), nullable=False)
    deviation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("deviation_log.deviation_id")
    )
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    completion_evidence: Mapped[Optional[str]] = mapped_column(Text)
    completed_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    completed_by: Mapped[Optional[int]] = mapped_column(Integer)
    verified_by: Mapped[Optional[int]] = mapped_column(Integer)
    verified_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    verification_signature_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
