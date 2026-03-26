"""
User Service — CRUD for user accounts.
Password hashing delegated to core/security.py.
Account lockout after max_failures consecutive failures.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.master import User
from app.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    async def get_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def list_users(self, db: AsyncSession) -> list[User]:
        result = await db.execute(select(User).order_by(User.username))
        return list(result.scalars().all())

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        full_name: str,
        email: str,
        role: str,
        password: str,
    ) -> User:
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            role=role,
            password_hash=_pwd.hash(password),
            is_active=True,
            failed_login_count=0,
        )
        db.add(user)
        await db.flush()
        return user

    async def update_user(
        self,
        db: AsyncSession,
        user: User,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> User:
        if is_active is not None:
            user.is_active = is_active
        if role is not None:
            user.role = role
        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email
        await db.flush()
        return user

    async def unlock_user(self, db: AsyncSession, user: User) -> User:
        user.failed_login_count = 0
        await db.flush()
        return user

    async def record_login_success(self, db: AsyncSession, user: User) -> None:
        from datetime import timezone, datetime
        user.failed_login_count = 0
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

    async def record_login_failure(self, db: AsyncSession, user: User) -> None:
        user.failed_login_count = (user.failed_login_count or 0) + 1
        await db.flush()

    def is_locked(self, user: User) -> bool:
        return (user.failed_login_count or 0) >= settings.login_max_failures


user_service = UserService()
