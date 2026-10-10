"""Database-backed queue for open-answer grading.

The API stores an answer first. This worker may be restarted without losing it.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment, OpenQuestionSubmission, TestSession
from app.core.open_question_bank import get_open_question_by_code
from app.services.open_question_service import evaluate_open_answer


logger = logging.getLogger(__name__)
MAX_CONCURRENT_EVALUATIONS = 2


async def process_queued_submission(submission_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        submission = await db.get(OpenQuestionSubmission, submission_id)
        if submission is None or submission.evaluation_status != "evaluating":
            return
        question = get_open_question_by_code(submission.question_code)
        answer_text = submission.answer_text
    if question is None:
        await _mark_failed(submission_id)
        return

    try:
        result = await evaluate_open_answer(question, answer_text)
        async with AsyncSessionLocal() as db:
            # All completions for one assessment serialize on its row.
            submission = await db.get(OpenQuestionSubmission, submission_id)
            if submission is None or submission.evaluation_status != "evaluating":
                return
            assessment_id = submission.assessment_id
            assessment = await db.scalar(select(GradeAssessment).where(
                GradeAssessment.id == assessment_id,
            ).with_for_update()) if assessment_id else None
            submission = await db.get(OpenQuestionSubmission, submission_id)
            if submission is None or submission.evaluation_status != "evaluating":
                return
            if result.get("evaluator") == "fallback_heuristic":
                submission.evaluation_status = "failed"
                submission.feedback = "Автоматическая проверка пока недоступна. Ответ сохранён; попробуйте повторить проверку."
                submission.evaluator = "pending"
            else:
                submission.score = result["score"]
                submission.passed = result["passed"]
                submission.feedback = result.get("feedback", "")
                submission.criterion_scores = result.get("criterion_scores", {})
                submission.evaluator = result.get("evaluator", "llm")
                submission.needs_manual_review = result.get("needs_manual_review", False)
                submission.evaluation_status = "manual_review" if submission.needs_manual_review else "completed"
                await db.flush()
                if assessment is not None and assessment.status in ("in_progress", "pending_review"):
                    sessions = (await db.execute(select(TestSession).where(
                        TestSession.assessment_id == assessment.id,
                        TestSession.status == "completed",
                    ).order_by(TestSession.created_at.desc()))).scalars().all()
                    if sessions and {item.skill_code for item in sessions} >= set(assessment.required_skills):
                        from app.services.roadmap_service import roadmap_service
                        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
                        if profile is not None:
                            await roadmap_service.finish_skill(db, sessions[0], profile)
            await db.commit()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Open-answer evaluation failed for %s", submission_id)
        await _mark_failed(submission_id)


async def _mark_failed(submission_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(update(OpenQuestionSubmission).where(
            OpenQuestionSubmission.id == submission_id,
            OpenQuestionSubmission.evaluation_status == "evaluating",
        ).values(
            evaluation_status="failed",
            feedback="Автоматическая проверка пока недоступна. Ответ сохранён; попробуйте повторить проверку.",
        ))
        await db.commit()


async def _claim_next() -> uuid.UUID | None:
    async with AsyncSessionLocal() as db:
        submission = await db.scalar(select(OpenQuestionSubmission).where(
            OpenQuestionSubmission.evaluation_status == "queued",
        ).order_by(OpenQuestionSubmission.created_at).limit(1).with_for_update(skip_locked=True))
        if submission is None:
            await db.rollback()
            return None
        submission.evaluation_status = "evaluating"
        submission_id = submission.id
        await db.commit()
        return submission_id


async def run_evaluation_worker() -> None:
    # A request may have been interrupted by process shutdown. Resume saved answers.
    async with AsyncSessionLocal() as db:
        await db.execute(update(OpenQuestionSubmission).where(
            OpenQuestionSubmission.evaluation_status == "evaluating",
        ).values(evaluation_status="queued"))
        await db.commit()
    active: set[asyncio.Task] = set()
    try:
        while True:
            active = {task for task in active if not task.done()}
            while len(active) < MAX_CONCURRENT_EVALUATIONS:
                submission_id = await _claim_next()
                if submission_id is None:
                    break
                active.add(asyncio.create_task(process_queued_submission(submission_id)))
            await asyncio.sleep(1)
    finally:
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
