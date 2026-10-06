from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendCodeRequest,
    TokenResponse,
    UserMeResponse,
    VerifyEmailRequest,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.register(db, request)


@router.post(
    "/verify-email",
    response_model=TokenResponse,
    summary="Подтверждение email",
)
async def verify_email(
    request: VerifyEmailRequest,
    user_agent: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.verify_email(db, request, user_agent)


@router.post(
    "/resend-code",
    summary="Повторная отправка кода",
)
async def resend_code(
    request: ResendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.resend_code(db, request.email)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
)
async def login(
    request: LoginRequest,
    user_agent: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.login(db, request, user_agent)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление JWT токенов",
)
async def refresh_tokens(
    request: RefreshTokenRequest,
    user_agent: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.refresh_tokens(db, request.refresh_token, user_agent)


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Выход из системы",
)
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    res = await auth_service.logout(db, request.refresh_token)
    return SuccessResponse(message=res["message"])


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Текущий пользователь",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_me(db, current_user)
