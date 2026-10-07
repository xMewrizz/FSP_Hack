from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.catalog import (
    CatalogError,
    assert_no_substitution,
    suggest_upshift_grade,
    validate_test_pair,
)
from app.core.constants import Grade
from app.core.question_bank import PREDEFINED_QUESTIONS
from app.models.candidate import CandidateProfile
from app.models.test import Question, TestSession
from app.models.user import User
from app.schemas.testing import (
    AnswerSubmission,
    QuestionInTest,
    QuestionOptionResponse,
    SkillScore,
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
)


class TestingService:
    @staticmethod
    async def ensure_questions_seeded(db: AsyncSession) -> None:
        stmt = select(Question.code)
        res = await db.execute(stmt)
        existing_codes = set(res.scalars().all())

        for q_data in PREDEFINED_QUESTIONS:
            if q_data["code"] not in existing_codes:
                q = Question(
                    code=q_data["code"],
                    specialization=q_data["specialization"],
                    grade=q_data["grade"],
                    topic=q_data["topic"],
                    question_type=q_data["question_type"],
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answers=q_data["correct_answers"],
                    explanation=q_data["explanation"],
                    weight=q_data["weight"],
                )
                db.add(q)
        await db.commit()

    @staticmethod
    async def start_test(
        db: AsyncSession, user: User, data: TestStartRequest
    ) -> TestStartResponse:
        stmt_prof = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль кандидата не найден. Сначала завершите онбординг.",
            )

        # B-01: значений по умолчанию нет. Если специализация или грейд не заданы
        # ни в запросе, ни в профиле — явная ошибка 400 из каталога, а не тихий
        # тест «Backend / junior» для чужого профиля.
        raw_spec = data.specialization or profile.specialization
        raw_grade = (data.target_grade.value if data.target_grade else None) or profile.declared_grade

        # B-01: единый справочник. Неподдерживаемая пара -> явная ошибка 400.
        # Тихая подмена вопросов другой специализации/уровня запрещена.
        try:
            spec, grade = validate_test_pair(raw_spec, raw_grade)
        except CatalogError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        # Check 90 days rule if candidate is trying to change an already verified grade
        if profile.verified_grade and profile.verified_grade_updated_at:
            delta = datetime.now(timezone.utc) - profile.verified_grade_updated_at
            if delta < timedelta(days=90) and profile.verified_grade != grade:
                days_left = 90 - delta.days
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Изменение подтвержденного грейда ограничено правилом 90 дней (ТЗ). Осталось {days_left} дн.",
                )

        await TestingService.ensure_questions_seeded(db)

        # Query matching questions
        stmt_q = select(Question).where(
            Question.specialization == spec,
            Question.grade == grade,
        )
        res_q = await db.execute(stmt_q)
        questions = list(res_q.scalars().all())

        # B-01: подмена запрещена. Пустая выдача или чужая пара -> 400, а не фолбэк.
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Для пары «{spec} / {grade}» нет заданий. "
                    f"Сейчас тест доступен для: Backend junior, Backend middle, Backend senior. "
                    f"Вопросы другой специализации или уровня не подставляются."
                ),
            )
        try:
            assert_no_substitution(spec, grade, questions)
        except CatalogError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

        # Build snapshot for storage
        snapshot = []
        client_questions = []

        for q in questions:
            snapshot.append({
                "id": str(q.id),
                "code": q.code,
                "topic": q.topic,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "options": q.options,
                "correct_answers": q.correct_answers,
                "weight": q.weight,
                "explanation": q.explanation,
            })

            client_questions.append(
                QuestionInTest(
                    id=str(q.id),
                    code=q.code,
                    topic=q.topic,
                    question_type=q.question_type,
                    question_text=q.question_text,
                    options=[QuestionOptionResponse(**opt) for opt in q.options],
                    weight=q.weight,
                )
            )

        session = TestSession(
            user_id=user.id,
            candidate_profile_id=profile.id,
            specialization=spec,
            target_grade=grade,
            status="in_progress",
            questions_snapshot=snapshot,
            answers_data=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return TestStartResponse(
            session_id=session.id,
            specialization=spec,
            target_grade=grade,
            status=session.status,
            questions=client_questions,
            total_questions=len(client_questions),
        )

    @staticmethod
    async def submit_test(
        db: AsyncSession, user: User, session_id: uuid.UUID, data: TestSubmitRequest
    ) -> TestResultResponse:
        stmt = select(TestSession).where(
            TestSession.id == session_id,
            TestSession.user_id == user.id,
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия тестирования не найдена",
            )

        if session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данный тест уже был завершен ранее",
            )

        # Map answers
        user_answers_map = {ans.question_id: set(ans.selected_answers) for ans in data.answers}

        total_score = 0.0
        max_score = 0.0
        topic_scores: dict[str, dict[str, float]] = {}

        for q in session.questions_snapshot:
            q_id = q["id"]
            topic = q["topic"]
            weight = float(q.get("weight", 1.0))
            correct_set = set(q.get("correct_answers", []))

            if topic not in topic_scores:
                topic_scores[topic] = {"score": 0.0, "max": 0.0}

            max_score += weight
            topic_scores[topic]["max"] += weight

            user_set = user_answers_map.get(q_id, set())
            if user_set == correct_set and len(correct_set) > 0:
                total_score += weight
                topic_scores[topic]["score"] += weight

        percentage = round((total_score / max_score * 100.0) if max_score > 0 else 0.0, 1)
        passed = percentage >= 70.0

        # Build skill breakdown
        skill_breakdown = [
            SkillScore(
                topic=top,
                score=round(val["score"], 1),
                max_score=round(val["max"], 1),
                percentage=round((val["score"] / val["max"] * 100.0) if val["max"] > 0 else 0.0, 1),
            )
            for top, val in topic_scores.items()
        ]

        now = datetime.now(timezone.utc)
        session.score = round(total_score, 1)
        session.max_score = round(max_score, 1)
        session.percentage = percentage
        session.passed = passed
        session.status = "completed"
        session.completed_at = now
        session.skill_breakdown = [s.model_dump() for s in skill_breakdown]
        session.answers_data = [a.model_dump() for a in data.answers]

        # Update candidate profile
        stmt_prof = select(CandidateProfile).where(CandidateProfile.id == session.candidate_profile_id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one()

        suggested_grade = None
        if passed:
            profile.verified_grade = session.target_grade
            profile.verified_grade_updated_at = now
            session.feedback = f"Поздравляем! Вы набрали {percentage}% и успешно подтвердили квалификацию {session.target_grade}."
            if percentage >= 90.0:
                # B-01: следующий грейд предлагаем только если тест по нему
                # доступен (senior -> lead сейчас даёт None, lead не предлагаем).
                suggested_grade = suggest_upshift_grade(session.specialization, session.target_grade)
        else:
            session.feedback = (
                f"Вы набрали {percentage}%. Для подтверждения грейда {session.target_grade} "
                f"необходимо минимум 70%. Согласно ТЗ, грейд не снижается принудительно — "
                f"рекомендуем пройти тест на уровень ниже."
            )
            if session.target_grade == "senior":
                suggested_grade = "middle"
            elif session.target_grade == "middle":
                suggested_grade = "junior"

        session.suggested_grade = suggested_grade

        # Collect verified skills into profile
        current_skills = set(profile.skills or [])
        for item in skill_breakdown:
            if item.percentage >= 70.0:
                current_skills.add(item.topic)
        profile.skills = list(current_skills)

        await db.commit()
        await db.refresh(session)

        return TestResultResponse(
            session_id=session.id,
            specialization=session.specialization,
            target_grade=session.target_grade,
            score=session.score,
            max_score=session.max_score,
            percentage=session.percentage,
            passed=session.passed,
            verified_grade=profile.verified_grade,
            skill_breakdown=skill_breakdown,
            feedback=session.feedback or "",
            suggested_grade=session.suggested_grade,
            completed_at=session.completed_at,
        )

    @staticmethod
    async def get_session(
        db: AsyncSession, user: User, session_id: uuid.UUID
    ) -> TestResultResponse:
        stmt = select(TestSession).where(
            TestSession.id == session_id,
            TestSession.user_id == user.id,
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия тестирования не найдена",
            )

        stmt_prof = select(CandidateProfile).where(CandidateProfile.id == session.candidate_profile_id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one()

        breakdown = [SkillScore(**item) for item in session.skill_breakdown]

        return TestResultResponse(
            session_id=session.id,
            specialization=session.specialization,
            target_grade=session.target_grade,
            score=session.score,
            max_score=session.max_score,
            percentage=session.percentage,
            passed=session.passed,
            verified_grade=profile.verified_grade,
            skill_breakdown=breakdown,
            feedback=session.feedback or "",
            suggested_grade=session.suggested_grade,
            completed_at=session.completed_at,
        )

    @staticmethod
    async def get_history(db: AsyncSession, user: User) -> list[TestSessionHistoryItem]:
        stmt = (
            select(TestSession)
            .where(TestSession.user_id == user.id)
            .order_by(TestSession.created_at.desc())
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()

        return [
            TestSessionHistoryItem(
                id=s.id,
                specialization=s.specialization,
                target_grade=s.target_grade,
                percentage=s.percentage,
                passed=s.passed,
                status=s.status,
                created_at=s.created_at,
                completed_at=s.completed_at,
            )
            for s in sessions
        ]


testing_service = TestingService()
