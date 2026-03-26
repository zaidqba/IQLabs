"""
IQ-RAD FastAPI Application
Entry point: uvicorn app.main:app

GMP/CFR Compliance Features:
- AuditMiddleware: every request logged to audit_trail
- JWT authentication with session blacklisting
- RBAC on all endpoints
- Electronic signature service for regulated actions
- Immutable data storage via DB triggers
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.exceptions import (
    AuthenticationError,
    InsufficientPermissionsError,
    ResourceNotFoundError,
)
from app.core.logging import configure_logging, get_logger
from app.services.ingestion_service import ingestion_service

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

_ingestion_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB, start ingestion pipeline. Shutdown: stop cleanly."""
    global _ingestion_task
    logger.info("iq_rad_starting", extra={"version": settings.app_version, "env": settings.environment})

    # Verify database
    db_ok = await check_database_connection()
    if not db_ok:
        logger.error("database_connection_failed")
        raise RuntimeError("Cannot connect to database — IQ-RAD cannot start")

    logger.info("database_connected")

    # Start ingestion pipeline as background task
    _ingestion_task = asyncio.create_task(ingestion_service.run())
    logger.info("ingestion_pipeline_started")

    yield

    # Shutdown
    logger.info("iq_rad_stopping")
    await ingestion_service.stop()
    if _ingestion_task:
        _ingestion_task.cancel()
        try:
            await _ingestion_task
        except asyncio.CancelledError:
            pass
    logger.info("iq_rad_stopped")


app = FastAPI(
    title="IQ-RAD — Radiation Monitoring System",
    description=(
        "IQLabs AI Ecosystem Radiation Monitoring System. "
        "GMP/CFR compliant per 21 CFR Part 212, 21 CFR Part 11, 10 CFR Part 20. "
        "Connects to Rotem WebiSmarts devices."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(AuditMiddleware)

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/health", tags=["System"])
async def health_check():
    """System health check — no auth required."""
    db_ok = await check_database_connection()
    from app.core.ntp_sync import get_ntp_offset_ms, is_ntp_valid
    from app.services.websocket_service import ws_manager
    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.app_version,
        "database": "connected" if db_ok else "disconnected",
        "ntp_valid": is_ntp_valid(),
        "ntp_offset_ms": get_ntp_offset_ms(),
        "ws_clients": ws_manager.connection_count,
        "ingestion_running": ingestion_service._running,
    }


# ─── Exception Handlers ───────────────────────────────────────────────────────
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(InsufficientPermissionsError)
async def perm_error_handler(request: Request, exc: InsufficientPermissionsError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(ResourceNotFoundError)
async def not_found_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
