"""
IQ-RAD Runtime Data ORM Models
raw_ingestion_log, normalized_readings, device_status, channel_status,
active_alarms, alarm_history, heartbeat_log
IMMUTABLE tables: raw_ingestion_log, normalized_readings, alarm_history
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DATETIME,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RawIngestionLog(Base, TimestampMixin):
    """
    IMMUTABLE — protected by DDL trigger trg_raw_ingestion_immutable.
    Exact bytes received from each device. Never modified after INSERT.
    """
    __tablename__ = "raw_ingestion_log"

    ingestion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    received_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    source_ip: Mapped[Optional[str]] = mapped_column(String(45))
    source_port: Mapped[Optional[int]] = mapped_column(Integer)
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
    raw_payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload_length: Mapped[int] = mapped_column(Integer, nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    parse_error: Mapped[Optional[str]] = mapped_column(String)
    packet_sequence: Mapped[Optional[int]] = mapped_column(BigInteger)


class NormalizedReading(Base, TimestampMixin):
    """
    IMMUTABLE — protected by DDL trigger trg_normalized_readings_immutable.
    Corrections create new rows with quality_flag='CORRECTED'.
    """
    __tablename__ = "normalized_readings"
    __table_args__ = (
        Index("CIX_readings_channel_time", "channel_id", "measured_at_utc"),
        CheckConstraint(
            "quality_flag IN ('GOOD', 'SUSPECT', 'BAD', 'SIMULATED', 'CORRECTED')",
            name="CHK_readings_quality",
        ),
        CheckConstraint(
            "severity_level IN ('NORMAL', 'LOW', 'ALERT', 'ALARM', 'DANGER', 'HIGH_DOSE')",
            name="CHK_readings_severity",
        ),
    )

    reading_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ingestion_id: Mapped[int] = mapped_column(
        ForeignKey("raw_ingestion_log.ingestion_id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.channel_id"), nullable=False)
    measured_at_utc: Mapped[datetime] = mapped_column(DATETIME(timezone=False), nullable=False)
    received_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    raw_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    normalized_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom_id: Mapped[int] = mapped_column(ForeignKey("units_of_measure.uom_id"), nullable=False)
    quality_flag: Mapped[str] = mapped_column(String(20), nullable=False, default="GOOD")
    quality_detail: Mapped[Optional[str]] = mapped_column(String(500))
    alarm_profile_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("alarm_profiles.profile_id")
    )
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    is_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ntp_offset_ms: Mapped[Optional[int]] = mapped_column(Integer)

    ingestion: Mapped["RawIngestionLog"] = relationship("RawIngestionLog")
    channel: Mapped["Channel"] = relationship("Channel")  # type: ignore[name-defined]


class DeviceStatus(Base, TimestampMixin):
    __tablename__ = "device_status"

    status_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    status_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    status_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status_detail: Mapped[Optional[str]] = mapped_column(String(500))
    tcp_latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    retry_count: Mapped[Optional[int]] = mapped_column(Integer)


class ChannelStatus(Base, TimestampMixin):
    __tablename__ = "channel_status"

    cs_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.channel_id"), nullable=False)
    status_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    status_code: Mapped[str] = mapped_column(String(20), nullable=False)
    last_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    last_severity: Mapped[Optional[str]] = mapped_column(String(20))
    last_reading_id: Mapped[Optional[int]] = mapped_column(BigInteger)


class ActiveAlarm(Base):
    __tablename__ = "active_alarms"

    alarm_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.channel_id"), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    trigger_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    trigger_reading_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("normalized_readings.reading_id")
    )
    alarm_state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    alarm_message: Mapped[Optional[str]] = mapped_column(String(500))
    requires_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    acknowledged_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    ack_comment: Mapped[Optional[str]] = mapped_column(String(1000))
    ack_signature_id: Mapped[Optional[int]] = mapped_column(Integer)
    cleared_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    escalated_at_utc: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))

    channel: Mapped["Channel"] = relationship("Channel")  # type: ignore[name-defined]
    history: Mapped[list["AlarmHistory"]] = relationship(
        "AlarmHistory", back_populates="alarm"
    )


class AlarmHistory(Base, TimestampMixin):
    """IMMUTABLE — protected by DDL trigger trg_alarm_history_immutable."""
    __tablename__ = "alarm_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("active_alarms.alarm_id"), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    previous_state: Mapped[Optional[str]] = mapped_column(String(20))
    new_state: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    actor_username: Mapped[Optional[str]] = mapped_column(String(50))
    comment: Mapped[Optional[str]] = mapped_column(String(1000))
    reading_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    severity_level: Mapped[Optional[str]] = mapped_column(String(20))
    signature_id: Mapped[Optional[int]] = mapped_column(Integer)

    alarm: Mapped["ActiveAlarm"] = relationship("ActiveAlarm", back_populates="history")


class HeartbeatLog(Base, TimestampMixin):
    __tablename__ = "heartbeat_log"

    heartbeat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    beat_at_utc: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    ntp_offset_ms: Mapped[Optional[int]] = mapped_column(Integer)
    is_ntp_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sequence_num: Mapped[Optional[int]] = mapped_column(BigInteger)
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
