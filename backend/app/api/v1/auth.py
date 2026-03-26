"""Auth API endpoints — login, logout, refresh, change password."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.config import get_settings
from app.core.exceptions import AccountLockedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.master import TokenBlacklist, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    ip = request.headers.get("X-Forwarded-For") or (
        request.client.host if request.client else "unknown"
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Contact administrator.",
        )

    if not verify_password(body.password, user.hashed_password):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_failures:
            user.is_locked = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Successful login
    user.failed_login_count = 0
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = ip

    access_token, session_id = create_access_token(user.user_id, user.username, user.role)
    refresh_token = create_refresh_token(user.user_id, session_id)

    request.state.user_id = user.user_id
    request.state.user_name = user.username
    request.state.user_role = user.role
    request.state.session_id = session_id

    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=settings.jwt_access_expire_minutes * 60,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        db.add(TokenBlacklist(
            session_id=session_id,
            user_id=user.user_id,
            reason="LOGOUT",
            expires_at=datetime.now(timezone.utc) + timedelta(
                hours=settings.jwt_refresh_expire_hours
            ),
        ))
        await db.commit()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not available",
        )

    access_token, new_session_id = create_access_token(user.user_id, user.username, user.role)
    new_refresh = create_refresh_token(user.user_id, new_session_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in_seconds=settings.jwt_access_expire_minutes * 60,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: CurrentUser):
    return UserInfo.model_validate(user)
