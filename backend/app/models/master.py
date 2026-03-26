"""
IQ-RAD Master/Reference Table ORM Models
Sites, Systems, Vendors, Devices, Detectors, Channels, UOM, AlarmProfiles, Users
"""
from datetime import datetime
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Site(Base, TimestampMixin):
    __tablename__ = "sites"

    site_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    nrc_license: Mapped[Optional[str]] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    systems: Mapped[list["System"]] = relationship("System", back_populates="site")


class System(Base, TimestampMixin):
    __tablename__ = "systems"

    system_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.site_id"), nullable=False)
    system_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    system_name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    site: Mapped["Site"] = relationship("Site", back_populates="systems")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="system")


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    vendor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    support_contact: Mapped[Optional[str]] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="vendor")


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    device_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.system_id"), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    device_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    port: Mapped[Optional[int]] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    poll_interval_s: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    connect_timeout_s: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False, default=5.0)
    read_timeout_s: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False, default=8.0)
    firmware_ver: Mapped[Optional[str]] = mapped_column(String(50))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    model_number: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    system: Mapped["System"] = relationship("System", back_populates="devices")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="devices")
    detectors: Mapped[list["Detector"]] = relationship("Detector", back_populates="device")
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="device")


class Detector(Base, TimestampMixin):
    __tablename__ = "detectors"

    detector_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    detector_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    detector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    detector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_number: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100))
    calibration_due: Mapped[Optional[datetime]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="detectors")
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="detector")


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    uom_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uom_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    uom_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    si_conversion: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 10))
    si_unit: Mapped[Optional[str]] = mapped_column(String(20))


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    channel_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    detector_id: Mapped[Optional[int]] = mapped_column(ForeignKey("detectors.detector_id"))
    channel_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rotem_point_id: Mapped[Optional[int]] = mapped_column(Integer)
    rotem_point_name: Mapped[Optional[str]] = mapped_column(String(50))
    rotem_adapter_id: Mapped[Optional[int]] = mapped_column(Integer)
    uom_id: Mapped[int] = mapped_column(ForeignKey("units_of_measure.uom_id"), nullable=False)
    is_stack_detector: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_rate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_dose: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expected_update_s: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    stale_threshold_s: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="channels")
    detector: Mapped[Optional["Detector"]] = relationship("Detector", back_populates="channels")
    uom: Mapped["UnitOfMeasure"] = relationship("UnitOfMeasure")
    alarm_profiles: Mapped[list["AlarmProfile"]] = relationship(
        "AlarmProfile", back_populates="channel"
    )


class AlarmProfile(Base, TimestampMixin):
    __tablename__ = "alarm_profiles"
    __table_args__ = (
        UniqueConstraint("channel_id", "profile_version", name="UQ_profile_channel_version"),
        CheckConstraint(
            "alert_threshold < alarm_threshold AND alarm_threshold < danger_threshold",
            name="CHK_threshold_order",
        ),
    )

    profile_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.channel_id"), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    low_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    alert_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    alarm_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    danger_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high_dose_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    reset_dose_interval_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    effective_from: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    change_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    approved_by: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_signature_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    channel: Mapped["Channel"] = relationship("Channel", back_populates="alarm_profiles")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'OPERATOR', 'VIEWER', 'EMISSIONS', 'DEVELOPER')",
            name="CHK_users_role",
        ),
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DATETIME(timezone=False))
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45))
    password_changed_at: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TokenBlacklist(Base, TimestampMixin):
    __tablename__ = "token_blacklist"

    blacklist_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    invalidated_at: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False), server_default=func.SYSUTCDATETIME(), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(timezone=False), nullable=False)
