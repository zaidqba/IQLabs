"""Auth request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user_id: int
    username: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)
    signature_password: str  # Re-auth for audit trail


class UserInfo(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_locked: bool

    class Config:
        from_attributes = True
