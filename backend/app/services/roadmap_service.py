from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assessment_catalog import (
    BACKEND_QUESTION_CODES, BACKEND_REQUIRED_SKILLS, SKILL_LABELS,
    SKILL_QUESTION_CODES, available_extra_skills,
)
from app.core.assessment_catalog_ds import DS_QUESTION_CODES, DS_REQUIRED_SKILLS
from app.core.catalog import ALL_SPECIALIZATIONS, CatalogError, is_testable, normalize_specialization, validate_test_pair
from app.core.grade_policy import OVERALL_MINIMUM, SKILL_MINIMUM, SkillResult, assess_grade
from app.core.open_question_bank import GRADE_OPEN_CODES, GRADE_RETAKE_OPEN_CODES, get_open_question_by_code
from app.core.question_variants import variant_for_attempt
from app.models.candidate import CandidateProfile
from app.models.candidate_specialization import CandidateSpecializationTrack
from app.models.test import GradeAssessment, OpenQuestionSubmission, Question, TestSession
from app.models.user import User
from app.schemas.testing import (
    AssessmentSkillProgress,
    AssessmentOpenQuestionProgress,
    AdditionalSkillTestResponse,
    CandidateSpecializationTrackResponse,
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
    async def request_specialization(
        db: AsyncSession, user: User, specialization: str,
    ) -> CandidateSpecializationTrackResponse:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        canonical = normalize_specialization(specialization)
        if canonical not in ALL_SPECIALIZATIONS:
            raise HTTPException(400, "Выберите специализацию из каталога")
        if canonical == profile.specialization:
            raise HTTPException(409, "Это основная специализация профиля")
        track = await db.scalar(select(CandidateSpecializationTrack).where(
            CandidateSpecializationTrack.candidate_profile_id == profile.id,
            CandidateSpecializationTrack.specialization == canonical,
        ))
        if track is None:
            track = CandidateSpecializationTrack(
                candidate_profile_id=profile.id,
                specialization=canonical,
            )
            db.add(track)
            await db.commit()
            await db.refresh(track)
        return await RoadmapService._track_response(db, track)

    @staticmethod
    async def list_specializations(
        db: AsyncSession, user: User,
    ) -> list[CandidateSpecializationTrackResponse]:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        tracks = (await db.scalars(select(CandidateSpecializationTrack).where(
            CandidateSpecializationTrack.candidate_profile_id == profile.id,
        ).order_by(CandidateSpecializationTrack.created_at))).all()
        return [await RoadmapService._track_response(db, track) for track in tracks]

    @staticmethod
    async def _track_response(
        db: AsyncSession, track: CandidateSpecializationTrack,
    ) -> CandidateSpecializationTrackResponse:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.candidate_profile_id == track.candidate_profile_id,
            GradeAssessment.specialization == track.specialization,
            GradeAssessment.status.in_(("in_progress", "pending_review")),
        ).order_by(GradeAssessment.created_at.desc()).limit(1))
        available = any(is_testable(track.specialization, grade) for grade in GRADE_ORDER)
        status = (
            "verified" if track.verified_grade else
            "in_progress" if assessment else
            "requested"
        )
        return CandidateSpecializationTrackResponse(
            specialization=track.specialization,
            status=status,
            test_available=available,
            availability_reason=None if available else (
                "Базовый банк тестов для этого направления ещё готовится."
            ),
            verified_grade=track.verified_grade,
            assessment_id=assessment.id if assessment else None,
        )

    @staticmethod
    async def reconcile_failed_skill(
        db: AsyncSession, assessment: GradeAssessment, profile: CandidateProfile,
    ) -> None:
        """Закрыть ранее начатый набор, если в нём уже есть навык ниже порога."""
        if assessment.status not in ("in_progress", "pending_review") or assessment_is_expired(assessment):
            return
        sessions = (await db.execute(select(TestSession).where(
            TestSession.assessment_id == assessment.id,
        ).order_by(TestSession.created_at.desc()))).scalars().all()
        latest_by_skill = {item.skill_code: item for item in reversed(sessions)}
        failed = next((item for item in latest_by_skill.values() if item.status == "completed"
                       and item.skill_code in assessment.required_skills
                       and item.percentage < assessment.scoring_policy["skill"] * 100), None)
        if failed is not None:
            await RoadmapService.finish_skill(db, failed, profile)
            await db.commit()

    @staticmethod
    async def start(db: AsyncSession, user: User, data: TestStartRequest) -> GradeAssessmentResponse:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id).with_for_update())
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        requested_specialization = normalize_specialization(data.specialization or profile.specialization)
        specialty_track = None
        if requested_specialization != profile.specialization:
            specialty_track = await db.scalar(select(CandidateSpecializationTrack).where(
                CandidateSpecializationTrack.candidate_profile_id == profile.id,
                CandidateSpecializationTrack.specialization == requested_specialization,
            ).with_for_update())
            if specialty_track is None:
                raise HTTPException(409, "Сначала запросите дополнительное направление")
        raw_grade = data.target_grade.value if data.target_grade else profile.declared_grade
        try:
            specialization, grade = validate_test_pair(requested_specialization, raw_grade)
        except CatalogError as error:
            raise HTTPException(400, str(error)) from error
        required_skills = BACKEND_REQUIRED_SKILLS if specialization == "Backend" else DS_REQUIRED_SKILLS
        question_codes = BACKEND_QUESTION_CODES if specialization == "Backend" else DS_QUESTION_CODES
        language = profile.programming_language or "Python"
        if language != "Python":
            raise HTTPException(400, "Для этой специализации пока подготовлен только базовый тест на Python")

        verified_grade = specialty_track.verified_grade if specialty_track else profile.verified_grade
        verified_at = specialty_track.verified_at if specialty_track else profile.verified_grade_updated_at
        # Подтверждённый грейд можно пересдать или повысить ровно на ступень.
        if verified_grade in GRADE_ORDER:
            current_index = GRADE_ORDER.index(verified_grade)
            target_index = GRADE_ORDER.index(grade)
            if target_index not in (current_index, current_index + 1):
                raise HTTPException(400, "После подтверждения грейда можно пересдать его или проверить следующий уровень")
            if target_index > current_index and verified_at:
                changed_at = verified_at
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
        if assessment is not None:
            await RoadmapService.reconcile_failed_skill(db, assessment, profile)
            if assessment.status == "completed":
                assessment = None
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
                verified_grade in GRADE_ORDER
                and GRADE_ORDER.index(grade) > GRADE_ORDER.index(verified_grade)
                and verified_at is not None
            ):
                # После подтверждения нижнего грейда попытка повышения — новый цикл.
                completed_query = completed_query.where(
                    GradeAssessment.created_at >= verified_at
                )
            previous_completed = await db.scalar(
                completed_query.order_by(GradeAssessment.created_at.desc()).limit(1)
            )
            retake_of_id = None
            if previous_completed is not None and not previous_completed.passed:
                retry_used = previous_completed.scoring_policy.get("skill_retry_used", False)
                if not retry_used and previous_completed.retake_of_id is None and datetime.now(timezone.utc) < assessment_expires_at(previous_completed):
                    completed_sessions = (await db.execute(select(TestSession).where(
                        TestSession.assessment_id == previous_completed.id,
                        TestSession.status == "completed",
                    ).order_by(TestSession.created_at.desc()))).scalars().all()
                    latest_by_skill = {item.skill_code: item for item in reversed(completed_sessions)}
                    failed_code = next((code for code, item in latest_by_skill.items()
                        if code in previous_completed.required_skills
                        and item.percentage < previous_completed.scoring_policy["skill"] * 100), None)
                    if failed_code:
                        raise HTTPException(409, f"Пересдайте только навык «{SKILL_LABELS.get(failed_code, failed_code)}» в текущем наборе")
                if previous_completed.retake_of_id is not None or retry_used:
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
                if set(frozen_snapshots) != {code for code, _ in required_skills}:
                    raise HTTPException(409, "Для пересдачи не сохранён полный запасной набор заданий")
                retake_snapshots = {}
            else:
                frozen_snapshots = {}
                retake_snapshots = {}
                for skill_code, _ in required_skills:
                    previous_attempts = await db.scalar(select(func.count(TestSession.id)).where(
                        TestSession.candidate_profile_id == profile.id,
                        TestSession.target_grade == grade,
                        TestSession.skill_code == skill_code,
                    )) or 0
                    frozen_snapshots[skill_code] = [
                        RoadmapService._snapshot_question(code, previous_attempts)
                        for code in question_codes[grade][skill_code]
                    ]
                    retake_snapshots[skill_code] = [
                        RoadmapService._snapshot_question(code, previous_attempts + 1)
                        for code in question_codes[grade][skill_code]
                    ]
            assessment = GradeAssessment(
                user_id=user.id,
                candidate_profile_id=profile.id,
                retake_of_id=retake_of_id,
                specialization=specialization,
                programming_language=language,
                target_grade=grade,
                required_skills=[code for code, _ in required_skills],
                question_codes={
                    code: list(question_codes[grade][code])
                    for code, _ in required_skills
                },
                question_snapshots=frozen_snapshots,
                retake_question_snapshots=retake_snapshots,
                scoring_policy={
                    "overall": OVERALL_MINIMUM, "skill": SKILL_MINIMUM,
                    "open_codes": list(
                        GRADE_RETAKE_OPEN_CODES[specialization][grade]
                        if retake_of_id else GRADE_OPEN_CODES[specialization][grade]
                    ), "open_weight": 10,
                },
            )
            db.add(assessment)
            if specialty_track is not None:
                specialty_track.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(assessment)
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def latest(
        db: AsyncSession, user: User, specialization: str | None = None,
    ) -> GradeAssessmentResponse | None:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None or profile.specialization is None:
            return None
        requested_specialization = normalize_specialization(specialization or profile.specialization)
        if requested_specialization != profile.specialization:
            track = await db.scalar(select(CandidateSpecializationTrack).where(
                CandidateSpecializationTrack.candidate_profile_id == profile.id,
                CandidateSpecializationTrack.specialization == requested_specialization,
            ))
            if track is None:
                return None
        assessment = await db.scalar(
            select(GradeAssessment).where(
                GradeAssessment.user_id == user.id,
                GradeAssessment.specialization == requested_specialization,
                GradeAssessment.programming_language == (profile.programming_language or "Python"),
            )
            .order_by(GradeAssessment.created_at.desc()).limit(1)
        )
        if assessment is None:
            return None
        await RoadmapService.reconcile_failed_skill(db, assessment, profile)
        return await RoadmapService.response(db, assessment, profile)

    @staticmethod
    async def get(db: AsyncSession, user: User, assessment_id: uuid.UUID) -> GradeAssessmentResponse:
        assessment = await db.scalar(select(GradeAssessment).where(
            GradeAssessment.id == assessment_id, GradeAssessment.user_id == user.id,
        ))
        if assessment is None:
            raise HTTPException(404, "Набор тестов не найден")
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        await RoadmapService.reconcile_failed_skill(db, assessment, profile)
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
        retake_used = assessment.scoring_policy.get("skill_retry_used", False) or assessment.retake_of_id is not None or await db.scalar(select(GradeAssessment.id).where(
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
                status=(
                    "review_pending" if submission.evaluation_status == "manual_review"
                    else submission.evaluation_status
                ) if submission else "not_started",
                score=submission.score if submission and submission.evaluation_status == "completed" else None,
                submission_id=submission.id if submission else None,
            ))
        failed_skill = next((skill for skill in skills if skill.percentage is not None
                             and skill.percentage < assessment.scoring_policy["skill"] * 100), None)
        stopped_early = assessment.status == "completed" and failed_skill is not None and (
            any(skill.status != "completed" for skill in skills)
            or any(item.status != "completed" for item in open_questions)
        )
        specialty_track = None
        if assessment.specialization != profile.specialization:
            specialty_track = await db.scalar(select(CandidateSpecializationTrack).where(
                CandidateSpecializationTrack.candidate_profile_id == profile.id,
                CandidateSpecializationTrack.specialization == assessment.specialization,
            ))
        verified_grade = specialty_track.verified_grade if specialty_track else profile.verified_grade
        promotion_at = specialty_track.verified_at if specialty_track else profile.verified_grade_updated_at
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
            percentage=assessment.percentage if assessment.status == "completed" and not stopped_early else None,
            passed=assessment.passed if assessment.status == "completed" else None,
            stopped_early=stopped_early,
            failed_skill=failed_skill.label if stopped_early else None,
            grade_confirmed=assessment.status == "completed" and assessment.passed,
            verified_grade=verified_grade,
            suggested_grade=assessment.suggested_grade,
            completed_at=assessment.completed_at,
            expires_at=assessment_expires_at(assessment),
            retake_used=retake_used,
            retry_available_at=(
                (_utc(assessment.completed_at) + JUNIOR_RETRY_COOLDOWN)
                if (assessment.retake_of_id is not None or assessment.scoring_policy.get("skill_retry_used", False)) and assessment.target_grade == "junior"
                and assessment.status == "completed" and not assessment.passed and assessment.completed_at
                else None
            ),
            promotion_available_at=(
                promotion_at + timedelta(days=90)
                if verified_grade == assessment.target_grade
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
        profile = await db.get(CandidateProfile, assessment.candidate_profile_id)
        await RoadmapService.reconcile_failed_skill(db, assessment, profile)
        if assessment.status not in ("in_progress", "completed"):
            raise HTTPException(409, "Набор уже завершён")
        if assessment.status == "completed" and datetime.now(timezone.utc) >= assessment_expires_at(assessment):
            raise HTTPException(409, "Срок набора истёк. Результаты навыков сохранены в истории")
        if assessment_is_expired(assessment):
            assessment.status = "expired"
            await db.execute(update(TestSession).where(
                TestSession.assessment_id == assessment.id,
                TestSession.status == "in_progress",
            ).values(status="expired"))
            await db.commit()
            raise HTTPException(409, "Срок набора истёк. Откройте новый набор тестов")
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
                if assessment.status == "in_progress" and existing.status == "in_progress":
                    return RoadmapService.session_response(existing)
                raise HTTPException(409, "Начатый тест навыка уже закрыт")
            can_retry = (
                assessment.status == "completed"
                and not assessment.passed
                and existing.percentage < assessment.scoring_policy["skill"] * 100
                and not assessment.scoring_policy.get("skill_retry_used", False)
                and assessment.retake_of_id is None
            )
            if not can_retry:
                raise HTTPException(409, "Этот навык уже завершён или единственная пересдача использована")
            frozen_snapshot = assessment.retake_question_snapshots.get(skill_code, [])
            if not frozen_snapshot:
                raise HTTPException(409, "Для пересдачи навыка не сохранены запасные задания")
            assessment.scoring_policy = {**assessment.scoring_policy, "skill_retry_used": True}
            assessment.status = "in_progress"
            assessment.completed_at = None
            assessment.suggested_grade = None
            assessment.score = 0
            assessment.max_score = 0
            assessment.percentage = 0
        else:
            if assessment.status != "in_progress":
                raise HTTPException(409, "Набор уже завершён")
            frozen_snapshot = assessment.question_snapshots.get(skill_code, [])
        if not frozen_snapshot:
            raise HTTPException(409, "Для этого навыка пока нет полного набора заданий")
        return await RoadmapService._create_skill_session(
            db, user, assessment.candidate_profile_id, assessment.specialization,
            assessment.target_grade, skill_code, assessment.question_codes[skill_code],
            assessment.id, frozen_snapshot=frozen_snapshot,
        )

    @staticmethod
    async def available_additional(
        db: AsyncSession, user: User, specialization: str | None = None,
    ) -> list[AdditionalSkillTestResponse]:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        selected_specialization = normalize_specialization(specialization or profile.specialization)
        specialty_track = None
        if selected_specialization != profile.specialization:
            specialty_track = await db.scalar(select(CandidateSpecializationTrack).where(
                CandidateSpecializationTrack.candidate_profile_id == profile.id,
                CandidateSpecializationTrack.specialization == selected_specialization,
            ))
        verified_grade = specialty_track.verified_grade if specialty_track else (
            profile.verified_grade if profile.verified_specialization == selected_specialization else None
        )
        available = available_extra_skills(selected_specialization or "")
        if not verified_grade:
            return []
        available = [item for item in available if item[2] == verified_grade]
        sessions = (await db.execute(select(TestSession).where(
            TestSession.user_id == user.id,
            TestSession.specialization == selected_specialization,
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
        specialization: str | None = None,
    ) -> TestStartResponse:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id).with_for_update())
        if profile is None:
            raise HTTPException(404, "Сначала заполните профиль кандидата")
        selected_specialization = normalize_specialization(specialization or profile.specialization)
        specialty_track = None
        if selected_specialization != profile.specialization:
            specialty_track = await db.scalar(select(CandidateSpecializationTrack).where(
                CandidateSpecializationTrack.candidate_profile_id == profile.id,
                CandidateSpecializationTrack.specialization == selected_specialization,
            ).with_for_update())
        verified_grade = specialty_track.verified_grade if specialty_track else (
            profile.verified_grade if profile.verified_specialization == selected_specialization else None
        )
        if not verified_grade:
            raise HTTPException(409, "Сначала подтвердите грейд по этой специализации")
        if grade != verified_grade:
            raise HTTPException(400, "Дополнительный навык проверяется на текущем подтверждённом грейде")
        if (skill_code, grade) not in {(code, available_grade) for code, _, available_grade in available_extra_skills(selected_specialization or "")}:
            raise HTTPException(400, "Для этого дополнительного навыка и уровня тест пока недоступен")
        existing = await db.scalar(select(TestSession).where(
            TestSession.user_id == user.id,
            TestSession.specialization == selected_specialization,
            TestSession.assessment_id.is_(None),
            TestSession.skill_code == skill_code,
            TestSession.target_grade == grade,
            TestSession.status == "in_progress",
        ).order_by(TestSession.created_at.desc()).limit(1))
        if existing is not None:
            return RoadmapService.session_response(existing)
        codes = SKILL_QUESTION_CODES[grade][skill_code]
        return await RoadmapService._create_skill_session(
            db, user, profile.id, selected_specialization, grade,
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
            if submission and submission.evaluation_status == "completed":
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
        if weak_skills:
            assessment.status = "completed"
            assessment.passed = False
            assessment.completed_at = datetime.now(timezone.utc)
            assessment.score = sum(item.earned for item in results)
            assessment.max_score = len(assessment.required_skills) * 10 + len(open_codes) * open_weight
            assessment.percentage = round(assessment.score / assessment.max_score * 100, 1)
            index = GRADE_ORDER.index(assessment.target_grade)
            retry_used = assessment.retake_of_id is not None or policy.get("skill_retry_used", False)
            assessment.suggested_grade = GRADE_ORDER[index - 1] if retry_used and index > 0 else None
            await db.execute(update(TestSession).where(
                TestSession.assessment_id == assessment.id,
                TestSession.status == "in_progress",
            ).values(status="cancelled"))
            weak = ", ".join(SKILL_LABELS.get(code, code) for code in weak_skills)
            next_step = (
                "Пересдача использована. Можно попробовать полный набор на уровень ниже."
                if assessment.suggested_grade else
                "Пересдача использована. Новый набор Junior доступен через неделю."
                if retry_used else
                f"Можно один раз пересдать только навык «{weak}» в этом наборе."
            )
            return False, assessment.suggested_grade, (
                f"Набор {'завершён досрочно' if retry_used else 'приостановлен'}: {weak} — результат ниже 50%. " + next_step
            )
        if not decision.complete:
            if all(code in latest_by_skill for code in assessment.required_skills):
                if all(code in open_by_code for code in open_codes) and any(
                    open_by_code[code].evaluation_status == "manual_review" for code in open_codes
                ):
                    assessment.status = "pending_review"
                    return False, None, "Открытый ответ ждёт ручной проверки. Грейд пока не присвоен."
                if all(code in open_by_code for code in open_codes) and any(
                       open_by_code[code].evaluation_status in ("queued", "evaluating", "failed")
                       for code in open_codes if code in open_by_code):
                    # All candidate work was submitted within the three-day window.
                    # Waiting for the evaluator must not expire the finished attempt.
                    assessment.status = "pending_review"
                    return False, None, "Развёрнутые ответы сохранены. Дождитесь автоматической проверки."
                return False, None, "Обязательные навыки пройдены. Решите развёрнутые задания для итоговой оценки."
            return False, assessment.suggested_grade, "Результат навыка сохранён. Продолжите остальные обязательные шаги."

        assessment.score = sum(item.earned for item in results)
        assessment.max_score = sum(item.maximum for item in results)
        assessment.percentage = round(decision.overall_ratio * 100, 1)
        assessment.passed = decision.passed
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)
        if decision.passed:
            if assessment.specialization == profile.specialization:
                grade_changed = profile.verified_grade != assessment.target_grade
                profile.verified_grade = assessment.target_grade
                profile.verified_specialization = assessment.specialization
                if grade_changed:
                    profile.verified_grade_updated_at = assessment.completed_at
            else:
                specialty_track = await db.scalar(select(CandidateSpecializationTrack).where(
                    CandidateSpecializationTrack.candidate_profile_id == profile.id,
                    CandidateSpecializationTrack.specialization == assessment.specialization,
                ).with_for_update())
                if specialty_track is None:
                    raise HTTPException(409, "Запрошенное направление больше недоступно")
                if specialty_track.verified_grade != assessment.target_grade:
                    specialty_track.verified_grade = assessment.target_grade
                    specialty_track.verified_at = assessment.completed_at
            feedback = f"Все обязательные навыки пройдены. Общий результат {assessment.percentage}%; грейд {assessment.target_grade} подтверждён."
        else:
            index = GRADE_ORDER.index(assessment.target_grade)
            retry_used = assessment.retake_of_id is not None or policy.get("skill_retry_used", False)
            assessment.suggested_grade = GRADE_ORDER[index - 1] if retry_used and index > 0 else None
            weak = ", ".join(SKILL_LABELS.get(code, get_open_question_by_code(code)["title"] if get_open_question_by_code(code) else code) for code in decision.below_minimum)
            reason = f" Ниже 50%: {weak}." if weak else ""
            next_step = " Можно один раз пересдать весь набор этого грейда."
            if retry_used:
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
