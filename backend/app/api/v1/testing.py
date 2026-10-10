import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate, get_current_reviewer, get_db
from app.models.candidate import CandidateProfile
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
    CandidateSpecializationTrackRequest,
    CandidateSpecializationTrackResponse,
)
from app.core.assessment_catalog import get_testing_catalog
from app.services.open_question_service import (
    get_candidate_submissions,
    get_pending_open_submissions,
    get_public_open_questions,
    review_open_submission,
    retry_open_submission_evaluation,
    queue_open_question_answer,
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


async def _require_test_confidentiality_consent(db: AsyncSession, user: User) -> None:
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=400, detail="Профиль кандидата не найден")
    if not profile.agreed_test_confidentiality:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Перед началом тестирования необходимо принять условия конфиденциальности заданий.",
        )


@router.get(
    "/catalog",
    response_model=TestingCatalogResponse,
    summary="Каталог поддерживаемых специализаций, языков и тестов (B-39)",
)
async def get_catalog():
    return get_testing_catalog()


@router.get("/specializations", response_model=list[CandidateSpecializationTrackResponse])
async def candidate_specializations(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.list_specializations(db, current_user)


@router.post(
    "/specializations",
    response_model=CandidateSpecializationTrackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_candidate_specialization(
    data: CandidateSpecializationTrackRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.request_specialization(db, current_user, data.specialization)


@router.get("/additional", response_model=list[AdditionalSkillTestResponse])
async def available_additional_tests(
    specialization: str | None = None,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.available_additional(db, current_user, specialization)


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
    await _require_test_confidentiality_consent(db, current_user)
    if data.target_grade is None:
        raise HTTPException(400, "Укажите уровень дополнительного теста")
    return await roadmap_service.start_additional(
        db, current_user, skill_code, data.target_grade.value, data.specialization,
    )


@router.post("/roadmap", response_model=GradeAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def start_roadmap(
    data: TestStartRequest = TestStartRequest(),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    await _require_test_confidentiality_consent(db, current_user)
    return await roadmap_service.start(db, current_user, data)


@router.get("/roadmap/current", response_model=GradeAssessmentResponse | None)
async def current_roadmap(
    specialization: str | None = None,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await roadmap_service.latest(db, current_user, specialization)


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
    await _require_test_confidentiality_consent(db, current_user)
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
    await _require_test_confidentiality_consent(db, current_user)
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
    await _require_test_confidentiality_consent(db, current_user)
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
async def list_open_questions(
    specialization: str | None = None,
    grade: str | None = None,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    await _require_test_confidentiality_consent(db, current_user)
    return get_public_open_questions(specialization, grade)


@router.get(
    "/open-questions/{code}",
    response_model=OpenQuestionResponse,
    summary="Получить открытый вопрос по коду",
)
async def get_open_question(
    code: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    await _require_test_confidentiality_consent(db, current_user)
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
    await _require_test_confidentiality_consent(db, current_user)
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


@router.post(
    "/open-questions/{code}/queue",
    response_model=OpenQuestionSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Сохранить ответ и поставить его в очередь проверки",
)
async def queue_open_question(
    code: str,
    data: OpenQuestionSubmitRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(400, "Профиль кандидата не найден")
    return await queue_open_question_answer(
        db, current_user, profile, code, data.answer_text, data.assessment_id,
    )


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
    "/open-submissions/{submission_id}/queue-retry",
    response_model=OpenQuestionSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Повторить проверку сохранённого ответа",
)
async def queue_retry_open_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.test import GradeAssessment, OpenQuestionSubmission
    from app.services.roadmap_service import assessment_is_expired
    submission = await db.scalar(select(OpenQuestionSubmission).where(
        OpenQuestionSubmission.id == submission_id,
        OpenQuestionSubmission.user_id == current_user.id,
    ).with_for_update())
    if submission is None:
        raise HTTPException(404, "Ответ не найден")
    if submission.evaluation_status not in ("failed", "manual_review"):
        raise HTTPException(409, "Повторная проверка этого ответа сейчас недоступна")
    assessment = await db.get(GradeAssessment, submission.assessment_id) if submission.assessment_id else None
    if assessment is None or assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
        raise HTTPException(409, "Набор завершён или срок истёк")
    submission.evaluation_status = "queued"
    submission.feedback = ""
    submission.score = 0
    submission.passed = False
    submission.criterion_scores = {}
    submission.needs_manual_review = False
    await db.commit()
    await db.refresh(submission)
    return submission


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
    db: AsyncSession = Depends(get_db),
):
    await _require_test_confidentiality_consent(db, current_user)
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
    db: AsyncSession = Depends(get_db),
):
    await _require_test_confidentiality_consent(db, current_user)
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
