import uuid
from pydantic import BaseModel, EmailStr, Field
from app.core.constants import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.CANDIDATE


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=64)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: uuid.UUID
    email: str
    is_verified: bool
    onboarding_completed: bool


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    profile: dict | None = None
