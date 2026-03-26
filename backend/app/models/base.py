"""SQLAlchemy declarative base and shared mixins."""
from datetime import datetime

from sqlalchemy import DATETIME, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at to any model. created_at is set by DB default (SYSUTCDATETIME)."""
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(timezone=False),
        server_default=func.SYSUTCDATETIME(),
        nullable=False,
    )
