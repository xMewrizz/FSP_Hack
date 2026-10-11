from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.candidate import CandidateProfile
from app.models.fsp import FSPAchievement
from app.models.resume_version import ResumeVersion
from app.models.test import GradeAssessment, TestSession
from app.models.user import User
from app.schemas.candidate import (
    AdditionalSkillResultItem,
    CandidateOnboardingRequest,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
)
from app.core.assessment_catalog import SKILL_LABELS
from app.schemas.fsp import FSPAchievementSchema
from app.services.fsp_service import fsp_service
from app.services.resume_versions import work_history_lines
from app.services.profile_completeness import calculate_profile_completeness


class CandidateService:
    @staticmethod
    async def complete_onboarding(
        db: AsyncSession, user: User, data: CandidateOnboardingRequest
    ) -> CandidateProfileResponse:
        if not data.agreed_152_fz:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для регистрации на платформе необходимо согласие на обработку персональных данных (152-ФЗ)",
            )
        if data.fsp_id and data.fsp_id.strip() and not data.agreed_fsp_id_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для привязки ID участника ФСП необходимо отдельное согласие.",
            )

        stmt = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.user_id == user.id)
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            profile = CandidateProfile(user_id=user.id)
            db.add(profile)

        now = datetime.now(timezone.utc)
        profile.first_name = data.first_name
        profile.last_name = data.last_name
        profile.middle_name = data.middle_name
        profile.phone = data.phone
        profile.telegram = data.telegram
        profile.city = data.city
        profile.bio = data.bio
        profile.github_url = data.github_url

        has_python_roadmap = data.specialization in ("Backend", "Data Science / ML")
        new_language = data.programming_language or ("Python" if has_python_roadmap else None)
        if has_python_roadmap and new_language != "Python":
            raise HTTPException(400, "Для этой специализации пока подготовлен только базовый тест на Python")
        if profile.specialization and (profile.specialization != data.specialization or profile.programming_language != new_language):
            profile.verified_grade = None
            profile.verified_specialization = None
            profile.verified_grade_updated_at = None
            await db.execute(update(GradeAssessment).where(
                GradeAssessment.candidate_profile_id == profile.id,
                GradeAssessment.specialization == profile.specialization,
                GradeAssessment.status == "in_progress",
            ).values(status="cancelled"))
            await db.execute(update(TestSession).where(
                TestSession.candidate_profile_id == profile.id,
                TestSession.specialization == profile.specialization,
                TestSession.assessment_id.is_not(None),
                TestSession.status == "in_progress",
            ).values(status="cancelled"))
        profile.specialization = data.specialization
        profile.programming_language = new_language
        profile.declared_grade = data.declared_grade.value
        profile.work_format = data.work_format.value
        profile.salary_expectation = data.salary_expectation
        profile.salary_tax_type = data.salary_tax_type
        if data.skills is not None:
            profile.skills = list(data.skills)

        profile.agreed_152_fz = True
        profile.agreed_152_fz_at = now
        if data.visibility_public and not data.agreed_publication:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Чтобы показывать профиль работодателям, нужно отдельное согласие на публикацию.",
            )
        profile.agreed_publication = data.agreed_publication
        profile.agreed_publication_at = now if data.agreed_publication else None
        profile.visibility_public = data.visibility_public and data.agreed_publication
        profile.agreed_fsp_id_link = data.agreed_fsp_id_link
        profile.agreed_fsp_id_link_at = now if data.agreed_fsp_id_link else None
        if data.agreed_osint is not None:
            profile.agreed_osint = data.agreed_osint
            profile.agreed_osint_at = now if data.agreed_osint else None

        if data.fsp_id and data.fsp_id.strip():
            fsp_clean = data.fsp_id.strip().upper()
            profile.fsp_id = fsp_clean
            profile.fsp_achievements.clear()
            v_res = await fsp_service.verify_fsp_id(fsp_clean)
            if v_res.found:
                profile.fsp_verified = True
                for ach in v_res.achievements:
                    achievement = FSPAchievement(
                        candidate_profile_id=profile.id,
                        fsp_id=fsp_clean,
                        tournament_name=ach.tournament_name,
                        year=ach.year,
                        rank_or_place=ach.rank_or_place,
                        sport_category=ach.sport_category,
                        score_or_rating=ach.score_or_rating,
                        verified=ach.verified,
                    )
                    db.add(achievement)
            else:
                profile.fsp_verified = False
        else:
            profile.fsp_id = None
            profile.fsp_verified = False
            profile.fsp_achievements.clear()

        profile.onboarding_completed = True
        await db.commit()
        await db.refresh(profile)

        stmt_reload = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.id == profile.id)
        )
        res_reload = await db.execute(stmt_reload)
        fresh_profile = res_reload.scalar_one()
        extra_skills = await CandidateService._load_additional_skills(db, fresh_profile.id)
        return CandidateService._build_response(fresh_profile, user.email, user.is_verified, extra_skills)

    @staticmethod
    async def get_profile(db: AsyncSession, user: User) -> CandidateProfileResponse:
        stmt = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.user_id == user.id)
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль кандидата не найден",
            )

        extra_skills = await CandidateService._load_additional_skills(db, profile.id)
        return CandidateService._build_response(profile, user.email, user.is_verified, extra_skills)

    @staticmethod
    async def update_profile(
        db: AsyncSession, user: User, data: CandidateProfileUpdateRequest
    ) -> CandidateProfileResponse:
        stmt = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.user_id == user.id)
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль кандидата не найден",
            )

        update_dict = data.model_dump(exclude_unset=True)
        target_specialization = update_dict.get("specialization", profile.specialization)
        target_language = update_dict.get("programming_language", profile.programming_language)
        if target_specialization != profile.specialization and "programming_language" not in update_dict:
            target_language = None
        if target_specialization in ("Backend", "Data Science / ML"):
            target_language = target_language or "Python"
            if target_language != "Python":
                raise HTTPException(400, "Для этой специализации пока подготовлен только базовый тест на Python")
        if target_specialization != profile.specialization or target_language != profile.programming_language:
            profile.verified_grade = None
            profile.verified_specialization = None
            profile.verified_grade_updated_at = None
            await db.execute(update(GradeAssessment).where(
                GradeAssessment.candidate_profile_id == profile.id,
                GradeAssessment.status == "in_progress",
            ).values(status="cancelled"))
            await db.execute(update(TestSession).where(
                TestSession.candidate_profile_id == profile.id,
                TestSession.assessment_id.is_not(None),
                TestSession.status == "in_progress",
            ).values(status="cancelled"))
        update_dict["programming_language"] = target_language
        publication = update_dict.get("agreed_publication", profile.agreed_publication)
        visibility = update_dict.get("visibility_public", profile.visibility_public)
        if update_dict.get("fsp_id") and not update_dict.get("agreed_fsp_id_link", profile.agreed_fsp_id_link):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для привязки ID участника ФСП необходимо отдельное согласие.",
            )
        if visibility and not publication and update_dict.get("visibility_public") is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Чтобы показывать профиль работодателям, нужно отдельное согласие на публикацию.",
            )
        if "agreed_publication" in update_dict:
            profile.agreed_publication_at = datetime.now(timezone.utc) if publication else None
            if not publication:
                update_dict["visibility_public"] = False
        if "agreed_fsp_id_link" in update_dict:
            consent = update_dict["agreed_fsp_id_link"]
            profile.agreed_fsp_id_link_at = datetime.now(timezone.utc) if consent else None
            if not consent and profile.agreed_fsp_id_link:
                profile.fsp_id = None
                profile.fsp_verified = False
                await db.execute(delete(FSPAchievement).where(FSPAchievement.candidate_profile_id == profile.id))
        if "agreed_test_confidentiality" in update_dict:
            consent = update_dict["agreed_test_confidentiality"]
            profile.agreed_test_confidentiality_at = datetime.now(timezone.utc) if consent else None
        if "agreed_osint" in update_dict:
            consent = update_dict["agreed_osint"]
            profile.agreed_osint_at = datetime.now(timezone.utc) if consent else None
        if "resume_text" in update_dict and (update_dict["resume_text"] or "") != (profile.resume_text or ""):
            previous = await db.scalar(
                select(ResumeVersion).where(ResumeVersion.candidate_profile_id == profile.id)
                .order_by(ResumeVersion.created_at.desc(), ResumeVersion.id.desc())
            )
            if profile.resume_text and (previous is None or previous.text != profile.resume_text):
                db.add(ResumeVersion(
                    candidate_profile_id=profile.id, text=profile.resume_text,
                    work_lines=work_history_lines(profile.resume_text),
                ))
            if update_dict["resume_text"]:
                db.add(ResumeVersion(
                    candidate_profile_id=profile.id, text=update_dict["resume_text"],
                    work_lines=work_history_lines(update_dict["resume_text"]),
                ))
        for key, value in update_dict.items():
            if key == "work_format" and value:
                profile.work_format = value.value if hasattr(value, "value") else value
            elif key == "declared_grade" and value:
                profile.declared_grade = value.value if hasattr(value, "value") else value
            elif hasattr(profile, key):
                setattr(profile, key, value)

        await db.commit()
        await db.refresh(profile)
        refreshed = await db.execute(
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.id == profile.id)
        )
        refreshed_prof = refreshed.scalar_one()
        extra_skills = await CandidateService._load_additional_skills(db, refreshed_prof.id)
        return CandidateService._build_response(refreshed_prof, user.email, user.is_verified, extra_skills)

    @staticmethod
    async def link_fsp_id(
        db: AsyncSession, user: User, fsp_id: str
    ) -> CandidateProfileResponse:
        stmt = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.user_id == user.id)
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль кандидата не найден",
            )

        if not profile.agreed_fsp_id_link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для привязки ID участника ФСП необходимо отдельное согласие.",
            )

        fsp_clean = fsp_id.strip().upper()
        profile.fsp_id = fsp_clean
        v_res = await fsp_service.verify_fsp_id(fsp_clean)

        await db.execute(delete(FSPAchievement).where(FSPAchievement.candidate_profile_id == profile.id))
        if v_res.found:
            profile.fsp_verified = True
            for ach in v_res.achievements:
                achievement = FSPAchievement(
                    candidate_profile_id=profile.id,
                    fsp_id=fsp_clean,
                    tournament_name=ach.tournament_name,
                    year=ach.year,
                    rank_or_place=ach.rank_or_place,
                    sport_category=ach.sport_category,
                    score_or_rating=ach.score_or_rating,
                    verified=ach.verified,
                    is_demo=True,
                    disclaimer="Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП",
                )
                db.add(achievement)
        else:
            profile.fsp_verified = False

        await db.commit()
        refreshed = await db.execute(
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.id == profile.id)
            .execution_options(populate_existing=True)
        )
        refreshed_prof = refreshed.scalar_one()
        extra_skills = await CandidateService._load_additional_skills(db, refreshed_prof.id)
        return CandidateService._build_response(refreshed_prof, user.email, user.is_verified, extra_skills)

    @staticmethod
    async def unlink_fsp_id(db: AsyncSession, user: User) -> CandidateProfileResponse:
        result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(status_code=404, detail="Профиль кандидата не найден")
        profile.fsp_id = None
        profile.fsp_verified = False
        await db.execute(delete(FSPAchievement).where(FSPAchievement.candidate_profile_id == profile.id))
        await db.commit()
        refreshed = await db.execute(
            select(CandidateProfile).options(selectinload(CandidateProfile.fsp_achievements))
            .where(CandidateProfile.id == profile.id).execution_options(populate_existing=True)
        )
        refreshed_prof = refreshed.scalar_one()
        extra_skills = await CandidateService._load_additional_skills(db, refreshed_prof.id)
        return CandidateService._build_response(refreshed_prof, user.email, user.is_verified, extra_skills)

    @staticmethod
    async def _load_additional_skills(
        db: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> list[AdditionalSkillResultItem]:
        stmt = (
            select(TestSession)
            .where(
                TestSession.candidate_profile_id == candidate_profile_id,
                TestSession.assessment_id.is_(None),
                TestSession.skill_code.is_not(None),
                TestSession.target_grade == "all",
                TestSession.status == "completed",
                TestSession.passed.is_(True),
            )
            .order_by(TestSession.completed_at.desc(), TestSession.created_at.desc())
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()
        seen = set()
        items: list[AdditionalSkillResultItem] = []
        for s in sessions:
            if s.skill_code and s.skill_code not in seen:
                seen.add(s.skill_code)
                label = SKILL_LABELS.get(s.skill_code, s.skill_code)
                items.append(
                    AdditionalSkillResultItem(
                        code=s.skill_code,
                        label=label,
                        percentage=s.percentage,
                        level_out_of_ten=round(s.percentage / 10, 1),
                        target_grade=s.target_grade,
                        completed_at=s.completed_at,
                    )
                )
        return items

    @staticmethod
    def _build_response(
        profile: CandidateProfile,
        email: str,
        email_verified: bool,
        additional_skills: list[AdditionalSkillResultItem] | None = None,
    ) -> CandidateProfileResponse:
        return CandidateProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            email=email,
            email_verified=email_verified,
            profile_completeness=calculate_profile_completeness(profile, email_verified=email_verified),
            first_name=profile.first_name,
            last_name=profile.last_name,
            middle_name=profile.middle_name,
            phone=profile.phone,
            telegram=profile.telegram,
            bio=profile.bio,
            hobbies=profile.hobbies,
            city=profile.city,
            github_url=profile.github_url,
            resume_url=profile.resume_url,
            resume_text=profile.resume_text,
            photo_url="/candidate/profile/photo" if profile.photo_filename else None,
            specialization=profile.specialization,
            programming_language=profile.programming_language,
            declared_grade=profile.declared_grade,
            verified_grade=profile.verified_grade,
            verified_specialization=profile.verified_specialization,
            work_format=profile.work_format,
            salary_expectation=profile.salary_expectation,
            salary_tax_type=getattr(profile, "salary_tax_type", "gross") or "gross",
            skills=profile.skills or [],
            education_level=profile.education_level,
            university_course=profile.university_course,
            birth_year=profile.birth_year,
            fsp_id=profile.fsp_id,
            fsp_verified=profile.fsp_verified,
            agreed_152_fz=profile.agreed_152_fz,
            agreed_publication=profile.agreed_publication,
            agreed_fsp_id_link=profile.agreed_fsp_id_link,
            agreed_test_confidentiality=profile.agreed_test_confidentiality,
            visibility_public=profile.visibility_public,
            mentor_available=profile.mentor_available,
            agreed_osint=profile.agreed_osint,
            onboarding_completed=profile.onboarding_completed,
            last_active_at=profile.last_active_at,
            achievements=[
                FSPAchievementSchema.model_validate(ach) for ach in profile.fsp_achievements
            ],
            additional_skills=additional_skills or [],
        )


candidate_service = CandidateService()
