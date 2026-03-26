"""
Users API — ADMIN-only CRUD for user accounts.
All mutations are captured by AuditMiddleware automatically.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_role
from app.models.master import User

router = APIRouter(prefix="/users", tags=["Users"])
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ROLES = {"ADMIN", "OPERATOR", "VIEWER", "EMISSIONS", "DEVELOPER"}


class UserOut(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str
    role: str
    is_active: bool
    is_locked: bool
    failed_login_count: int
    last_login_at: Optional[datetime]
    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    role: str
    password: str = Field(..., min_length=12)


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


@router.get("", response_model=list[UserOut])
async def list_users(
    user: CurrentUser,
    _: None = require_role("ADMIN"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.username))
    return list(result.scalars().all())


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: CreateUserRequest,
    user: CurrentUser,
    _: None = require_role("ADMIN"),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in _ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {_ROLES}")

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = User(
        username=body.username,
        full_name=body.full_name,
        email=body.email,
        role=body.role,
        hashed_password=_pwd.hash(body.password),
        is_active=True,
        is_locked=False,
        failed_login_count=0,
        created_by=user.user_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    user: CurrentUser,
    _: None = require_role("ADMIN"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return target


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    user: CurrentUser,
    _: None = require_role("ADMIN"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is not None:
        target.is_active = body.is_active
    if body.role is not None:
        if body.role not in _ROLES:
            raise HTTPException(status_code=422, detail=f"Invalid role")
        target.role = body.role
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.email is not None:
        target.email = body.email

    await db.commit()
    await db.refresh(target)
    return target


@router.post("/{user_id}/unlock", response_model=UserOut)
async def unlock_user(
    user_id: int,
    user: CurrentUser,
    _: None = require_role("ADMIN"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.failed_login_count = 0
    target.is_locked = False
    await db.commit()
    await db.refresh(target)
    return target
