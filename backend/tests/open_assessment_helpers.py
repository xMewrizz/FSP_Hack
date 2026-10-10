"""Заранее проверенные открытые ответы для интеграционных сценариев грейда.

Тесты пути кандидата не обращаются к внешней LLM: независимые оценки задаются здесь.
Работа API отправки и ручной проверки проверяется в test_b27_open_questions.py.
"""

import uuid

from sqlalchemy import select

from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment, OpenQuestionSubmission, TestSession
from app.services.roadmap_service import roadmap_service
from conftest import TestingSessionLocal


async def finish_open_assessment(assessment_id: str, scores: tuple[float, float] = (1.0, 1.0)) -> None:
    async with TestingSessionLocal() as db:
        assessment = await db.get(GradeAssessment, uuid.UUID(assessment_id))
        assert assessment is not None
        codes = assessment.scoring_policy["open_codes"]
        assert len(codes) == len(scores) == 2
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        session = await db.scalar(select(TestSession).where(
            TestSession.assessment_id == assessment.id, TestSession.status == "completed",
        ).order_by(TestSession.created_at.desc()))
        assert session is not None
        for code, score in zip(codes, scores):
            db.add(OpenQuestionSubmission(
                user_id=assessment.user_id,
                candidate_profile_id=assessment.candidate_profile_id,
                assessment_id=assessment.id,
                question_code=code,
                question_type="code" if "CODE" in code else "free_text",
                answer_text="Ответ проверен отдельно",
                score=score,
                passed=score >= 0.7,
                feedback="Проверено для интеграционного теста",
                criterion_scores={},
                evaluator="manual_test",
                needs_manual_review=False,
            ))
        await db.flush()
        await roadmap_service.finish_skill(db, session, profile)
        await db.commit()
