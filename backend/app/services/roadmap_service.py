from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assessment_catalog import (
    BACKEND_QUESTION_CODES, BACKEND_REQUIRED_SKILLS, SKILL_LABELS,
    SKILL_QUESTION_CODES, available_extra_skills,
)
from app.core.catalog import CatalogError, validate_test_pair
from app.core.grade_policy import OVERALL_MINIMUM, SKILL_MINIMUM, SkillResult, assess_grade
from app.core.open_question_bank import BACKEND_GRADE_OPEN_CODES, get_open_question_by_code
from app.core.question_variants import variant_for_attempt
from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment, OpenQuestionSubmission, Question, TestSession
from app.models.user import User
from app.schemas.testing import (
    AssessmentSkillProgress,
    AssessmentOpenQuestionProgress,
    AdditionalSkillTestResponse,
    GradeAssessmentResponse,
    QuestionInTest,
    QuestionOptionResponse,
    TestStartRequest,
    TestStartResponse,
)


GRADE_ORDER = ("junior", "middle", "senior")
ASSESSMENT_LIFETIME = timedelta(days=3)
JUNIOR_RETRY_COOLDOWN = timedelta(days=7)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def assessment_expires_at(assessment: GradeAssessment) -> datetime:
    created_at = assessment.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + ASSESSMENT_LIFETIME


def assessment_is_expired(assessment: GradeAssessment) -> bool:
    return assessment.status == "in_progress" and datetime.now(timezone.utc) >= assessment_expires_at(assessment)


