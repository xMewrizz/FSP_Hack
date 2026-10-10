import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate, get_current_reviewer, get_db
from app.models.user import User
from app.schemas.testing import (
    GradeAssessmentResponse,
    AdditionalSkillTestResponse,
    OpenQuestionResponse,
    OpenQuestionReviewRequest,
    OpenQuestionSubmissionResponse,
    OpenQuestionSubmitRequest,
    TestingCatalogResponse,
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
)
from app.core.assessment_catalog import get_testing_catalog
from app.services.open_question_service import (
    get_candidate_submissions,
    get_pending_open_submissions,
    get_public_open_questions,
    review_open_submission,
    retry_open_submission_evaluation,
    submit_open_question_answer,
)
from app.core.open_question_bank import get_open_question_by_code
from app.core.code_sandbox.schemas import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
)
from app.services.code_sandbox_service import code_sandbox_service
from app.services.roadmap_service import roadmap_service
from app.services.testing_service import testing_service

router = APIRouter(prefix="/testing", tags=["Testing & Skill Verification"])



@router.get(
    "/catalog",
    response_model=TestingCatalogResponse,
    summary="Каталог поддерживаемых специализаций, языков и тестов (B-39)",
)
async def get_catalog():
    return get_testing_catalog()


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
    "/open-questions",
    response_model=list[OpenQuestionResponse],
    summary="Список доступных открытых вопросов и заданий с кодом",
)
async def list_open_questions(specialization: str | None = None, grade: str | None = None):
    return get_public_open_questions(specialization, grade)


@router.get(
    "/open-questions/{code}",
    response_model=OpenQuestionResponse,
    summary="Получить открытый вопрос по коду",
)
async def get_open_question(code: str):
    q = get_open_question_by_code(code)
    if not q:
        raise HTTPException(status_code=404, detail="Открытый вопрос не найден")
    return {
        "code": q["code"],
        "title": q["title"],
        "specialization": q["specialization"],
        "grade": q["grade"],
        "question_type": q["question_type"],
        "skill": q.get("skill", ""),
        "question_text": q["question_text"],
        "rubric_criteria": q["rubric_criteria"],
    }


@router.post(
    "/open-questions/{code}/submit",
    response_model=OpenQuestionSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить решение открытого вопроса на проверку",
)
async def submit_open_question(
    code: str,
    data: OpenQuestionSubmitRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Профиль кандидата не найден")
    try:
        return await submit_open_question_answer(
            db=db,
            user=current_user,
            profile=profile,
            question_code=code,
            answer_text=data.answer_text,
            assessment_id=data.assessment_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/open-submissions",
    response_model=list[OpenQuestionSubmissionResponse],
    summary="Список отправленных кандидатом решений открытых вопросов",
)
async def list_candidate_open_submissions(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Профиль кандидата не найден")
    return await get_candidate_submissions(db, profile.id)


@router.get(
    "/open-submissions/pending-review",
    response_model=list[OpenQuestionSubmissionResponse],
    summary="Очередь открытых решений, требующих проверки экспертом (B-27)",
)
async def list_pending_open_submissions(
    current_user: User = Depends(get_current_reviewer),
    db: AsyncSession = Depends(get_db),
):
    return await get_pending_open_submissions(db)


@router.post(
    "/open-submissions/{submission_id}/retry-evaluation",
    response_model=OpenQuestionSubmissionResponse,
    summary="Повторить автоматическую проверку сохранённого ответа",
)
async def retry_open_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await retry_open_submission_evaluation(db, current_user, submission_id)


@router.post(
    "/open-submissions/{submission_id}/review",
    response_model=OpenQuestionSubmissionResponse,
    summary="Экспертная проверка и утверждение оценки открытого задания (B-27)",
)
async def review_submission(
    submission_id: uuid.UUID,
    data: OpenQuestionReviewRequest,
    current_user: User = Depends(get_current_reviewer),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await review_open_submission(
            db=db,
            submission_id=submission_id,
            reviewer_id=current_user.id,
            score=data.score,
            passed=data.passed,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



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


@router.post(
    "/code-sandbox/execute",
    response_model=SandboxExecutionResponse,
    summary="Проверить код в отдельном изолированном исполнителе (B-25)",
)
async def execute_code_sandbox(
    data: SandboxExecutionRequest,
    current_user: User = Depends(get_current_candidate),
):
    try:
        return await code_sandbox_service.execute(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post(
    "/open-questions/{code}/test-run",
    response_model=SandboxExecutionResponse,
    summary="Пробный запуск решения задачи с кодом (B-25)",
)
async def test_run_open_question_code(
    code: str,
    data: SandboxExecutionRequest,
    current_user: User = Depends(get_current_candidate),
):
    q = get_open_question_by_code(code)
    if not q:
        raise HTTPException(status_code=404, detail="Открытый вопрос не найден")
    try:
        return await code_sandbox_service.evaluate_question_code(
            question_code=code,
            candidate_code=data.code,
            timeout_seconds=data.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


