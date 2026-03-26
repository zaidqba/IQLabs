"""
IQ-RAD Audit Middleware and Audit Trail Helpers
Satisfies 21 CFR Part 11 §11.10(e): computer-generated, time-stamped audit trail
for all operator actions that create, modify, or delete electronic records.

Every API request/response pair is logged to audit_trail.
Audit writes use a dedicated DB session independent of the request transaction,
ensuring audit records are written even when the main transaction rolls back.
"""
import time
import uuid
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Endpoints excluded from per-request audit (to prevent flooding) ─────────
_AUDIT_EXCLUDED_PATHS = {
    "/health",
    "/api/v1/readings/latest",   # High-frequency polling; sampled instead
    "/favicon.ico",
}

# ─── Action type mapping from HTTP method + path patterns ────────────────────
_METHOD_ACTION_MAP = {
    "GET": "READ",
    "POST": "CREATE",
    "PATCH": "UPDATE",
    "PUT": "UPDATE",
    "DELETE": "DELETE",
}

_PATH_ACTION_OVERRIDES = {
    "/auth/login": "LOGIN",
    "/auth/logout": "LOGOUT",
    "/auth/refresh": "TOKEN_REFRESH",
    "/acknowledge": "ACK_ALARM",
    "/sign": "SIGN",
    "/approve": "APPROVE",
    "/review": "REVIEW",
    "/generate": "REPORT_GENERATE",
    "/thresholds": "THRESHOLD_CHANGE",
    "/export": "EXPORT",
}


def _derive_action_type(method: str, path: str) -> str:
    for fragment, action in _PATH_ACTION_OVERRIDES.items():
        if fragment in path:
            return action
    return _METHOD_ACTION_MAP.get(method.upper(), "READ")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every request and writes an audit_trail record.
    User context is extracted from JWT claims attached to request.state
    by the authentication dependency.
    Runs a best-effort fire-and-forget audit write — errors are logged
    but do NOT fail the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.monotonic()

        # Process the request
        response = await call_next(request)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id

        path = request.url.path
        if path not in _AUDIT_EXCLUDED_PATHS:
            await self._write_audit(request, response, request_id, duration_ms)

        return response

    async def _write_audit(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: int,
    ) -> None:
        try:
            user_id: Optional[int] = getattr(request.state, "user_id", None)
            user_name: Optional[str] = getattr(request.state, "user_name", None)
            user_role: Optional[str] = getattr(request.state, "user_role", None)
            session_id: Optional[str] = getattr(request.state, "session_id", None)
            action_detail: Optional[str] = getattr(request.state, "audit_detail", None)

            ip = request.headers.get("X-Forwarded-For") or (
                request.client.host if request.client else None
            )

            result_status = "SUCCESS" if response.status_code < 400 else (
                "DENIED" if response.status_code == 403 else "FAILURE"
            )

            # Lazy import to avoid circular imports with models
            from app.core.database import get_audit_db
            from app.models.compliance import AuditTrail

            async with get_audit_db() as db:
                entry = AuditTrail(
                    user_id=user_id,
                    user_name=user_name,
                    user_role=user_role,
                    session_id=session_id,
                    ip_address=ip,
                    http_method=request.method,
                    endpoint=request.url.path,
                    action_type=_derive_action_type(request.method, request.url.path),
                    action_detail=action_detail,
                    result_code=response.status_code,
                    result_status=result_status,
                    duration_ms=duration_ms,
                    request_id=request_id,
                )
                db.add(entry)
        except Exception as exc:
            logger.warning("audit_write_failed", extra={"error": str(exc)})


def set_audit_detail(request: Request, detail: str) -> None:
    """
    Call from route handlers to attach before/after JSON diff to the
    current request's audit record.
    Usage: set_audit_detail(request, json.dumps({"before": ..., "after": ...}))
    """
    request.state.audit_detail = detail