class RoadmapService:
    @staticmethod
    async def start(db: AsyncSession, user: User, data: TestStartRequest) -> GradeAssessmentResponse:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id).with_for_update())
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        raw_grade = data.target_grade.value if data.target_grade else profile.declared_grade
        try:
            specialization, grade = validate_test_pair(data.specialization or profile.specialization, raw_grade)
        except CatalogError as error:
            raise HTTPException(400, str(error)) from error
        if specialization != profile.specialization:
            raise HTTPException(400, "Специализация теста должна совпадать с текущим профилем")
        if specialization != "Backend":
            raise HTTPException(400, "Для этой специализации пока нет набора обязательных навыков")
        language = profile.programming_language or "Python"
        if language != "Python":
            raise HTTPException(400, "Для Backend пока подготовлен только базовый тест на Python")

        # Подтверждённый грейд можно пересдать или повысить ровно на ступень.
        if profile.verified_specialization == specialization and profile.verified_grade in GRADE_ORDER:
            current_index = GRADE_ORDER.index(profile.verified_grade)
            target_index = GRADE_ORDER.index(grade)
            if target_index not in (current_index, current_index + 1):
                raise HTTPException(400, "После подтверждения грейда можно пересдать его или проверить следующий уровень")
            if target_index > current_index and profile.verified_grade_updated_at:
                changed_at = profile.verified_grade_updated_at
                if changed_at.tzinfo is None:
                    changed_at = changed_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - changed_at < timedelta(days=90):
                    raise HTTPException(400, "Следующий грейд можно подтвердить через 90 дней после предыдущего присвоения")

        assessment = await db.scalar(
            select(GradeAssessment).where(
                GradeAssessment.user_id == user.id,
                GradeAssessment.specialization == specialization,
                GradeAssessment.status.in_(("in_progress", "pending_review")),
            ).order_by(GradeAssessment.created_at.desc()).limit(1)
        )
        if assessment is not None and assessment_is_expired(assessment):
            assessment.status = "expired"
            await db.execute(update(TestSession).where(
                TestSession.assessment_id == assessment.id,
                TestSession.status == "in_progress",
            ).values(status="expired"))
            await db.flush()
            assessment = None
        if assessment is not None and assessment.target_grade != grade:
            raise HTTPException(409, "Сначала завершите начатый набор тестов на другой грейд")
        if assessment is None:
            completed_query = select(GradeAssessment).where(
                GradeAssessment.user_id == user.id,
                GradeAssessment.specialization == specialization,
                GradeAssessment.programming_language == language,
                GradeAssessment.target_grade == grade,
                GradeAssessment.status == "completed",
            )
            if (
                profile.verified_specialization == specialization
                and profile.verified_grade in GRADE_ORDER
                and GRADE_ORDER.index(grade) > GRADE_ORDER.index(profile.verified_grade)
                and profile.verified_grade_updated_at is not None
            ):
                # После подтверждения нижнего грейда попытка повышения — новый цикл.
                completed_query = completed_query.where(
                    GradeAssessment.created_at >= profile.verified_grade_updated_at
                )
            previous_completed = await db.scalar(
                completed_query.order_by(GradeAssessment.created_at.desc()).limit(1)
            )
            retake_of_id = None
            if previous_completed is not None:
                if previous_completed.retake_of_id is not None:
                    available_at = (
                        previous_completed.completed_at + JUNIOR_RETRY_COOLDOWN
                        if grade == "junior" and not previous_completed.passed and previous_completed.completed_at
                        else None
                    )
                    if available_at is not None and datetime.now(timezone.utc) >= _utc(available_at):
                        previous_completed = None
                    elif available_at is not None:
                        raise HTTPException(409, "Обе попытки Junior использованы. Новый набор доступен через неделю после пересдачи")
                    else:
                        raise HTTPException(409, "Обе попытки этого грейда использованы. Можно попробовать полный набор на уровень ниже")
            if previous_completed is not None:
                child = await db.scalar(select(GradeAssessment).where(
                    GradeAssessment.retake_of_id == previous_completed.id,
                ))
                if child is not None:
                    if grade == "junior" and child.status in ("expired", "cancelled"):
                        available_at = assessment_expires_at(child) + JUNIOR_RETRY_COOLDOWN
                        if datetime.now(timezone.utc) >= available_at:
                            previous_completed = None
                        else:
                            raise HTTPException(409, "Пересдача Junior использована. Новый набор доступен через неделю после её срока")
                    else:
                        raise HTTPException(409, "Пересдача этого грейда уже использована. Можно попробовать полный набор на уровень ниже")
            if previous_completed is not None:
                retake_of_id = previous_completed.id
                frozen_snapshots = previous_completed.retake_question_snapshots
                if set(frozen_snapshots) != {code for code, _ in BACKEND_REQUIRED_SKILLS}:
                    raise HTTPException(409, "Для пересдачи не сохранён полный запасной набор заданий")
                retake_snapshots = {}
            else:
                frozen_snapshots = {}
                retake_snapshots = {}
                for skill_code, _ in BACKEND_REQUIRED_SKILLS:
                    previous_attempts = await db.scalar(select(func.count(TestSession.id)).where(
                        TestSession.candidate_profile_id == profile.id,
                        TestSession.target_grade == grade,
                        TestSession.skill_code == skill_code,
                    )) or 0
                    frozen_snapshots[skill_code] = [
                        RoadmapService._snapshot_question(code, previous_attempts)
                        for code in BACKEND_QUESTION_CODES[grade][skill_code]
                    ]
                    retake_snapshots[skill_code] = [
                        RoadmapService._snapshot_question(code, previous_attempts + 1)
                        for code in BACKEND_QUESTION_CODES[grade][skill_code]
                    ]
            assessment = GradeAssessment(
                user_id=user.id,
                candidate_profile_id=profile.id,
                retake_of_id=retake_of_id,
                specialization=specialization,
                programming_language=language,
                target_grade=grade,
                required_skills=[code for code, _ in BACKEND_REQUIRED_SKILLS],
                question_codes={
                    code: list(BACKEND_QUESTION_CODES[grade][code])
                    for code, _ in BACKEND_REQUIRED_SKILLS
                },
                question_snapshots=frozen_snapshots,
                retake_question_snapshots=retake_snapshots,
                scoring_policy={
                    "overall": OVERALL_MINIMUM, "skill": SKILL_MINIMUM,
                    "open_codes": list(BACKEND_GRADE_OPEN_CODES[grade]), "open_weight": 10,
                },
            )
            db.add(assessment)
            await db.commit()
            await db.refresh(assessment)
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def latest(db: AsyncSession, user: User) -> GradeAssessmentResponse | None:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None or profile.specialization is None:
            return None
        assessment = await db.scalar(
            select(GradeAssessment).where(
                GradeAssessment.user_id == user.id,
                GradeAssessment.specialization == profile.specialization,
                GradeAssessment.programming_language == (profile.programming_language or "Python"),
            )
            .order_by(GradeAssessment.created_at.desc()).limit(1)
        )
        if assessment is None:
            return None
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def get(db: AsyncSession, user: User, assessment_id: uuid.UUID) -> GradeAssessmentResponse:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ))
        if assessment is None:
            raise HTTPException(404, "Набор тестов не найден")
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def stop(db: AsyncSession, user: User, assessment_id: uuid.UUID) -> GradeAssessmentResponse:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ).with_for_update())
        if assessment is None:
            raise HTTPException(404, "Набор тестов не найден")
        if assessment.status != "in_progress" or assessment_is_expired(assessment):
            raise HTTPException(409, "Этот набор уже завершён или срок его действия истёк")
        assessment.status = "cancelled"
        await db.execute(update(TestSession).where(
            TestSession.assessment_id == assessment.id,
            TestSession.status == "in_progress",
        ).values(status="cancelled"))
        await db.commit()
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def response(
        db: AsyncSession, assessment: GradeAssessment, profile: CandidateProfile,
    ) -> GradeAssessmentResponse:
        sessions = (await db.execute(
            select(TestSession).where(TestSession.assessment_id == assessment.id)
            .order_by(TestSession.created_at.desc())
        )).scalars().all()
        by_skill: dict[str, TestSession] = {}
        for session in sessions:
            if session.skill_code not in by_skill:
                by_skill[session.skill_code] = session
        retake_used = assessment.retake_of_id is not None or await db.scalar(select(GradeAssessment.id).where(
            GradeAssessment.retake_of_id == assessment.id,
        )) is not None
        skills = []
        for code in assessment.required_skills:
            session = by_skill.get(code)
            completed = session is not None and session.status == "completed"
            skills.append(AssessmentSkillProgress(
                code=code,
                label=SKILL_LABELS.get(code, code),
                status=session.status if session else "not_started",
                percentage=session.percentage if completed else None,
                level_out_of_ten=round(session.percentage / 10, 1) if completed else None,
                session_id=session.id if session else None,
            ))
        open_submissions = (await db.execute(select(OpenQuestionSubmission).where(
            OpenQuestionSubmission.assessment_id == assessment.id,
        ))).scalars().all()
        open_by_code = {item.question_code: item for item in open_submissions}
        open_questions = []
        for code in assessment.scoring_policy.get("open_codes", []):
            question = get_open_question_by_code(code)
            submission = open_by_code.get(code)
            open_questions.append(AssessmentOpenQuestionProgress(
                code=code,
                title=question["title"] if question else code,
                question_type=question["question_type"] if question else "free_text",
                status=("review_pending" if submission.needs_manual_review else "completed") if submission else "not_started",
                score=submission.score if submission and not submission.needs_manual_review else None,
                submission_id=submission.id if submission else None,
            ))
        promotion_at = profile.verified_grade_updated_at
        if promotion_at is not None and promotion_at.tzinfo is None:
            promotion_at = promotion_at.replace(tzinfo=timezone.utc)
        return GradeAssessmentResponse(
            id=assessment.id,
            specialization=assessment.specialization,
            programming_language=assessment.programming_language,
            target_grade=assessment.target_grade,
            status="expired" if assessment_is_expired(assessment) else assessment.status,
            skills=skills,
            open_questions=open_questions,
            percentage=assessment.percentage if assessment.status == "completed" else None,
            passed=assessment.passed if assessment.status == "completed" else None,
            grade_confirmed=assessment.status == "completed" and assessment.passed,
            verified_grade=profile.verified_grade,
            suggested_grade=assessment.suggested_grade,
            completed_at=assessment.completed_at,
            expires_at=assessment_expires_at(assessment),
            retake_used=retake_used,
            retry_available_at=(
                (_utc(assessment.completed_at) + JUNIOR_RETRY_COOLDOWN)
                if assessment.retake_of_id is not None and assessment.target_grade == "junior"
                and assessment.status == "completed" and not assessment.passed and assessment.completed_at
                else None
            ),
            promotion_available_at=(
                promotion_at + timedelta(days=90)
                if profile.verified_specialization == assessment.specialization
                and profile.verified_grade == assessment.target_grade
                and promotion_at
                and assessment.target_grade != "senior"
                else None
            ),
        )

    @staticmethod
    async def start_skill(
        db: AsyncSession, user: User, assessment_id: uuid.UUID, skill_code: str,
    ) -> TestStartResponse:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ).with_for_update())
        if assessment is None:
            raise HTTPException(404, "Набор тестов не найден")
        if assessment.status != "in_progress":
            raise HTTPException(409, "Набор уже завершён")
        if assessment_is_expired(assessment):
            assessment.status = "expired"
            await db.execute(update(TestSession).where(
                TestSession.assessment_id == assessment.id,
                TestSession.status == "in_progress",
            ).values(status="expired"))
            await db.commit()
            raise HTTPException(409, "Срок набора истёк. Откройте новый набор тестов")
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        if profile is None or profile.specialization != assessment.specialization or (profile.programming_language or "Python") != assessment.programming_language:
            raise HTTPException(409, "Специализация профиля изменилась. Начните новый набор тестов")
        if skill_code not in assessment.required_skills:
            raise HTTPException(400, "Навык не входит в обязательный набор")
        skill_sessions = (await db.execute(select(TestSession).where(
            TestSession.assessment_id == assessment.id,
            TestSession.skill_code == skill_code,
        ).order_by(TestSession.created_at.desc()))).scalars().all()
        existing = skill_sessions[0] if skill_sessions else None
        if existing is not None:
            if existing.status != "completed":
                return RoadmapService.session_response(existing)
            raise HTTPException(409, "Навык уже завершён. Пересдача возможна только для всего набора после всех шагов")
        frozen_snapshot = assessment.question_snapshots.get(skill_code, [])
        if not frozen_snapshot:
            raise HTTPException(409, "Для этого навыка пока нет полного набора заданий")
        return await RoadmapService._create_skill_session(
            db, user, assessment.candidate_profile_id, assessment.specialization,
            assessment.target_grade, skill_code, assessment.question_codes[skill_code],
            assessment.id, frozen_snapshot=frozen_snapshot,
        )

    @staticmethod
    async def available_additional(db: AsyncSession, user: User) -> list[AdditionalSkillTestResponse]:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        available = available_extra_skills(profile.specialization or "")
        if profile.verified_specialization != profile.specialization or not profile.verified_grade:
            return []
        available = [item for item in available if item[2] == profile.verified_grade]
        sessions = (await db.execute(select(TestSession).where(
            TestSession.user_id == user.id,
            TestSession.assessment_id.is_(None),
            TestSession.skill_code.is_not(None),
            TestSession.status == "completed",
        ).order_by(TestSession.created_at.desc()))).scalars().all()
        latest = {(item.skill_code, item.target_grade): item for item in reversed(sessions)}
        return [AdditionalSkillTestResponse(
            code=code, label=label, target_grade=grade,
            latest_percentage=latest[(code, grade)].percentage if (code, grade) in latest else None,
            level_out_of_ten=round(latest[(code, grade)].percentage / 10, 1) if (code, grade) in latest else None,
            latest_session_id=latest[(code, grade)].id if (code, grade) in latest else None,
        ) for code, label, grade in available]

    @staticmethod
    async def start_additional(
        db: AsyncSession, user: User, skill_code: str, grade: str,
    ) -> TestStartResponse:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id).with_for_update())
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        if profile.verified_specialization != profile.specialization or not profile.verified_grade:
            raise HTTPException(409, "Сначала подтвердите грейд по текущей специализации")
        if grade != profile.verified_grade:
            raise HTTPException(400, "Дополнительный навык проверяется на текущем подтверждённом грейде")
        if (skill_code, grade) not in {(code, available_grade) for code, _, available_grade in available_extra_skills(profile.specialization or "")}:
            raise HTTPException(400, "Для этого дополнительного навыка и уровня тест пока недоступен")
        existing = await db.scalar(select(TestSession).where(
            TestSession.user_id == user.id,
            TestSession.assessment_id.is_(None),
            TestSession.skill_code == skill_code,
            TestSession.target_grade == grade,
            TestSession.status == "in_progress",
        ).order_by(TestSession.created_at.desc()).limit(1))
        if existing is not None:
            return RoadmapService.session_response(existing)
        codes = SKILL_QUESTION_CODES[grade][skill_code]
        return await RoadmapService._create_skill_session(
            db, user, profile.id, profile.specialization, grade,
            skill_code, codes, None,
        )

    @staticmethod
    async def _create_skill_session(
        db: AsyncSession, user: User, profile_id: uuid.UUID,
        specialization: str, grade: str, skill_code: str,
        codes: list[str] | tuple[str, ...], assessment_id: uuid.UUID | None,
        frozen_snapshot: list[dict] | None = None,
    ) -> TestStartResponse:
        from app.services.testing_service import TestingService
        await TestingService.ensure_questions_seeded(db)
        questions = (await db.execute(select(Question).where(Question.code.in_(codes)))).scalars().all()
        if {question.code for question in questions} != set(codes):
            raise HTTPException(409, "Банк заданий для навыка неполный")
        if any(question.grade != grade for question in questions):
            raise HTTPException(500, "Задание относится к другому грейду")
        if frozen_snapshot is not None:
            snapshot = frozen_snapshot
        else:
            previous_attempts = await db.scalar(select(func.count(TestSession.id)).where(
                TestSession.candidate_profile_id == profile_id,
                TestSession.target_grade == grade,
                TestSession.skill_code == skill_code,
            )) or 0
            snapshot = [
                RoadmapService._snapshot_question(question.code, previous_attempts)
                for question in sorted(questions, key=lambda item: item.code)
            ]
        session = TestSession(
            user_id=user.id,
            candidate_profile_id=profile_id,
            assessment_id=assessment_id,
            skill_code=skill_code,
            specialization=specialization,
            target_grade=grade,
            status="in_progress",
            questions_snapshot=snapshot,
            answers_data=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return RoadmapService.session_response(session)

    @staticmethod
    def _snapshot_question(code: str, previous_attempts: int) -> dict:
        variant = variant_for_attempt(code, previous_attempts)
        return {
            "id": str(uuid.uuid4()),
            "code": variant["code"],
            "family_code": variant["family_code"],
            "variant_id": variant["variant_id"],
            "topic": variant["topic"],
            "question_type": variant["question_type"],
            "question_text": variant["question_text"],
            "options": variant["options"],
            "correct_answers": variant["correct_answers"],
            "weight": variant["weight"],
            "explanation": variant["explanation"],
        }

    @staticmethod
    def session_response(session: TestSession) -> TestStartResponse:
        return TestStartResponse(
            session_id=session.id,
            assessment_id=session.assessment_id,
            skill_code=session.skill_code,
            specialization=session.specialization,
            target_grade=session.target_grade,
            status=session.status,
            total_questions=len(session.questions_snapshot),
            questions=[QuestionInTest(
                id=item["id"], code=item["code"], topic=item["topic"],
                question_type=item["question_type"], question_text=item["question_text"],
                options=[QuestionOptionResponse(**option) for option in item["options"]],
                weight=item["weight"],
            ) for item in session.questions_snapshot],
        )

    @staticmethod
    async def finish_skill(
        db: AsyncSession, session: TestSession, profile: CandidateProfile,
    ) -> tuple[bool, str | None, str]:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == session.assessment_id,
        ).with_for_update())
        if assessment is None or assessment.status not in ("in_progress", "pending_review"):
            raise HTTPException(409, "Набор уже завершён")
        if assessment_is_expired(assessment):
            await db.rollback()
            assessment = await db.get(GradeAssessment, session.assessment_id)
            assessment.status = "expired"
            await db.execute(update(TestSession).where(
                TestSession.assessment_id == assessment.id,
                TestSession.status == "in_progress",
            ).values(status="expired"))
            await db.commit()
            raise HTTPException(409, "Срок набора истёк. Откройте новый набор тестов")
        if profile.specialization != assessment.specialization or (profile.programming_language or "Python") != assessment.programming_language:
            raise HTTPException(409, "Специализация профиля изменилась. Начните новый набор тестов")
        sessions = (await db.execute(select(TestSession).where(
            TestSession.assessment_id == assessment.id,
            TestSession.status == "completed",
        ).order_by(TestSession.created_at.desc()))).scalars().all()
        latest_by_skill: dict[str, TestSession] = {}
        for item in sessions:
            if item.skill_code not in latest_by_skill:
                latest_by_skill[item.skill_code] = item
        policy = assessment.scoring_policy
        open_codes = tuple(policy.get("open_codes", ()))
        # В исходном банке максимумы навыков зависят от грейда (например, Middle — 15).
        # Для нового набора каждый обязательный шаг нормализуется к десяти баллам.
        results = [
            SkillResult(item.skill_code, item.score / item.max_score * 10, 10)
            if open_codes else SkillResult(item.skill_code, item.score, item.max_score)
            for item in latest_by_skill.values()
        ]
        open_submissions = (await db.execute(select(OpenQuestionSubmission).where(
            OpenQuestionSubmission.assessment_id == assessment.id,
        ))).scalars().all()
        open_by_code = {item.question_code: item for item in open_submissions}
        open_weight = float(policy.get("open_weight", 10))
        for code in open_codes:
            submission = open_by_code.get(code)
            if submission and not submission.needs_manual_review:
                results.append(SkillResult(code, submission.score * open_weight, open_weight))
        decision = assess_grade(
            tuple(assessment.required_skills) + open_codes, results,
            overall_minimum=policy["overall"], skill_minimum=policy["skill"],
        )
        weak_skills = tuple(
            code for code in assessment.required_skills
            if code in latest_by_skill
            and latest_by_skill[code].score / latest_by_skill[code].max_score < policy["skill"]
        )
        if not decision.complete:
            if all(code in latest_by_skill for code in assessment.required_skills):
                if all(code in open_by_code for code in open_codes) and any(
                    open_by_code[code].needs_manual_review for code in open_codes
                ):
                    assessment.status = "pending_review"
                    return False, None, "Открытый ответ ждёт ручной проверки. Грейд пока не присвоен."
                return False, None, "Обязательные навыки пройдены. Решите два развёрнутых задания для итоговой оценки."
            if session.percentage < 50:
                return False, assessment.suggested_grade, "Навык набрал меньше 50%. Завершите остальные шаги; затем можно будет один раз пересдать весь набор."
            return False, assessment.suggested_grade, "Результат навыка сохранён. Продолжите остальные обязательные шаги."

        assessment.score = sum(item.earned for item in results)
        assessment.max_score = sum(item.maximum for item in results)
        assessment.percentage = round(decision.overall_ratio * 100, 1)
        assessment.passed = decision.passed
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)
        if decision.passed:
            grade_changed = (
                profile.verified_specialization != assessment.specialization
                or profile.verified_grade != assessment.target_grade
            )
            profile.verified_grade = assessment.target_grade
            profile.verified_specialization = assessment.specialization
            if grade_changed:
                profile.verified_grade_updated_at = assessment.completed_at
            feedback = f"Все обязательные навыки пройдены. Общий результат {assessment.percentage}%; грейд {assessment.target_grade} подтверждён."
        else:
            index = GRADE_ORDER.index(assessment.target_grade)
            assessment.suggested_grade = (
                GRADE_ORDER[index - 1] if assessment.retake_of_id is not None and index > 0 else None
            )
            weak = ", ".join(SKILL_LABELS.get(code, get_open_question_by_code(code)["title"] if get_open_question_by_code(code) else code) for code in decision.below_minimum)
            reason = f" Ниже 50%: {weak}." if weak else ""
            next_step = " Можно один раз пересдать весь набор этого грейда."
            if assessment.retake_of_id is not None:
                next_step = (
                    " Пересдача использована. Новый набор Junior доступен через неделю."
                    if assessment.target_grade == "junior"
                    else " Пересдача использована."
                )
            if assessment.suggested_grade:
                next_step += " Можно попробовать полный набор на уровень ниже."
            feedback = f"Общий результат {assessment.percentage}%. Грейд не подтверждён.{reason}" + next_step
        return decision.passed, assessment.suggested_grade, feedback


roadmap_service = RoadmapService()
