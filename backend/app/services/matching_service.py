"""Выдача кандидатов работодателю по подтверждённой категории."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ranking import rank_candidates
from app.models.candidate import CandidateProfile
from app.models.need import EmployerNeed
from app.models.test import GradeAssessment
from app.models.user import User
from app.schemas.matching import CandidateMatchItem, MatchExplanation, MatchingCandidatesResponse


def _candidate_data(candidate: CandidateProfile, percentage: float | None) -> dict:
    return {
        "id": candidate.id,
        "specialization": candidate.verified_specialization or candidate.specialization,
        "verified_grade": candidate.verified_grade,
        "declared_grade": candidate.declared_grade,
        "skills": candidate.skills or [],
        "test_percentage": percentage,
        "work_format": candidate.work_format,
        "city": candidate.city,
        "salary_expectation": candidate.salary_expectation,
        "salary_tax_type": candidate.salary_tax_type,
        "fsp_verified": candidate.fsp_verified,
        "fsp_achievements": [
            {"id": str(item.id)}
            for item in candidate.fsp_achievements
            if item.verified
        ],
    }


def _need_data(need: EmployerNeed) -> dict:
    return {
        "specialization": need.specialization,
        "required_grade": need.required_grade,
        "required_skills": need.required_skills or [],
        "work_format": need.work_format,
        "city": need.city,
        "salary_max": need.salary_max,
        "salary_tax_type": need.salary_tax_type,
    }


def _match_item(candidate: CandidateProfile, score: dict, percentage: float | None, need: EmployerNeed) -> CandidateMatchItem:
    tax_labels = {"gross": "до вычета НДФЛ", "net": "на руки"}
    candidate_tax = tax_labels.get(candidate.salary_tax_type, candidate.salary_tax_type)
    need_tax = tax_labels.get(need.salary_tax_type, need.salary_tax_type)
    if candidate.salary_expectation is None:
        salary_note = "Ожидания по зарплате не указаны"
    elif candidate.salary_tax_type != need.salary_tax_type:
        salary_note = f"Разный налоговый базис: кандидат — {candidate_tax}, потребность — {need_tax}"
    elif score["salary_match"]:
        salary_note = "Ожидания по зарплате укладываются в бюджет"
    else:
        salary_note = "Ожидания по зарплате выше максимума бюджета"

    matched = score["matched_skills"]
    missing = score["missing_skills"]
    summary = [f"Подтверждён {candidate.verified_grade.capitalize()} по направлению {candidate.verified_specialization or candidate.specialization}."]
    if matched:
        summary.append(f"Совпали навыки: {', '.join(matched)}.")
    if missing:
        summary.append(f"Не указаны навыки: {', '.join(missing)}.")
    if score["salary_match"]:
        summary.append("Зарплатные ожидания соответствуют бюджету.")
    elif candidate.salary_expectation is not None and candidate.salary_tax_type != need.salary_tax_type:
        summary.append("Требуется согласование налогового типа зарплаты.")
    else:
        summary.append(salary_note + ".")
    if score["fsp_bonus"]:
        summary.append("Учтено достижение ФСП.")
    top_achievement = next((item for item in candidate.fsp_achievements if item.verified), None)

    return CandidateMatchItem(
        candidate_id=candidate.id,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        specialization=candidate.specialization,
        verified_grade=candidate.verified_grade,
        declared_grade=candidate.declared_grade,
        city=candidate.city,
        work_format=candidate.work_format,
        fsp_id=candidate.fsp_id,
        fsp_verified=candidate.fsp_verified,
        fsp_sport_category=top_achievement.sport_category if top_achievement else None,
        fsp_rating=top_achievement.score_or_rating if top_achievement else None,
        achievements_count=len(candidate.fsp_achievements),
        skills=candidate.skills or [],
        salary_expectation=candidate.salary_expectation,
        salary_tax_type=candidate.salary_tax_type,
        test_percentage=percentage,
        match_score=score["points"],
        match_explanation=MatchExplanation(
            grade_match=True,
            matched_skills=matched,
            missing_skills=missing,
            fsp_bonus=score["fsp_bonus"],
            salary_match=(False if candidate.salary_expectation is not None and candidate.salary_tax_type != need.salary_tax_type else score["salary_match"]),
            salary_note=salary_note,
            summary=" ".join(summary),
        ),
    )


class MatchingService:
    @staticmethod
    async def match_candidates_for_need(
        db: AsyncSession, need_id: uuid.UUID, current_user: User | None = None
    ) -> MatchingCandidatesResponse:
        need = await db.scalar(
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.employer))
            .where(EmployerNeed.id == need_id)
        )
        if need is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Потребность не найдена")
        if current_user and need.employer and need.employer.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чужая потребность недоступна")

        candidates = (await db.scalars(
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements), selectinload(CandidateProfile.test_sessions))
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
                CandidateProfile.verified_grade.is_not(None),
            )
        )).all()
        if not candidates:
            return MatchingCandidatesResponse(need_id=need.id, need_title=need.title, total=0, candidates=[])

        by_id = {item.id: item for item in candidates}
        assessments = (await db.scalars(
            select(GradeAssessment)
            .where(
                GradeAssessment.candidate_profile_id.in_([item.id for item in candidates]),
                GradeAssessment.status == "completed",
                GradeAssessment.passed.is_(True),
            )
            .order_by(GradeAssessment.completed_at.desc())
        )).all()
        confirmed_results: dict[uuid.UUID, float] = {}
        for assessment in assessments:
            candidate = by_id.get(assessment.candidate_profile_id)
            if (
                candidate is not None
                and candidate.id not in confirmed_results
                and assessment.target_grade.casefold() == (candidate.verified_grade or "").casefold()
                and assessment.specialization.casefold() == (candidate.verified_specialization or candidate.specialization or "").casefold()
            ):
                confirmed_results[candidate.id] = assessment.percentage

        for candidate in candidates:
            if candidate.id in confirmed_results:
                continue
            legacy_result = next((session for session in candidate.test_sessions if (
                session.assessment_id is None
                and session.status == "completed"
                and session.passed
                and session.target_grade.casefold() == (candidate.verified_grade or "").casefold()
                and session.specialization.casefold() == (candidate.verified_specialization or candidate.specialization or "").casefold()
            )), None)
            if legacy_result is not None:
                confirmed_results[candidate.id] = legacy_result.percentage

        ranked = rank_candidates(
            _need_data(need),
            [_candidate_data(item, confirmed_results.get(item.id)) for item in candidates],
        )
        items = [
            _match_item(by_id[result["candidate_id"]], result, confirmed_results.get(result["candidate_id"]), need)
            for result in ranked
        ]
        return MatchingCandidatesResponse(need_id=need.id, need_title=need.title, total=len(items), candidates=items)

    @staticmethod
    async def search_candidates(
        db: AsyncSession,
        specialization: str | None = None,
        grade: str | None = None,
        work_format: str | None = None,
        city: str | None = None,
        fsp_only: bool = False,
    ) -> list[CandidateMatchItem]:
        stmt = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.fsp_achievements))
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
                CandidateProfile.verified_grade.is_not(None),
            )
        )
        if specialization:
            stmt = stmt.where(CandidateProfile.specialization == specialization)
        if grade:
            stmt = stmt.where(CandidateProfile.verified_grade == grade)
        if work_format:
            stmt = stmt.where(CandidateProfile.work_format == work_format)
        if city:
            stmt = stmt.where(CandidateProfile.city.ilike(f"%{city}%"))
        if fsp_only:
            stmt = stmt.where(CandidateProfile.fsp_verified.is_(True))

        candidates = (await db.scalars(stmt)).all()
        return [
            CandidateMatchItem(
                candidate_id=candidate.id,
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                specialization=candidate.specialization,
                verified_grade=candidate.verified_grade,
                declared_grade=candidate.declared_grade,
                city=candidate.city,
                work_format=candidate.work_format,
                fsp_id=candidate.fsp_id,
                fsp_verified=candidate.fsp_verified,
                fsp_sport_category=candidate.fsp_achievements[0].sport_category if candidate.fsp_achievements else None,
                fsp_rating=candidate.fsp_achievements[0].score_or_rating if candidate.fsp_achievements else None,
                achievements_count=len(candidate.fsp_achievements),
                skills=candidate.skills or [],
                salary_expectation=candidate.salary_expectation,
                salary_tax_type=candidate.salary_tax_type,
                test_percentage=None,
                match_score=0,
                match_explanation=MatchExplanation(
                    grade_match=True,
                    matched_skills=[],
                    missing_skills=[],
                    fsp_bonus=bool(candidate.fsp_verified and candidate.fsp_achievements),
                    summary="Кандидат с подтверждённой категорией. Балл для конкретной потребности здесь не рассчитывается.",
                ),
            )
            for candidate in candidates
        ]


matching_service = MatchingService()
