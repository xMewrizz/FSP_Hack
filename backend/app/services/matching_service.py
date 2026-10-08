from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.candidate import CandidateProfile
from app.models.fsp import FSPAchievement
from app.models.need import EmployerNeed
from app.models.test import TestSession
from app.models.user import User
from app.schemas.matching import (
    CandidateMatchItem,
    MatchExplanation,
    MatchingCandidatesResponse,
)

GRADE_WEIGHTS = {
    "junior": 1,
    "middle": 2,
    "senior": 3,
    "lead": 4,
}


def _matches_skill(req_name: str, cand_skills: set[str], bio_text: str) -> bool:
    if req_name in cand_skills:
        return True
    if bio_text and req_name in bio_text:
        return True
    req_words = {w for w in req_name.replace("&", " ").replace("/", " ").replace(",", " ").split() if len(w) > 1}
    for cand_s in cand_skills:
        if req_name == cand_s:
            return True
        cand_words = {w for w in cand_s.replace("&", " ").replace("/", " ").replace(",", " ").split() if len(w) > 1}
        if req_words and cand_words and (req_words <= cand_words or cand_words <= req_words):
            return True
        if len(req_name) >= 3 and (f" {req_name} " in f" {cand_s} " or cand_s.startswith(f"{req_name} ") or cand_s.endswith(f" {req_name}")):
            return True
        if len(cand_s) >= 3 and (f" {cand_s} " in f" {req_name} " or req_name.startswith(f"{cand_s} ") or req_name.endswith(f" {cand_s}")):
            return True
    return False


