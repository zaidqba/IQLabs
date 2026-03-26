"""
IQ-RAD FastAPI Dependencies
Provides: get_db, get_current_user, require_role, require_permission
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, InsufficientPermissionsError
from app.core.security import decode_token, has_permission
from app.models.master import TokenBlacklist, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT, check blacklist, load user from DB.
    Attaches user context to request.state for AuditMiddleware.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    session_id = payload.get("session_id")
    if session_id:
        blacklisted = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.session_id == session_id)
        )
        if blacklisted.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been invalidated",
            )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Contact administrator.",
        )

    # Attach to request.state for AuditMiddleware
    request.state.user_id = user.user_id
    request.state.user_name = user.username
    request.state.user_role = user.role
    request.state.session_id = session_id

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """Dependency factory: require one of the specified roles."""
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role} does not have access to this resource",
            )
        return user
    return Depends(_check)


def require_permission(permission: str):
    """Dependency factory: require a specific permission."""
    async def _check(user: CurrentUser) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires '{permission}'",
            )
        return user
    return Depends(_check)
