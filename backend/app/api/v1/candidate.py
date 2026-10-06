from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate
from app.core.database import get_db
from app.models.user import User
from app.schemas.candidate import (
    CandidateOnboardingRequest,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
)
from app.schemas.fsp import FSPLinkRequest
from app.services.candidate_service import candidate_service

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.post(
    "/onboarding",
    response_model=CandidateProfileResponse,
    summary="Онбординг кандидата",
)
async def complete_onboarding(
    request: CandidateOnboardingRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.complete_onboarding(db, current_user, request)


@router.get(
    "/profile",
    response_model=CandidateProfileResponse,
    summary="Профиль кандидата",
)
async def get_my_profile(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.get_profile(db, current_user)


@router.put(
    "/profile",
    response_model=CandidateProfileResponse,
    summary="Обновление профиля кандидата",
)
async def update_my_profile(
    request: CandidateProfileUpdateRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.update_profile(db, current_user, request)


@router.post(
    "/link-fsp",
    response_model=CandidateProfileResponse,
    summary="Привязка ФСП ID",
)
async def link_fsp_id(
    request: FSPLinkRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.link_fsp_id(db, current_user, request.fsp_id)
