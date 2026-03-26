"""
IQ-RAD Electronic Signature Service
Implements 21 CFR Part 11 §11.50, §11.200(a)(1) two-component authentication.

Re-authentication Flow:
1. User has a valid JWT session (first authentication component: identification code)
2. User submits their password again at signature time (second component: password)
3. Backend verifies password via bcrypt (independent of JWT)
4. On success: create electronic_signatures record with SHA-256 hash
5. Bind signature_id to the signed record
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, SignatureError
from app.core.security import compute_signature_hash, verify_password
from app.models.compliance import ElectronicSignature
from app.models.master import User


class SignatureService:
    async def create_signature(
        self,
        db: AsyncSession,
        user_id: int,
        password: str,
        item_type: str,
        item_id: str,
        meaning: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ElectronicSignature:
        """
        Verify user password and create an electronic signature record.
        Raises AuthenticationError if password is incorrect.
        Raises SignatureError if user account is not active.

        This implements the 21 CFR Part 11 §11.200(a)(1) requirement:
        signatures based on passwords shall use at least two distinct
        identification components (the JWT session_id + this password re-entry).
        """
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active or user.is_locked:
            raise SignatureError("User account is not available for signing")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError(
                "Signature authentication failed: incorrect password"
            )

        signed_at = datetime.now(timezone.utc)
        sig_hash = compute_signature_hash(user_id, item_type, item_id, signed_at)

        signature = ElectronicSignature(
            user_id=user_id,
            user_name=user.username,
            user_role=user.role,
            signed_at_utc=signed_at,
            meaning=meaning,
            signed_item_type=item_type,
            signed_item_id=item_id,
            authentication_method="PASSWORD",
            ip_address=ip_address,
            session_id=session_id,
            signature_hash=sig_hash,
            is_valid=True,
        )
        db.add(signature)
        await db.flush()
        return signature
