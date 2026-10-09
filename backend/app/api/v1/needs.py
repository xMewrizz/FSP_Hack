import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_employer, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.need import (
    EmployerNeedCreate,
    EmployerNeedResponse,
    EmployerNeedUpdate,
    NeedDraftResponse,
    NeedTextRequest,
)
from app.services.need_service import need_service

router = APIRouter(prefix="/needs", tags=["Employer Needs & Requirements"])


@router.post(
    "/parse",
    response_model=NeedDraftResponse,
    summary="Предложить поля потребности по свободному описанию",
)
async def parse_need_draft(
    data: NeedTextRequest,
    current_user: User = Depends(get_current_employer),
):
    try:
        async with httpx.AsyncClient(timeout=95.0) as client:
            response = await client.post(f"{settings.ML_SERVICE_URL.rstrip('/')}/parse-need", json={"text": data.text})
            response.raise_for_status()
        return NeedDraftResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось получить предложения от модели. Заполните поля вручную.",
        ) from None


@router.post(
    "",
    response_model=EmployerNeedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать потребность в кандидате (запрос на подбор)",
)
async def create_need(
    data: EmployerNeedCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.create_need(db, current_user, data)


@router.get(
    "",
    response_model=list[EmployerNeedResponse],
    summary="Список созданных потребностей компании",
)
async def get_my_needs(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.get_my_needs(db, current_user)


@router.get(
    "/{need_id}",
    response_model=EmployerNeedResponse,
    summary="Получить детали потребности по ID",
)
async def get_need(
    need_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.get_need(db, need_id, current_user)


@router.put(
    "/{need_id}",
    response_model=EmployerNeedResponse,
    summary="Обновить потребность компании",
)
async def update_need(
    need_id: uuid.UUID,
    data: EmployerNeedUpdate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.update_need(db, current_user, need_id, data)


@router.delete(
    "/{need_id}",
    summary="Удалить потребность",
)
async def delete_need(
    need_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await need_service.delete_need(db, current_user, need_id)
