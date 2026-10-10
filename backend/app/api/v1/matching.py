import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_employer, get_db
from app.models.user import User
from app.schemas.matching import (
    CandidateMatchItem,
    MatchingCandidatesResponse,
)
from app.schemas.employer_workspace import (
    CandidateReviewMessageCreate,
    CandidateReviewResponse,
    CandidateReviewUpdate,
)
from app.services.matching_service import matching_service
from app.services.employer_workspace_service import employer_workspace_service

router = APIRouter(prefix="/matching", tags=["Reverse Matching & Candidate Bank"])


@router.get(
    "/for-need/{need_id}",
    response_model=MatchingCandidatesResponse,
    summary="Обратный подбор кандидатов под конкретную потребность работодателя",
)
async def match_candidates(
    need_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await matching_service.match_candidates_for_need(db, need_id, current_user)


@router.get(
    "/search",
    response_model=list[CandidateMatchItem],
    summary="Поиск и фильтрация по банку кандидатов с подтвержденными категориями",
)
async def search_candidates(
    specialization: str | None = Query(None, description="Специализация"),
    grade: str | None = Query(None, description="Подтвержденный грейд (junior, middle, senior, lead)"),
    stack: str | None = Query(None, description="Фильтр по стеку или технологиям (например: Python, PostgreSQL)"),
    skill: str | None = Query(None, max_length=100, description="Навык или технология из стека"),
    work_format: str | None = Query(None, description="Формат работы"),
    city: str | None = Query(None, description="Город"),
    education_level: str | None = Query(None, description="Уровень образования"),
    university_course_group: str | None = Query(None, pattern="^(junior|senior)$", description="Младшие (1–2) или старшие (3+) курсы"),
    age_min: int | None = Query(None, ge=14, le=100, description="Минимальный примерный возраст по году рождения"),
    age_max: int | None = Query(None, ge=14, le=100, description="Максимальный примерный возраст по году рождения"),
    fsp_only: bool = Query(False, description="Только спортсмены реестра ФСП"),
    verified_only: bool = Query(False, description="Совместимость со старым клиентом: выдача всегда ограничена подтверждёнными профилями"),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await matching_service.search_candidates(
        db=db,
        specialization=specialization,
        grade=grade,
        stack=stack or skill,
        skill=skill,
        work_format=work_format,
        city=city,
        education_level=education_level,
        university_course_group=university_course_group,
        age_min=age_min,
        age_max=age_max,
        fsp_only=fsp_only,
        verified_only=verified_only,
    )


@router.get(
    "/candidates/{candidate_id}/review",
    response_model=CandidateReviewResponse,
    summary="Внутренняя HR-карточка кандидата",
)
async def get_candidate_review(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.get_candidate_review(db, current_user, candidate_id)


@router.put(
    "/candidates/{candidate_id}/review",
    response_model=CandidateReviewResponse,
    summary="Обновление внутренней HR-карточки кандидата",
)
async def update_candidate_review(
    candidate_id: uuid.UUID,
    request: CandidateReviewUpdate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.update_candidate_review(db, current_user, candidate_id, request)


@router.post(
    "/candidates/{candidate_id}/review/messages",
    response_model=CandidateReviewResponse,
    summary="Добавить внутреннее сообщение по кандидату",
)
async def add_candidate_review_message(
    candidate_id: uuid.UUID,
    request: CandidateReviewMessageCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.add_candidate_review_message(
        db, current_user, candidate_id, request.body
    )