class MatchingService:
    @staticmethod
    async def match_candidates_for_need(
        db: AsyncSession, need_id: uuid.UUID, current_user: User | None = None
    ) -> MatchingCandidatesResponse:
        stmt_need = (
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.employer))
            .where(EmployerNeed.id == need_id)
        )
        res_need = await db.execute(stmt_need)
        need = res_need.scalar_one_or_none()

        if not need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Потребность не найдена",
            )

        if current_user and need.employer and need.employer.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав для просмотра подбора по чужой потребности",
            )

        stmt_cand = (
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.fsp_achievements),
                selectinload(CandidateProfile.test_sessions),
            )
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
            )
        )
        res_cand = await db.execute(stmt_cand)
        candidates = res_cand.scalars().all()

        scored_candidates: list[CandidateMatchItem] = []

        req_grade_val = GRADE_WEIGHTS.get((need.required_grade or "").lower(), 1)
        
        # 1. Parse required skills with weights
        req_skills_items: list[tuple[str, float]] = []
        for s in (need.required_skills or []):
            if isinstance(s, dict):
                name = (s.get("name") or "").strip().lower()
                if not name:
                    continue
                try:
                    w = float(s.get("weight", 1.0))
                except (ValueError, TypeError):
                    w = 1.0
                req_skills_items.append((name, max(0.1, w)))

        need_tax = (getattr(need, "salary_tax_type", "gross") or "gross").lower()
        tax_labels = {
            "gross": "до вычета НДФЛ",
            "net": "на руки",
        }
        need_tax_label = tax_labels.get(need_tax, need_tax)

        for cand in candidates:
            # 1. Grade match score (max 35)
            cand_grade_str = (cand.verified_grade or cand.declared_grade or "junior").lower()
            cand_grade_val = GRADE_WEIGHTS.get(cand_grade_str, 1)

            grade_matched = False
            if cand.verified_grade and cand_grade_val >= req_grade_val:
                grade_score = 35.0
                grade_matched = True
            elif cand.verified_grade and cand_grade_val == req_grade_val - 1:
                grade_score = 22.0
            elif cand.declared_grade and cand_grade_val >= req_grade_val:
                grade_score = 20.0
            else:
                grade_score = 12.0

            # 2. Skills match score with dynamic weights (max 35)
            cand_skills_normalized = {s.lower() for s in (cand.skills or [])}
            bio_text = (cand.bio or "").lower()

            matched_skills = []
            missing_skills = []
            matched_weight = 0.0
            total_weight = sum(w for _, w in req_skills_items)

            if req_skills_items:
                for req_name, req_w in req_skills_items:
                    if _matches_skill(req_name, cand_skills_normalized, bio_text):
                        matched_skills.append(req_name.capitalize())
                        matched_weight += req_w
                    else:
                        missing_skills.append(req_name.capitalize())
                skills_ratio = matched_weight / total_weight if total_weight > 0 else 0.0
                skills_score = round(skills_ratio * 35.0, 1)
            else:
                skills_score = 30.0

            # 3. Work format & location (max 10)
            format_score = 7.0
            if cand.work_format == "remote" or need.work_format == "remote":
                format_score = 10.0
            elif cand.work_format == need.work_format:
                format_score = 10.0

            if need.city and cand.city and need.city.lower() == cand.city.lower():
                format_score = min(10.0, format_score + 2.0)

            # 4. Salary expectations & Tax type matching (max 10)
            cand_tax = (getattr(cand, "salary_tax_type", "gross") or "gross").lower()
            cand_tax_label = tax_labels.get(cand_tax, cand_tax)
            cand_salary = cand.salary_expectation

            if cand_salary is None:
                salary_match = None
                salary_note = "Ожидания по зарплате не указаны (договорная)"
                salary_score = 5.0
            else:
                if cand_tax == need_tax:
                    if cand_salary <= need.salary_max:
                        salary_match = True
                        salary_note = (
                            f"Ожидания ({int(cand_salary):,} ₽ {need_tax_label}) "
                            f"укладываются в бюджет вакансии (до {int(need.salary_max):,} ₽)"
                        )
                        salary_score = 10.0
                    else:
                        salary_match = False
                        salary_note = (
                            f"Ожидания ({int(cand_salary):,} ₽ {need_tax_label}) "
                            f"выше максимума ({int(need.salary_max):,} ₽)"
                        )
                        salary_score = 0.0
                else:
                    salary_match = False
                    salary_note = (
                        f"Разный налоговый базис: потребность «{need_tax_label}», "
                        f"соискатель «{cand_tax_label}»"
                    )
                    salary_score = 2.0

            # 5. FSP bonus (max 10)
            fsp_bonus = False
            fsp_score = 0.0
            fsp_category = None
            fsp_rating = None

            if cand.fsp_verified:
                fsp_bonus = True
                fsp_score = 10.0
                if cand.fsp_achievements:
                    top_ach = cand.fsp_achievements[0]
                    fsp_category = top_ach.sport_category
                    fsp_rating = top_ach.score_or_rating

            total_score = round(min(100.0, grade_score + skills_score + format_score + salary_score + fsp_score), 1)

            # Summary formulation
            summary_parts = []
            if cand.verified_grade:
                summary_parts.append(f"Подтверждённый уровень: {cand.verified_grade.capitalize()}.")
            else:
                summary_parts.append(f"Заявленный уровень: {cand.declared_grade or 'junior'}.")

            if matched_skills:
                summary_parts.append(f"Совпадение по стеку: {', '.join(matched_skills)}.")
            if missing_skills:
                summary_parts.append(f"Требуется уточнить: {', '.join(missing_skills)}.")
            if salary_match is True:
                summary_parts.append(f"Зарплатные ожидания соответствуют («{need_tax_label}»).")
            elif salary_match is False:
                if cand_tax != need_tax:
                    summary_parts.append(f"Требуется согласование налогового типа («{cand_tax_label}» vs «{need_tax_label}»).")
                else:
                    summary_parts.append("Зарплатные ожидания превышают максимум вилки.")
            if fsp_bonus:
                summary_parts.append("Участник соревнований ФСП (высокий алгоритмический рейтинг).")

            explanation = MatchExplanation(
                grade_match=grade_matched,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
                fsp_bonus=fsp_bonus,
                salary_match=salary_match,
                salary_note=salary_note,
                summary=" ".join(summary_parts),
            )

            # Latest test percentage
            test_perc = None
            if cand.test_sessions:
                test_perc = cand.test_sessions[0].percentage

            item = CandidateMatchItem(
                candidate_id=cand.id,
                first_name=cand.first_name,
                last_name=cand.last_name,
                specialization=cand.specialization,
                verified_grade=cand.verified_grade,
                declared_grade=cand.declared_grade,
                city=cand.city,
                work_format=cand.work_format,
                fsp_id=cand.fsp_id,
                fsp_verified=cand.fsp_verified,
                fsp_sport_category=fsp_category,
                fsp_rating=fsp_rating,
                achievements_count=len(cand.fsp_achievements),
                skills=cand.skills or [],
                salary_expectation=cand.salary_expectation,
                salary_tax_type=getattr(cand, "salary_tax_type", "gross") or "gross",
                test_percentage=test_perc,
                match_score=total_score,
                match_explanation=explanation,
            )
            scored_candidates.append(item)

        # Sort descending: verified candidates strictly first (ТЗ: неподтвержденные идут после подтвержденных), then by match_score
        scored_candidates.sort(
            key=lambda x: (x.verified_grade is not None, x.match_score),
            reverse=True,
        )

        return MatchingCandidatesResponse(
            need_id=need.id,
            need_title=need.title,
            total=len(scored_candidates),
            candidates=scored_candidates,
        )

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
            .options(
                selectinload(CandidateProfile.fsp_achievements),
                selectinload(CandidateProfile.test_sessions),
            )
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
            )
        )

        if specialization:
            stmt = stmt.where(CandidateProfile.specialization == specialization)
        if grade:
            stmt = stmt.where(
                (CandidateProfile.verified_grade == grade)
                | (CandidateProfile.declared_grade == grade)
            )
        if work_format:
            stmt = stmt.where(CandidateProfile.work_format == work_format)
        if city:
            stmt = stmt.where(CandidateProfile.city.ilike(f"%{city}%"))
        if fsp_only:
            stmt = stmt.where(CandidateProfile.fsp_verified.is_(True))

        res = await db.execute(stmt)
        candidates = res.scalars().all()

        results = []
        for cand in candidates:
            test_perc = cand.test_sessions[0].percentage if cand.test_sessions else None
            top_ach = cand.fsp_achievements[0] if cand.fsp_achievements else None

            results.append(
                CandidateMatchItem(
                    candidate_id=cand.id,
                    first_name=cand.first_name,
                    last_name=cand.last_name,
                    specialization=cand.specialization,
                    verified_grade=cand.verified_grade,
                    declared_grade=cand.declared_grade,
                    city=cand.city,
                    work_format=cand.work_format,
                    fsp_id=cand.fsp_id,
                    fsp_verified=cand.fsp_verified,
                    fsp_sport_category=top_ach.sport_category if top_ach else None,
                    fsp_rating=top_ach.score_or_rating if top_ach else None,
                    achievements_count=len(cand.fsp_achievements),
                    skills=cand.skills or [],
                    salary_expectation=cand.salary_expectation,
                    salary_tax_type=getattr(cand, "salary_tax_type", "gross") or "gross",
                    test_percentage=test_perc,
                    match_score=test_perc or 80.0,
                    match_explanation=MatchExplanation(
                        grade_match=bool(cand.verified_grade),
                        matched_skills=cand.skills or [],
                        missing_skills=[],
                        fsp_bonus=cand.fsp_verified,
                        summary="Найдено в банке кандидатов по заданным фильтрам.",
                    ),
                )
            )

        results.sort(
            key=lambda x: (x.verified_grade is not None, x.match_score),
            reverse=True,
        )
        return results


matching_service = MatchingService()
