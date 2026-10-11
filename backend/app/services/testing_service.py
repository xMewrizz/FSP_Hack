from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import httpx
from fastapi import HTTPException, status
from app.core.assessment_catalog import SKILL_LABELS
from app.core.config import settings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer
from app.core.catalog import (
    CatalogError,
    assert_no_substitution,
    validate_test_pair,
)
from app.core.question_bank import PREDEFINED_QUESTIONS
from app.core.question_variants import variant_for_attempt
from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment, Question, TestSession
from app.models.user import User
from app.schemas.testing import (
    QuestionInTest,
    QuestionOptionResponse,
    QuestionReview,
    SkillScore,
    TestResultResponse,
    TestSessionHistoryItem,
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
)


def build_question_review(
    questions: list[dict[str, Any]], answers: list[dict[str, Any]]
) -> list[QuestionReview]:
    selected_by_id = {answer["question_id"]: answer["selected_answers"] for answer in answers}
    review = []
    for question in questions:
        option_text = {option["id"]: option["text"] for option in question["options"]}
        selected = selected_by_id.get(question["id"], [])
        correct = question.get("correct_answers", [])
        review.append(QuestionReview(
            code=question["code"],
            topic=question["topic"],
            question_text=question["question_text"],
            selected_answers=[option_text[choice] for choice in selected],
            correct_answers=[option_text[choice] for choice in correct],
            is_correct=bool(correct) and set(selected) == set(correct),
            explanation=question.get("explanation", ""),
        ))
    return review


def missed_answer_pairs(review: list[QuestionReview], limit: int = 10) -> list[dict[str, str]]:
    """Только неверные пары. Верные ответы в модель не отправляются."""
    pairs: list[dict[str, str]] = []
    for item in review:
        if item.is_correct:
            continue
        pairs.append({
            "question": item.question_text,
            "answer": "; ".join(item.selected_answers) or "нет ответа",
        })
        if len(pairs) >= limit:
            break
    return pairs


async def load_review_topics(
    review: list[QuestionReview],
    *,
    skill_code: str | None,
    specialization: str,
    grade: str,
) -> tuple[list[str], str]:
    """none — ошибок нет; ready — темы получены; unavailable — модель не ответила."""
    missed = missed_answer_pairs(review)
    if not missed:
        return [], "none"
    skill = SKILL_LABELS.get(skill_code or "", skill_code or "Навык")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{settings.ML_SERVICE_URL.rstrip('/')}/skill-gap-topics",
                json={
                    "skill": skill,
                    "specialization": specialization,
                    "grade": grade,
                    "missed": missed,
                },
            )
            response.raise_for_status()
            payload = response.json()
            topics = payload.get("topics") if isinstance(payload, dict) else None
            if not isinstance(topics, list):
                return [], "unavailable"
            cleaned = []
            for topic in topics:
                text = " ".join(str(topic).split())
                if text and text not in cleaned:
                    cleaned.append(text)
            return cleaned[:10], "ready"
    except (httpx.HTTPError, ValueError, TypeError):
        return [], "unavailable"


def required_correct_answers(question_count: int) -> int:
    """Предварительный порог: 9 из 12, для старых попыток — та же доля 3/4."""
    return (3 * question_count + 3) // 4


def grade_confirmed_by_session(session: TestSession) -> bool:
    # Грейд подтверждает полный GradeAssessment, а не отдельная сессия.
    return False


