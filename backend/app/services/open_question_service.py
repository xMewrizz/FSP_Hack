from typing import Any
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.code_sandbox.run_job import SUPPORTED_QUESTIONS
from app.core.open_question_bank import (
    OPEN_QUESTIONS,
    get_open_question_by_code,
)
from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment, OpenQuestionSubmission, TestSession
from app.models.user import User


def get_public_open_questions(specialization: str | None = None, grade: str | None = None) -> list[dict[str, Any]]:
    questions = OPEN_QUESTIONS
    if specialization:
        questions = [q for q in questions if q["specialization"] == specialization]
    if grade:
        questions = [q for q in questions if q["grade"] == grade.lower()]
    return [
        {
            "code": q["code"],
            "title": q["title"],
            "specialization": q["specialization"],
            "grade": q["grade"],
            "question_type": q["question_type"],
            "skill": q.get("skill", ""),
            "question_text": q["question_text"],
            "rubric_criteria": q["rubric_criteria"],
            "critical_criteria": q["critical_criteria"],
        }
        for q in questions
    ]


def _local_fallback_eval(
    question: dict[str, Any], answer_text: str
) -> dict[str, Any]:
    """Недоступный ML-сервис не даёт оснований выставлять балл."""
    return {
        "score": 0.0,
        "passed": False,
        "feedback": "Автоматическая проверка недоступна. Ответ пока не оценён; повторите проверку позже.",
        "criterion_scores": {},
        "evaluator": "fallback_heuristic",
        "needs_manual_review": True,
    }


async def _evaluate_with_ml(
    question: dict[str, Any], answer_text: str, client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    payload = {
        "question_code": question["code"],
        "question_type": question["question_type"],
        "question_text": question["question_text"],
        "reference_solution": question["reference_solution"],
        "rubric_criteria": question["rubric_criteria"],
        "critical_criteria": question.get("critical_criteria", []),
        "candidate_answer": answer_text,
    }
    own_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=135.0)
    try:
        response = await client.post(f"{settings.ML_SERVICE_URL.rstrip('/')}/evaluate-open-answer", json=payload)
        if response.status_code == 200:
            return response.json()
        return _local_fallback_eval(question, answer_text)
    except (httpx.HTTPError, ValueError):
        return _local_fallback_eval(question, answer_text)
    finally:
        if own_client:
            await client.aclose()


