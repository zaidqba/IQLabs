"""
IQ-RAD Security: JWT, bcrypt, RBAC, Electronic Signatures
Implements 21 CFR Part 11 §11.200(a)(1) two-component signature requirement.
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    InsufficientPermissionsError,
)

settings = get_settings()

# ─── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ─── RBAC ─────────────────────────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "VIEWER": {
        "read:readings", "read:alarms", "read:reports",
        "read:channels", "read:devices",
    },
    "EMISSIONS": {
        "read:*",
        "write:calibration", "sign:calibration",
    },
    "OPERATOR": {
        "read:*",
        "write:alarms", "sign:alarms",
        "write:reports", "sign:reports",
        "write:reviews", "sign:reviews",
        "write:thresholds", "sign:thresholds",
    },
    "DEVELOPER": {
        "read:*", "read:raw_data", "read:audit",
    },
    "ADMIN": {"*"},
}


def has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        return True
    if permission in perms:
        return True
    # Check wildcard namespace: read:* grants read:anything
    namespace = permission.split(":")[0] + ":*"
    return namespace in perms


# ─── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(user_id: int, username: str, role: str) -> tuple[str, str]:
    """Returns (access_token, session_id)."""
    session_id = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "session_id": session_id,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, session_id


def create_refresh_token(user_id: int, session_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.jwt_refresh_expire_hours
    )
    payload = {
        "sub": str(user_id),
        "session_id": session_id,
        "token_type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises AuthenticationError on failure."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc


# ─── Electronic Signatures (21 CFR Part 11 §11.50, §11.200) ──────────────────
def compute_signature_hash(
    user_id: int,
    item_type: str,
    item_id: str,
    timestamp_utc: datetime,
) -> str:
    """
    Compute a tamper-evident SHA-256 HMAC hash for an electronic signature.
    Components: user_id | item_type | item_id | ISO timestamp | HMAC_SECRET
    """
    message = f"{user_id}|{item_type}|{item_id}|{timestamp_utc.isoformat()}"
    return hmac.new(
        settings.hmac_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_signature_hash(
    user_id: int,
    item_type: str,
    item_id: str,
    timestamp_utc: datetime,
    stored_hash: str,
) -> bool:
    expected = compute_signature_hash(user_id, item_type, item_id, timestamp_utc)
    return hmac.compare_digest(expected, stored_hash)
