"""
IQ-RAD Database Engine and Session Management
Uses SQLAlchemy 2.0 async-compatible session factory with SQL Server.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# ─── Engine ───────────────────────────────────────────────────────────────────
# NullPool is used for async to avoid connection leaks in FastAPI
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args={"timeout": 30},
)

# ─── Session Factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_audit_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dedicated session for audit trail writes.
    Uses a separate connection to ensure audit writes are independent
    of the main request transaction — an audit entry should be written
    even if the main transaction rolls back.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Health check: verify database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
