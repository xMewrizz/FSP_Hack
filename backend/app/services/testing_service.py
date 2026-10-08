from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import Grade
from app.core.question_bank import PREDEFINED_QUESTIONS
from app.models.candidate import CandidateProfile
from app.models.test import Question, TestSession
from app.models.user import User
from app.schemas.testing import (
    AnswerSubmission,
    AvailableGradeInfo,
    QuestionInTest,
    QuestionOptionResponse,
    SkillScore,
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
    TestingStatusResponse,
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

        spec = data.specialization or profile.specialization or "Backend"
        grade = (data.target_grade.value if data.target_grade else None) or profile.declared_grade or "junior"

        # Check 90 days rule if candidate is trying to change an already verified grade
        if profile.verified_grade and profile.verified_grade_updated_at and profile.verified_grade != grade:
            updated_at = profile.verified_grade_updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - updated_at
            if delta < timedelta(days=90):
                # Query last completed test session to see if this change was unlocked by recommendation
                stmt_last = (
                    select(TestSession)
                    .where(
                        TestSession.user_id == user.id,
                        TestSession.status == "completed",
                    )
                    .order_by(TestSession.completed_at.desc())
                    .limit(1)
                )
                res_last = await db.execute(stmt_last)
                last_session = res_last.scalar_one_or_none()

                is_allowed_recommendation = False
                if last_session:
                    # Confident score (>= 90%) allows recommended upgrade
                    if (
                        last_session.passed
                        and (last_session.percentage or 0.0) >= 90.0
                        and last_session.suggested_grade == grade
                    ):
                        is_allowed_recommendation = True
                    # Failed attempt allows taking recommended lower grade without cooldown block
                    elif not last_session.passed and last_session.suggested_grade == grade:
                        is_allowed_recommendation = True

                if not is_allowed_recommendation:
                    days_left = max(1, 90 - delta.days)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Изменение подтвержденного грейда ограничено правилом 90 дней (ТЗ). "
                            f"Осталось {days_left} дн., либо пройдите тест по рекомендации (результат >= 90%)."
                        ),
                    )

        # Expire any previous uncompleted in-progress sessions for this user
        stmt_prev = select(TestSession).where(
            TestSession.user_id == user.id,
            TestSession.status == "in_progress",
        )
        res_prev = await db.execute(stmt_prev)
        for prev_s in res_prev.scalars().all():
            prev_s.status = "expired"

        await TestingService.ensure_questions_seeded(db)

        # Query matching questions
        stmt_q = select(Question).where(
            Question.specialization == spec,
            Question.grade == grade,
        )
        res_q = await db.execute(stmt_q)
        questions = res_q.scalars().all()

        if not questions:
            # Fallback to any questions for this grade or specialization
            stmt_fallback = select(Question).where(Question.grade == grade)
            res_fb = await db.execute(stmt_fallback)
            questions = res_fb.scalars().all()

        if not questions:
            stmt_all = select(Question).limit(5)
            res_all = await db.execute(stmt_all)
            questions = res_all.scalars().all()

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
        if session.status == "expired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сессия тестирования истекла или была начата более поздняя сессия",
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
            if percentage >= 90.0:
                if session.target_grade == "junior":
                    suggested_grade = "middle"
                elif session.target_grade == "middle":
                    suggested_grade = "senior"
                elif session.target_grade == "senior":
                    suggested_grade = "lead"
                session.feedback = (
                    f"Поздравляем! Вы набрали {percentage}% и уверенно подтвердили квалификацию {session.target_grade}. "
                    f"При таком высоком результате вам открыт отдельный тест на повышение ({suggested_grade})."
                )
            else:
                session.feedback = (
                    f"Поздравляем! Вы набрали {percentage}% и успешно подтвердили квалификацию {session.target_grade}."
                )
        else:
            if session.target_grade == "senior":
                suggested_grade = "middle"
            elif session.target_grade == "middle":
                suggested_grade = "junior"

            session.feedback = (
                f"Вы набрали {percentage}%. Для подтверждения грейда {session.target_grade} "
                f"необходимо минимум 70%. Согласно ТЗ, грейд не снижается принудительно"
                + (f" — рекомендуем пройти тест на уровень ниже ({suggested_grade})." if suggested_grade else ".")
            )

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
                suggested_grade=s.suggested_grade,
                created_at=s.created_at,
                completed_at=s.completed_at,
            )
            for s in sessions
        ]

    @staticmethod
    async def get_status(db: AsyncSession, user: User) -> TestingStatusResponse:
        stmt_prof = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль кандидата не найден. Сначала завершите онбординг.",
            )

        stmt_last = (
            select(TestSession)
            .where(
                TestSession.user_id == user.id,
                TestSession.status == "completed",
            )
            .order_by(TestSession.completed_at.desc())
            .limit(1)
        )
        res_last = await db.execute(stmt_last)
        last_session = res_last.scalar_one_or_none()

        cooldown_active = False
        cooldown_days_remaining = 0
        cooldown_expires_at = None

        if profile.verified_grade and profile.verified_grade_updated_at:
            updated_at = profile.verified_grade_updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - updated_at
            if delta < timedelta(days=90):
                cooldown_active = True
                cooldown_days_remaining = max(1, 90 - delta.days)
                cooldown_expires_at = updated_at + timedelta(days=90)

        last_test_item = None
        suggested_grade = None
        if last_session:
            suggested_grade = last_session.suggested_grade
            last_test_item = TestSessionHistoryItem(
                id=last_session.id,
                specialization=last_session.specialization,
                target_grade=last_session.target_grade,
                percentage=last_session.percentage,
                passed=last_session.passed,
                status=last_session.status,
                suggested_grade=last_session.suggested_grade,
                created_at=last_session.created_at,
                completed_at=last_session.completed_at,
            )

        # Formulate recommended action description
        if not profile.verified_grade:
            if last_session and not last_session.passed:
                if suggested_grade:
                    recommended_action = (
                        f"Предыдущий тест на {last_session.target_grade} не сдан ({last_session.percentage}%). "
                        f"Рекомендуем пройти тест на уровень ниже: {suggested_grade.capitalize()}."
                    )
                else:
                    recommended_action = (
                        f"Предыдущий тест на {last_session.target_grade} не сдан ({last_session.percentage}%). "
                        f"Рекомендуем повторить попытку."
                    )
            else:
                recommended_action = (
                    f"Пройдите тестирование по специализации {profile.specialization or 'Backend'} "
                    f"для подтверждения грейда {profile.declared_grade or 'junior'}."
                )
        else:
            if last_session and last_session.passed and (last_session.percentage or 0.0) >= 90.0 and suggested_grade:
                recommended_action = (
                    f"Уверенный результат ({last_session.percentage}%)! "
                    f"Вам открыт отдельный тест на повышение до {suggested_grade.capitalize()}."
                )
            elif last_session and not last_session.passed and suggested_grade:
                recommended_action = (
                    f"Текущий подтвержденный грейд ({profile.verified_grade.capitalize()}) сохранен. "
                    f"Рекомендуем пройти тест на {suggested_grade.capitalize()}."
                )
            elif cooldown_active:
                recommended_action = (
                    f"Грейд {profile.verified_grade.capitalize()} подтвержден. "
                    f"Плановая смена грейда доступна через {cooldown_days_remaining} дн."
                )
            else:
                recommended_action = (
                    f"Грейд {profile.verified_grade.capitalize()} подтвержден. "
                    f"Срок 90 дней истек — доступна аттестация на любой грейд."
                )

        # Grades available to start
        available_grades = []
        for g in ["junior", "middle", "senior"]:
            is_current = (profile.verified_grade == g)
            is_rec = (suggested_grade == g)

            if not profile.verified_grade:
                is_avail = True
                if is_rec:
                    reason = "Рекомендован системой по результатам предыдущего теста"
                else:
                    reason = "Доступно для подтверждения грейда"
            else:
                if is_current:
                    is_avail = True
                    reason = "Текущий подтвержденный грейд (можно повторить тест)"
                elif is_rec:
                    is_avail = True
                    reason = "Разблокирован отдельный тест по рекомендации системы"
                elif not cooldown_active:
                    is_avail = True
                    reason = "Доступно (срок 90 дней истек)"
                else:
                    is_avail = False
                    reason = f"Заблокировано правилом 90 дней (осталось {cooldown_days_remaining} дн.)"

            available_grades.append(
                AvailableGradeInfo(
                    grade=g,
                    is_available=is_avail,
                    is_recommended=is_rec,
                    is_current_verified=is_current,
                    reason=reason,
                )
            )

        return TestingStatusResponse(
            specialization=profile.specialization,
            declared_grade=profile.declared_grade,
            verified_grade=profile.verified_grade,
            verified_grade_updated_at=profile.verified_grade_updated_at,
            cooldown_active=cooldown_active,
            cooldown_days_remaining=cooldown_days_remaining,
            cooldown_expires_at=cooldown_expires_at,
            last_completed_test=last_test_item,
            suggested_grade=suggested_grade,
            recommended_action=recommended_action,
            available_grades=available_grades,
        )


testing_service = TestingService()

