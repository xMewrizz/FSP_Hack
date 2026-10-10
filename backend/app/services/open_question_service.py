import ast
import re
from typing import Any
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
        }
        for q in questions
    ]


def _local_fallback_eval(
    question: dict[str, Any], answer_text: str
) -> dict[str, Any]:
    """Детерминированная локальная оценка на случай недоступности ml-service."""
    stripped = answer_text.strip()
    criteria = question["rubric_criteria"]
    if not stripped:
        return {
            "score": 0.0,
            "passed": False,
            "feedback": "Ответ пуст. Требуется ручная проверка экспертом.",
            "criterion_scores": {c: 0.0 for c in criteria},
            "evaluator": "fallback_heuristic",
            "needs_manual_review": True,
        }

    q_type = question["question_type"]
    criterion_scores: dict[str, float] = {}

    if q_type == "code":
        err_msg = ""
        parsed_ast = None
        try:
            parsed_ast = ast.parse(answer_text)
            has_syntax_err = False
        except SyntaxError as e:
            has_syntax_err = True
            err_msg = str(e)

        if has_syntax_err or parsed_ast is None:
            return {
                "score": 0.1,
                "passed": False,
                "feedback": f"Синтаксическая ошибка в коде: {err_msg}. Требуется ручная проверка экспертом.",
                "criterion_scores": {c: 0.0 for c in criteria},
                "evaluator": "fallback_heuristic",
                "needs_manual_review": True,
            }

        ast_classes = {n.name for n in ast.walk(parsed_ast) if isinstance(n, ast.ClassDef)}
        ast_funcs = {n.name for n in ast.walk(parsed_ast) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        code_lower = answer_text.lower()
        for c in criteria:
            c_low = c.lower()
            if "класс" in c_low or "rate_limiter" in c_low or "ratelimiter" in c_low:
                m = bool(ast_classes) or ("class " in code_lower)
            elif "инициализаци" in c_low or "__init__" in c_low:
                m = "__init__" in ast_funcs or "__init__" in code_lower or "def " in code_lower
            elif "allow_request" in c_low or "метод" in c_low:
                m = any(f in ast_funcs for f in ("allow_request", "check", "acquire", "is_allowed")) or "def " in code_lower
            elif "deque" in c_low or "хранение" in c_low or "список" in c_low:
                m = any(k in code_lower for k in ("deque", "list", "dict", "defaultdict", "append"))
            elif "окна" in c_low or "устаревш" in c_low or "threshold" in c_low:
                m = any(k in code_lower for k in ("popleft", "pop", "threshold", "while", "for", ">", "<"))
            elif "проверка лимита" in c_low or "лимит" in c_low:
                m = any(k in code_lower for k in ("<", "<=", "return true", "return false", "max_requests"))
            elif "фолд" in c_low or "kfold" in c_low or "split" in c_low:
                m = any(k in code_lower for k in ("kfold", "split", "stratifiedkfold", "cv"))
            elif "fit" in c_low or "scaler" in c_low or "обучение" in c_low:
                m = "fit" in code_lower or "scaler" in code_lower
            elif "transform" in c_low:
                m = "transform" in code_lower
            elif "roc_auc" in c_low or "score" in c_low or "метрик" in c_low:
                m = any(k in code_lower for k in ("roc_auc", "score", "predict_proba", "mean", "np.mean"))
            else:
                words = [w for w in re.findall(r"\w{4,}", c_low) if w not in {"быть", "должен", "использованием"}]
                m = any(w in code_lower for w in words)
            criterion_scores[c] = 1.0 if m else 0.2
    else:
        ans_words = set(re.findall(r"\w+", answer_text.lower(), re.UNICODE))
        for c in criteria:
            c_tokens = [w for w in re.findall(r"\w{4,}", c.lower()) if w not in {"быть", "должен", "через", "также", "например"}]
            matches = sum(1 for tok in c_tokens if any(tok[:4] in aw or aw[:4] in tok for aw in ans_words))
            ratio = matches / max(len(c_tokens), 1)
            criterion_scores[c] = 1.0 if ratio >= 0.30 else (0.5 if ratio >= 0.15 else 0.0)

    total_score = round(sum(criterion_scores.values()) / max(len(criteria), 1), 2)
    return {
        "score": total_score,
        "passed": total_score >= 0.70,
        "feedback": f"Эвристическая оценка: {int(total_score * 100)}%. Ожидает верификации экспертом (LLM офлайн).",
        "criterion_scores": criterion_scores,
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

    eval_result = await _evaluate_with_ml(question, answer_text, client)

    if assessment_id is not None and eval_result.get("evaluator") == "fallback_heuristic":
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
        .where(OpenQuestionSubmission.needs_manual_review == True)  # noqa: E712
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
    result = await _evaluate_with_ml(question, submission.answer_text, client)
    if result.get("needs_manual_review") or result.get("evaluator") == "fallback_heuristic":
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

    submission.score = round(max(0.0, min(1.0, score)), 2)
    submission.passed = passed
    submission.manual_reviewer_notes = notes
    submission.reviewed_by = reviewer_id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.needs_manual_review = False

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

