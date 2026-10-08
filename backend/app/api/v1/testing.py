import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate, get_db
from app.models.user import User
from app.schemas.testing import (
    GradeAssessmentResponse,
    AdditionalSkillTestResponse,
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
)
from app.services.roadmap_service import roadmap_service
from app.services.testing_service import testing_service

router = APIRouter(prefix="/testing", tags=["Testing & Skill Verification"])


@router.get("/additional", response_model=list[AdditionalSkillTestResponse])
async def available_additional_tests(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.available_additional(db, current_user)


@router.post(
    "/additional/{skill_code}/start",
    response_model=TestStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_additional_test(
    skill_code: str,
    data: TestStartRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if data.target_grade is None:
        raise HTTPException(400, "Укажите уровень дополнительного теста")
    return await roadmap_service.start_additional(
        db, current_user, skill_code, data.target_grade.value,
    )


@router.post("/roadmap", response_model=GradeAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def start_roadmap(
    data: TestStartRequest = TestStartRequest(),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.start(db, current_user, data)


@router.get("/roadmap/current", response_model=GradeAssessmentResponse | None)
async def current_roadmap(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.latest(db, current_user)


@router.get("/roadmap/{assessment_id}", response_model=GradeAssessmentResponse)
async def get_roadmap(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.get(db, current_user, assessment_id)


@router.post("/roadmap/{assessment_id}/stop", response_model=GradeAssessmentResponse)
async def stop_roadmap(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.stop(db, current_user, assessment_id)


@router.post(
    "/roadmap/{assessment_id}/skills/{skill_code}/start",
    response_model=TestStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_roadmap_skill(
    assessment_id: uuid.UUID,
    skill_code: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.start_skill(db, current_user, assessment_id, skill_code)


@router.post(
    "/start",
    response_model=TestStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Начать общий тест прежнего формата без присвоения грейда",
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
    summary="Отправить ответы на тест и получить результат",
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
