import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_employer, get_db
from app.models.user import User
from app.schemas.matching import (
    CandidateMatchItem,
    MatchingCandidatesResponse,
)
from app.services.matching_service import matching_service

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
    return await matching_service.match_candidates_for_need(db, need_id)


@router.get(
    "/search",
    response_model=list[CandidateMatchItem],
    summary="Поиск и фильтрация по банку кандидатов с подтвержденными категориями",
)
async def search_candidates(
    specialization: str | None = Query(None, description="Специализация"),
    grade: str | None = Query(None, description="Грейд (junior, middle, senior, lead)"),
    work_format: str | None = Query(None, description="Формат работы"),
    city: str | None = Query(None, description="Город"),
    fsp_only: bool = Query(False, description="Только спортсмены реестра ФСП"),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await matching_service.search_candidates(
        db=db,
        specialization=specialization,
        grade=grade,
        work_format=work_format,
        city=city,
        fsp_only=fsp_only,
    )