async def evaluate_open_answer(
    question: dict[str, Any], answer_text: str, client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Combine the rubric with functional tests when a code task has a runnable contract."""
    if question["code"] not in SUPPORTED_QUESTIONS or question["question_type"] != "code":
        return await _evaluate_with_ml(question, answer_text, client)

    from app.services.code_sandbox_service import UnsupportedSandboxQuestion, code_sandbox_service

    try:
        sandbox = await code_sandbox_service.evaluate_question_code(question["code"], answer_text)
    except UnsupportedSandboxQuestion as exc:
        raise RuntimeError("Изолированная проверка не поддерживает это задание") from exc
    if sandbox.tests_total <= 0:
        raise RuntimeError("Изолированная проверка не вернула тесты")
    model = await _evaluate_with_ml(question, answer_text, client)
    score = round(min(float(model["score"]), sandbox.score), 2)
    criteria = dict(model.get("criterion_scores", {}))
    criteria["Функциональные тесты"] = sandbox.score
    feedback = model.get("feedback", "").strip()
    if sandbox.status == "syntax_error":
        execution_feedback = sandbox.feedback or "Синтаксическая ошибка в решении."
    else:
        execution_feedback = f"Код прошёл {sandbox.tests_passed} из {sandbox.tests_total} проверок."
    return {
        **model,
        "score": score,
        "passed": score >= 0.7,
        "feedback": f"{execution_feedback} {feedback}".strip(),
        "criterion_scores": criteria,
        "evaluator": f"{model['evaluator']}+code_sandbox_b25",
    }


async def submit_open_question_answer(
    db: AsyncSession,
    user: User,
    profile: CandidateProfile,
    question_code: str,
    answer_text: str,
    assessment_id: uuid.UUID | None = None,
    client: httpx.AsyncClient | None = None,
) -> OpenQuestionSubmission:
    question = get_open_question_by_code(question_code)
    if not question:
        raise ValueError(f"Открытый вопрос с кодом {question_code} не найден")
    if not answer_text.strip():
        raise HTTPException(400, "Напишите ответ перед отправкой")
    assessment = None
    if assessment_id is not None:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ))
        if assessment is None:
            raise HTTPException(404, "Набор тестов не найден")
        from app.services.roadmap_service import assessment_is_expired
        if assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
            raise HTTPException(409, "Срок набора истёк или он уже завершён")
        if question_code not in assessment.scoring_policy.get("open_codes", []):
            raise HTTPException(400, "Задание не входит в этот набор")
        existing = await db.scalar(select(OpenQuestionSubmission.id).where(
            OpenQuestionSubmission.assessment_id == assessment_id,
            OpenQuestionSubmission.question_code == question_code,
        ))
        if existing:
            raise HTTPException(409, "Ответ на это задание уже отправлен")

    try:
        eval_result = await evaluate_open_answer(question, answer_text, client)
    except RuntimeError as exc:
        raise HTTPException(503, "Проверка кода сейчас недоступна. Ответ не отправлен; попробуйте позже.") from exc

    evaluator = str(eval_result.get("evaluator", ""))
    if assessment_id is not None and evaluator.startswith("fallback_heuristic"):
        raise HTTPException(
            503,
            "Проверка ответа сейчас недоступна. Ответ не отправлен; сохраните его текст и попробуйте позже.",
        )

    if assessment_id is not None:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ).with_for_update())
        from app.services.roadmap_service import assessment_is_expired
        if assessment is None or assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
            raise HTTPException(409, "Срок набора истёк или он уже завершён")
        existing = await db.scalar(select(OpenQuestionSubmission.id).where(
            OpenQuestionSubmission.assessment_id == assessment_id,
            OpenQuestionSubmission.question_code == question_code,
        ))
        if existing:
            raise HTTPException(409, "Ответ на это задание уже отправлен")

    submission = OpenQuestionSubmission(
        user_id=user.id,
        candidate_profile_id=profile.id,
        assessment_id=assessment_id,
        question_code=question["code"],
        question_type=question["question_type"],
        answer_text=answer_text,
        score=eval_result.get("score", 0.0),
        passed=eval_result.get("passed", False),
        feedback=eval_result.get("feedback", ""),
        criterion_scores=eval_result.get("criterion_scores", {}),
        evaluator=eval_result.get("evaluator", "fallback_heuristic"),
        needs_manual_review=eval_result.get("needs_manual_review", True),
        evaluation_status="manual_review" if eval_result.get("needs_manual_review", True) else "completed",
    )
    db.add(submission)
    await db.flush()
    if assessment is not None:
        from app.services.roadmap_service import roadmap_service
        completed_sessions = (await db.execute(select(TestSession).where(
            TestSession.assessment_id == assessment.id, TestSession.status == "completed",
        ).order_by(TestSession.created_at.desc()))).scalars().all()
        if {item.skill_code for item in completed_sessions} >= set(assessment.required_skills):
            await roadmap_service.finish_skill(db, completed_sessions[0], profile)
    await db.commit()
    await db.refresh(submission)
    return submission


async def queue_open_question_answer(
    db: AsyncSession, user: User, profile: CandidateProfile,
    question_code: str, answer_text: str, assessment_id: uuid.UUID | None,
) -> OpenQuestionSubmission:
    """Save the answer before contacting the model so navigation cannot lose it."""
    question = get_open_question_by_code(question_code)
    if question is None:
        raise HTTPException(404, "Открытое задание не найдено")
    if not answer_text.strip():
        raise HTTPException(400, "Напишите ответ перед отправкой")
    if assessment_id is None:
        raise HTTPException(400, "Для отправки нужен открытый набор тестов")
    assessment = await db.scalar(select(GradeAssessment).where(
        GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
    ).with_for_update())
    from app.services.roadmap_service import assessment_is_expired
    if assessment is None:
        raise HTTPException(404, "Набор тестов не найден")
    if assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
        raise HTTPException(409, "Срок набора истёк или он уже завершён")
    if question_code not in assessment.scoring_policy.get("open_codes", []):
        raise HTTPException(400, "Задание не входит в этот набор")
    existing = await db.scalar(select(OpenQuestionSubmission.id).where(
        OpenQuestionSubmission.assessment_id == assessment_id,
        OpenQuestionSubmission.question_code == question_code,
    ))
    if existing:
        raise HTTPException(409, "Ответ на это задание уже отправлен")
    submission = OpenQuestionSubmission(
        user_id=user.id, candidate_profile_id=profile.id, assessment_id=assessment_id,
        question_code=question_code, question_type=question["question_type"],
        answer_text=answer_text, score=0.0, passed=False, feedback="",
        criterion_scores={}, evaluator="pending", needs_manual_review=False,
        evaluation_status="queued",
    )
    db.add(submission)
    await db.flush()
    completed_sessions = (await db.execute(select(TestSession).where(
        TestSession.assessment_id == assessment.id,
        TestSession.status == "completed",
    ).order_by(TestSession.created_at.desc()))).scalars().all()
    if {item.skill_code for item in completed_sessions} >= set(assessment.required_skills):
        from app.services.roadmap_service import roadmap_service
        await roadmap_service.finish_skill(db, completed_sessions[0], profile)
    await db.commit()
    await db.refresh(submission)
    return submission


async def get_candidate_submissions(
    db: AsyncSession, candidate_profile_id: uuid.UUID
) -> list[OpenQuestionSubmission]:
    result = await db.execute(
        select(OpenQuestionSubmission)
        .where(OpenQuestionSubmission.candidate_profile_id == candidate_profile_id)
        .order_by(OpenQuestionSubmission.created_at.desc())
    )
    return list(result.scalars().all())


async def get_pending_open_submissions(
    db: AsyncSession,
) -> list[OpenQuestionSubmission]:
    """Получить список решений, требующих проверки экспертом (B-27)."""
    result = await db.execute(
        select(OpenQuestionSubmission)
        .where(OpenQuestionSubmission.evaluation_status == "manual_review")
        .order_by(OpenQuestionSubmission.created_at.asc())
    )
    return list(result.scalars().all())


async def get_open_submission_by_id(
    db: AsyncSession, submission_id: uuid.UUID
) -> OpenQuestionSubmission | None:
    result = await db.execute(
        select(OpenQuestionSubmission).where(OpenQuestionSubmission.id == submission_id)
    )
    return result.scalar_one_or_none()


async def retry_open_submission_evaluation(
    db: AsyncSession, user: User, submission_id: uuid.UUID,
    client: httpx.AsyncClient | None = None,
) -> OpenQuestionSubmission:
    submission = await db.scalar(select(OpenQuestionSubmission).where(
        OpenQuestionSubmission.id == submission_id,
        OpenQuestionSubmission.user_id == user.id,
    ))
    if submission is None:
        raise HTTPException(404, "Ответ не найден")
    if not submission.needs_manual_review or submission.assessment_id is None:
        raise HTTPException(409, "Этот ответ не ожидает повторной проверки")
    assessment = await db.get(GradeAssessment, submission.assessment_id)
    from app.services.roadmap_service import assessment_is_expired, roadmap_service
    if assessment is None or assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
        raise HTTPException(409, "Набор уже завершён или срок истёк")
    question = get_open_question_by_code(submission.question_code)
    if question is None:
        raise HTTPException(404, "Задание больше не найдено")
    try:
        result = await evaluate_open_answer(question, submission.answer_text, client)
    except RuntimeError as exc:
        raise HTTPException(503, "Проверка кода сейчас недоступна. Попробуйте позже.") from exc
    if result.get("needs_manual_review") or str(result.get("evaluator", "")).startswith("fallback_heuristic"):
        raise HTTPException(503, "Автоматическая проверка пока недоступна. Попробуйте позже.")

    submission = await db.scalar(select(OpenQuestionSubmission).where(
        OpenQuestionSubmission.id == submission_id,
        OpenQuestionSubmission.user_id == user.id,
    ).with_for_update())
    if submission is None or not submission.needs_manual_review:
        raise HTTPException(409, "Ответ уже проверен")
    submission.score = result["score"]
    submission.passed = result["passed"]
    submission.feedback = result["feedback"]
    submission.criterion_scores = result["criterion_scores"]
    submission.evaluator = result["evaluator"]
    submission.needs_manual_review = False
    submission.evaluation_status = "completed"
    profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
    sessions = (await db.execute(select(TestSession).where(
        TestSession.assessment_id == assessment.id, TestSession.status == "completed",
    ).order_by(TestSession.created_at.desc()))).scalars().all()
    if profile and {item.skill_code for item in sessions} >= set(assessment.required_skills):
        await roadmap_service.finish_skill(db, sessions[0], profile)
    await db.commit()
    await db.refresh(submission)
    return submission


async def review_open_submission(
    db: AsyncSession,
    submission_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    score: float,
    passed: bool,
    notes: str | None = None,
) -> OpenQuestionSubmission:
    """Сохранить экспертную оценку решения открытого вопроса (B-27)."""
    submission = await get_open_submission_by_id(db, submission_id)
    if not submission:
        raise ValueError(f"Решение открытого вопроса с id {submission_id} не найдено")
    if not submission.needs_manual_review:
        raise ValueError("Этот ответ не ожидает ручной проверки")
    if submission.assessment_id is not None:
        assessment = await db.get(GradeAssessment, submission.assessment_id)
        if assessment is None or assessment.status not in ("in_progress", "pending_review"):
            raise ValueError("Набор уже завершён")

    bounded_score = round(max(0.0, min(1.0, score)), 2)
    if submission.question_code in SUPPORTED_QUESTIONS:
        functional_score = submission.criterion_scores.get("Функциональные тесты")
        if functional_score is None:
            raise ValueError("Результат проверки кода отсутствует; повторите автоматическую проверку")
        bounded_score = min(bounded_score, float(functional_score))
    submission.score = bounded_score
    submission.passed = passed and bounded_score >= 0.7
    submission.manual_reviewer_notes = notes
    submission.reviewed_by = reviewer_id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.needs_manual_review = False
    submission.evaluation_status = "completed"

    if submission.assessment_id is not None:
        from app.services.roadmap_service import roadmap_service
        assessment = await db.get(GradeAssessment, submission.assessment_id)
        if assessment and assessment.status in ("in_progress", "pending_review"):
            profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
            completed_sessions = (await db.execute(select(TestSession).where(
                TestSession.assessment_id == assessment.id, TestSession.status == "completed",
            ).order_by(TestSession.created_at.desc()))).scalars().all()
            if {item.skill_code for item in completed_sessions} >= set(assessment.required_skills):
                await roadmap_service.finish_skill(db, completed_sessions[0], profile)
    await db.commit()
    await db.refresh(submission)
    return submission

