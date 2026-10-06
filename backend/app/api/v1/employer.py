from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_employer
from app.core.database import get_db
from app.models.user import User
from app.schemas.employer import (
    EmployerOnboardingRequest,
    EmployerProfileResponse,
    EmployerProfileUpdateRequest,
)
from app.services.employer_service import employer_service

router = APIRouter(tags=["Employer"])


@router.post(
    "/onboarding",
    response_model=EmployerProfileResponse,
    summary="Онбординг работодателя",
)
async def complete_onboarding(
    request: EmployerOnboardingRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.complete_onboarding(db, current_user, request)


@router.get(
    "/profile",
    response_model=EmployerProfileResponse,
    summary="Профиль компании",
)
async def get_my_profile(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.get_profile(db, current_user)


@router.put(
    "/profile",
    response_model=EmployerProfileResponse,
    summary="Обновление профиля компании",
)
async def update_my_profile(
    request: EmployerProfileUpdateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.update_profile(db, current_user, request)