class TestingService:
    @staticmethod
    async def ensure_questions_seeded(db: AsyncSession) -> None:
        stmt = select(Question).where(
            Question.code.in_([q["code"] for q in PREDEFINED_QUESTIONS])
        )
        res = await db.execute(stmt)
        existing = {q.code: q for q in res.scalars().all()}

        for q_data in PREDEFINED_QUESTIONS:
            question = existing.get(q_data["code"])
            if question is None:
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
            else:
                # Исправления эталонного банка должны попадать и в ранее
                # созданную БД. Уже начатые попытки хранят свой снимок.
                for field in (
                    "specialization", "grade", "topic", "question_type",
                    "question_text", "options", "correct_answers", "explanation", "weight",
                ):
                    value = q_data[field]
                    if getattr(question, field) != value:
                        setattr(question, field, value)
        await db.flush()

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
            updated_at = profile.verified_grade_updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - updated_at
            if delta < timedelta(days=90) and profile.verified_grade != grade and grade != "senior":
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
            Question.code.in_([
                question["code"] for question in PREDEFINED_QUESTIONS
                if question["specialization"] == spec
                and question["grade"] == grade
                and int(question["code"].split("-")[-1]) <= 12
            ]),
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

        # Serialize starts for one candidate so concurrent requests do not
        # receive the same next variant.
        await db.execute(
            select(CandidateProfile.id)
            .where(CandidateProfile.id == profile.id)
            .with_for_update()
        )
        previous_attempts = await db.scalar(
            select(func.count(TestSession.id)).where(
                TestSession.candidate_profile_id == profile.id,
                TestSession.specialization == spec,
                TestSession.target_grade == grade,
            )
        ) or 0

        selected_variants = [
            (question, variant_for_attempt(question.code, previous_attempts))
            for question in sorted(questions, key=lambda item: item.code)
        ]
        try:
            assert_no_substitution(spec, grade, [variant for _, variant in selected_variants])
        except CatalogError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        # The snapshot fixes the selected version and answer key for this attempt.
        snapshot = []
        client_questions = []

        for q, variant in selected_variants:
            question_id = str(q.id if variant["variant_id"] == "v1" else uuid.uuid5(q.id, variant["variant_id"]))
            snapshot.append({
                "id": question_id,
                "code": variant["code"],
                "family_code": variant["family_code"],
                "variant_id": variant["variant_id"],
                "parameters": variant.get("parameters", {}),
                "topic": variant["topic"],
                "question_type": variant["question_type"],
                "question_text": variant["question_text"],
                "options": variant["options"],
                "correct_answers": variant["correct_answers"],
                "weight": variant["weight"],
                "explanation": variant["explanation"],
            })

            client_questions.append(
                QuestionInTest(
                    id=question_id,
                    code=variant["code"],
                    topic=variant["topic"],
                    question_type=variant["question_type"],
                    question_text=variant["question_text"],
                    options=[QuestionOptionResponse(**opt) for opt in variant["options"]],
                    weight=variant["weight"],
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

        # Answers must refer to questions issued in this session.
        snapshot_by_id = {question["id"]: question for question in session.questions_snapshot}
        submitted_ids = [answer.question_id for answer in data.answers]
        if len(submitted_ids) != len(set(submitted_ids)) or any(question_id not in snapshot_by_id for question_id in submitted_ids):
            raise HTTPException(status_code=400, detail="Ответы содержат повтор или задание не из этой попытки")
        for answer in data.answers:
            allowed = {option["id"] for option in snapshot_by_id[answer.question_id]["options"]}
            if any(choice not in allowed for choice in answer.selected_answers):
                raise HTTPException(status_code=400, detail="Ответ содержит неизвестный вариант выбора")

        # Map answers
        user_answers_map = {ans.question_id: set(ans.selected_answers) for ans in data.answers}
        review = build_question_review(
            session.questions_snapshot,
            [answer.model_dump() for answer in data.answers],
        )
        review_topics, review_topics_status = await load_review_topics(
            review,
            skill_code=session.skill_code,
            specialization=session.specialization,
            grade=session.target_grade,
        )
        session.review_topics = review_topics
        session.review_topics_status = review_topics_status

        total_score = 0.0
        max_score = 0.0
        topic_scores: dict[str, dict[str, float | int]] = {}

        for q in session.questions_snapshot:
            q_id = q["id"]
            topic = q["topic"]
            weight = float(q.get("weight", 1.0))
            correct_set = set(q.get("correct_answers", []))

            if topic not in topic_scores:
                topic_scores[topic] = {"score": 0.0, "max": 0.0, "correct": 0, "count": 0}

            max_score += weight
            topic_scores[topic]["max"] += weight
            topic_scores[topic]["count"] += 1

            user_set = user_answers_map.get(q_id, set())
            if user_set == correct_set and len(correct_set) > 0:
                total_score += weight
                topic_scores[topic]["score"] += weight
                topic_scores[topic]["correct"] += 1

        percentage = round((total_score / max_score * 100.0) if max_score > 0 else 0.0, 1)
        correct_count = sum(item.is_correct for item in review)
        required_correct = (
            (len(review) + 1) // 2 if session.assessment_id
            else 0 if session.skill_code else required_correct_answers(len(review))
        )
        passed = bool(review) and (
            total_score / max_score >= 0.50 if session.assessment_id
            else False if session.skill_code else correct_count >= required_correct
        )

        # Build skill breakdown
        skill_breakdown = [
            SkillScore(
                topic=top,
                score=round(val["score"], 1),
                max_score=round(val["max"], 1),
                percentage=round((val["score"] / val["max"] * 100.0) if val["max"] > 0 else 0.0, 1),
                correct_count=int(val["correct"]),
                total_questions=int(val["count"]),
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
        session.answers_data = [
            {
                **answer.model_dump(),
                "code": snapshot_by_id[answer.question_id]["code"],
                "family_code": snapshot_by_id[answer.question_id].get("family_code", snapshot_by_id[answer.question_id]["code"]),
                "variant_id": snapshot_by_id[answer.question_id].get("variant_id", "v1"),
            }
            for answer in data.answers
        ]

        # Update candidate profile
        stmt_prof = select(CandidateProfile).where(CandidateProfile.id == session.candidate_profile_id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one()

        if session.assessment_id:
            from app.services.roadmap_service import roadmap_service
            await db.flush()
            grade_confirmed, suggested_grade, feedback = await roadmap_service.finish_skill(db, session, profile)
            session.feedback = feedback
            session.suggested_grade = suggested_grade
            await db.commit()
            await db.refresh(session)
            return TestResultResponse(
                session_id=session.id,
                specialization=session.specialization,
                target_grade=session.target_grade,
                score=session.score,
                max_score=session.max_score,
                percentage=session.percentage,
                correct_count=correct_count,
                total_questions=len(review),
                required_correct=required_correct,
                passed=session.passed,
                grade_confirmed=grade_confirmed,
                verified_grade=profile.verified_grade,
                skill_breakdown=skill_breakdown,
                question_review=review,
                feedback=feedback,
                suggested_grade=suggested_grade,
                completed_at=session.completed_at,
                skill_code=session.skill_code,
                assessment_id=session.assessment_id,
                review_topics=review_topics,
                review_topics_status=review_topics_status,
            )

        if session.skill_code:
            session.feedback = (
                f"Результат навыка сохранён: {percentage}% на уровне {session.target_grade}. "
                "Дополнительный тест не влияет на грейд."
            )
            await db.commit()
            await db.refresh(session)
            return TestResultResponse(
                session_id=session.id,
                specialization=session.specialization,
                target_grade=session.target_grade,
                score=session.score,
                max_score=session.max_score,
                percentage=session.percentage,
                correct_count=correct_count,
                total_questions=len(review),
                required_correct=0,
                passed=None,
                grade_confirmed=False,
                verified_grade=profile.verified_grade,
                skill_breakdown=skill_breakdown,
                question_review=review,
                feedback=session.feedback,
                suggested_grade=None,
                completed_at=session.completed_at,
                skill_code=session.skill_code,
                assessment_id=None,
                review_topics=review_topics,
                review_topics_status=review_topics_status,
            )

        session.feedback = (
            f"Верно {correct_count} из {len(review)} заданий. Это старый общий формат: "
            "он не присваивает грейд. Откройте набор обязательных навыков."
        )
        session.suggested_grade = None

        await db.commit()
        await db.refresh(session)

        return TestResultResponse(
            session_id=session.id,
            specialization=session.specialization,
            target_grade=session.target_grade,
            score=session.score,
            max_score=session.max_score,
            percentage=session.percentage,
            correct_count=correct_count,
            total_questions=len(review),
            required_correct=required_correct,
            passed=session.passed,
            grade_confirmed=grade_confirmed_by_session(session),
            verified_grade=profile.verified_grade,
            skill_breakdown=skill_breakdown,
            question_review=review,
            feedback=session.feedback or "",
            suggested_grade=session.suggested_grade,
            completed_at=session.completed_at,
            skill_code=session.skill_code,
            assessment_id=session.assessment_id,
            review_topics=review_topics,
            review_topics_status=review_topics_status,
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
        review = build_question_review(session.questions_snapshot, session.answers_data) if session.status == "completed" else []
        assessment = await db.get(GradeAssessment, session.assessment_id) if session.assessment_id else None

        return TestResultResponse(
            session_id=session.id,
            specialization=session.specialization,
            target_grade=session.target_grade,
            score=session.score,
            max_score=session.max_score,
            percentage=session.percentage,
            correct_count=sum(item.is_correct for item in review),
            total_questions=len(session.questions_snapshot),
            required_correct=(
                (len(session.questions_snapshot) + 1) // 2 if session.assessment_id
                else 0 if session.skill_code else required_correct_answers(len(session.questions_snapshot))
            ),
            passed=None if session.skill_code and not session.assessment_id else session.passed,
            grade_confirmed=bool(assessment and assessment.status == "completed" and assessment.passed),
            verified_grade=profile.verified_grade,
            skill_breakdown=breakdown,
            question_review=review,
            feedback=session.feedback or "",
            suggested_grade=session.suggested_grade,
            completed_at=session.completed_at,
            skill_code=session.skill_code,
            assessment_id=session.assessment_id,
            review_topics=list(session.review_topics or []),
            review_topics_status=session.review_topics_status or "none",
        )

    @staticmethod
    async def get_history(db: AsyncSession, user: User) -> list[TestSessionHistoryItem]:
        stmt = (
            select(TestSession)
            .options(
                defer(TestSession.questions_snapshot),
                defer(TestSession.answers_data),
                defer(TestSession.skill_breakdown),
            )
            .where(TestSession.user_id == user.id)
            .order_by(TestSession.created_at.desc())
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()
        assessment_ids = {s.assessment_id for s in sessions if s.assessment_id}
        assessments = {
            item.id: item for item in (await db.execute(
                select(GradeAssessment).where(GradeAssessment.id.in_(assessment_ids))
            )).scalars().all()
        } if assessment_ids else {}

        return [
            TestSessionHistoryItem(
                id=s.id,
                specialization=s.specialization,
                target_grade=s.target_grade,
                percentage=s.percentage,
                passed=None if s.skill_code and not s.assessment_id else s.passed,
                grade_confirmed=bool(
                    s.assessment_id in assessments
                    and assessments[s.assessment_id].status == "completed"
                    and assessments[s.assessment_id].passed
                ),
                status=s.status,
                created_at=s.created_at,
                completed_at=s.completed_at,
                skill_code=s.skill_code,
                assessment_id=s.assessment_id,
            )
            for s in sessions
        ]


testing_service = TestingService()
