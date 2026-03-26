"""Aggregate all v1 API routers."""
from fastapi import APIRouter

from app.api.v1 import alarms, audit, auth, calibration, devices, readings, reports, users, ws

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(readings.router)
api_router.include_router(alarms.router)
api_router.include_router(devices.router)
api_router.include_router(audit.router)
api_router.include_router(calibration.router)
api_router.include_router(reports.router)
api_router.include_router(users.router)

# WebSocket (no prefix — mounts at /api/v1/ws/live)
api_router.include_router(ws.router)
