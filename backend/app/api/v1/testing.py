import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate, get_db
from app.models.user import User
from app.schemas.testing import (
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
)
from app.services.testing_service import testing_service

router = APIRouter(prefix="/testing", tags=["Testing & Skill Verification"])


@router.post(
    "/start",
    response_model=TestStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Начать тестирование для подтверждения грейда",
)
async def start_test(
    data: TestStartRequest = TestStartRequest(),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await testing_service.start_test(db, current_user, data)


@router.post(
    "/{session_id}/submit",
    response_model=TestResultResponse,
    summary="Отправить ответы на тест и получить подтвержденный грейд",
)
async def submit_test(
    session_id: uuid.UUID,
    data: TestSubmitRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await testing_service.submit_test(db, current_user, session_id, data)


@router.get(
    "/history",
    response_model=list[TestSessionHistoryItem],
    summary="История тестирований кандидата",
)
async def get_test_history(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await testing_service.get_history(db, current_user)


@router.get(
    "/{session_id}",
    response_model=TestResultResponse,
    summary="Детальные результаты сессии тестирования",
)
async def get_test_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await testing_service.get_session(db, current_user, session_id)
