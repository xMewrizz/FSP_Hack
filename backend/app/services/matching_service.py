"""Выдача кандидатов работодателю по подтверждённой категории."""

import uuid
from datetime import datetime, timezone
from typing import Any
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload, selectinload

from app.core.ranking import rank_candidates
from app.core.assessment_catalog import BACKEND_MATCHING_SKILL_CODES
from app.core.assessment_catalog_ds import DS_MATCHING_SKILL_CODES
from app.models.candidate import CandidateProfile
from app.models.candidate_specialization import CandidateSpecializationTrack
from app.models.need import EmployerNeed
from app.models.test import GradeAssessment, TestSession
from app.models.user import User
from app.schemas.matching import CandidateMatchItem, MatchExplanation, MatchingCandidatesResponse, RequestedSkillTestResult
from app.services.profile_completeness import calculate_profile_completeness


def _parse_need_requirements(need: EmployerNeed) -> dict[str, tuple[str, float]]:
    requirements: dict[str, tuple[str, float]] = {}
    for item in need.required_skills or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        try:
            weight = float(item.get("weight", 1))
        except (TypeError, ValueError):
            continue
        if name and weight > 0:
            key = name.casefold()
            previous = requirements.get(key)
            requirements[key] = (previous[0] if previous else name, max(weight, previous[1] if previous else 0))
    return requirements


def _requested_skill_tests_dict(
    requirements: dict[str, tuple[str, float]],
    aliases: dict[str, str],
    base_sessions: dict[str, Any],
    additional_sessions: dict[str, Any],
) -> list[dict]:
    results = []
    for key, (name, weight) in requirements.items():
        code = aliases.get(key)
        base_session = base_sessions.get(code) if code else None
        session = base_session or (additional_sessions.get(code) if code else None)
        results.append({
            "name": name,
            "weight": weight,
            "percentage": session.percentage if session else None,
            "test_grade": session.target_grade if base_session else None,
            "test_kind": ("base" if base_session else "additional") if session else None,
            "completed_at": session.completed_at if session else None,
        })
    return results


def _candidate_data(candidate: CandidateProfile, percentage: float | None, requested_skill_tests: list[dict], specialization: str | None = None, grade: str | None = None) -> dict:
    return {
        "id": candidate.id,
        "specialization": specialization or candidate.verified_specialization or candidate.specialization,
        "verified_grade": grade or candidate.verified_grade,
        "declared_grade": candidate.declared_grade,
        "skills": candidate.skills or [],
        "test_percentage": percentage,
        "requested_skill_tests": requested_skill_tests,
        "work_format": candidate.work_format,
        "city": candidate.city,
        "salary_expectation": candidate.salary_expectation,
        "salary_tax_type": candidate.salary_tax_type,
        "fsp_verified": candidate.fsp_verified,
        "fsp_achievements": [
            {"id": str(item.id), "verified": item.verified, "is_demo": item.is_demo}
            for item in candidate.fsp_achievements
        ],
    }


def _candidate_activity_status(last_active_at: datetime | None) -> str:
    if last_active_at is None:
        return "Нет отметки об активности"
    timestamp = last_active_at.replace(tzinfo=timezone.utc) if last_active_at.tzinfo is None else last_active_at
    days_since_activity = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds() / 86400
    if days_since_activity < 7:
        return "Активен"
    if days_since_activity < 30:
        return "Недавно активен"
    if days_since_activity < 60:
        return "Устаревает"
    return "Не активен"


def _match_item(
    candidate: CandidateProfile,
    score: dict,
    percentage: float | None,
    need: EmployerNeed,
    requested_skill_tests: list[RequestedSkillTestResult],
    additional_specializations: list[dict[str, Any]],
    declared_grade: str | None,
) -> CandidateMatchItem:
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
    summary = [f"Подтверждён {need.required_grade.capitalize()} по направлению {need.specialization}."]
    if matched:
        summary.append(f"Совпали навыки: {', '.join(matched)}.")
    if missing:
        summary.append(f"Не указаны навыки: {', '.join(missing)}.")
    summary.append(
        f"Отдельные результаты тестов есть по {score['tested_skill_count']} из "
        f"{score['requested_skill_count']} запрошенных навыков. "
        "Балл учитывает подтверждённые результаты и навыки из анкеты; отсутствие результата не означает отсутствие навыка."
    )
    if score["salary_match"]:
        summary.append("Зарплатные ожидания соответствуют бюджету.")
    elif candidate.salary_expectation is not None and candidate.salary_tax_type != need.salary_tax_type:
        summary.append("Требуется согласование налогового типа зарплаты.")
    else:
        summary.append(salary_note + ".")
    if score["fsp_bonus"]:
        summary.append("Подтверждённое достижение ФСП добавило 5 баллов; грейд не изменился.")
    elif any(item.is_demo for item in candidate.fsp_achievements):
        summary.append("Достижения ФСП демонстрационные и не влияют на балл подбора.")
    top_achievement = next((item for item in candidate.fsp_achievements if item.verified and not item.is_demo), None)

    from app.services.trust_score_service import calculate_trust_score
    from app.services.resume_versions import labeled_work_entries
    trust_score_val, trust_flags_val = calculate_trust_score(candidate)
    return CandidateMatchItem(
        candidate_id=candidate.id,
        is_demo=not candidate.user.is_active and candidate.user.email.endswith("@example.test"),
        profile_completeness=calculate_profile_completeness(candidate, email_verified=candidate.user.is_verified),
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        specialization=need.specialization,
        verified_grade=need.required_grade,
        declared_grade=declared_grade,
        city=candidate.city,
        work_format=candidate.work_format,
        fsp_id=candidate.fsp_id,
        fsp_verified=candidate.fsp_verified,
        fsp_sport_category=top_achievement.sport_category if top_achievement else None,
        fsp_rating=top_achievement.score_or_rating if top_achievement else None,
        achievements_count=len(candidate.fsp_achievements),
        skills=candidate.skills or [],
        bio=candidate.bio,
        hobbies=candidate.hobbies,
        education_level=candidate.education_level,
        university_course=candidate.university_course,
        birth_year=candidate.birth_year,
        photo_url=f"/candidate/{candidate.id}/photo" if candidate.photo_filename else None,
        github_url=candidate.github_url,
        resume_text=None,
        resume_employers=list(dict.fromkeys(
            company for company, _role in labeled_work_entries(candidate.resume_text or "").values()
        )),
        resume_url=None,
        salary_expectation=candidate.salary_expectation,
        salary_tax_type=candidate.salary_tax_type,
        test_percentage=percentage,
        activity_status=_candidate_activity_status(candidate.last_active_at),
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
        requested_skill_tests=requested_skill_tests,
        additional_specializations=additional_specializations,
        trust_score=trust_score_val,
        trust_flags=trust_flags_val,
        profile_updated_at=candidate.updated_at,
    )


async def _additional_specializations_by_candidate(
    db: AsyncSession, candidates: list[CandidateProfile],
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    if not candidates:
        return {}
    candidate_ids = [candidate.id for candidate in candidates]
    tracks = (await db.scalars(select(CandidateSpecializationTrack).where(
        CandidateSpecializationTrack.candidate_profile_id.in_(candidate_ids),
    ).order_by(CandidateSpecializationTrack.created_at))).all()
    active = (await db.execute(select(
        GradeAssessment.candidate_profile_id,
        GradeAssessment.specialization,
    ).where(
        GradeAssessment.candidate_profile_id.in_(candidate_ids),
        GradeAssessment.status.in_(("in_progress", "pending_review")),
    ))).all()
    active_keys = {(row.candidate_profile_id, row.specialization) for row in active}
    result: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for track in tracks:
        result.setdefault(track.candidate_profile_id, []).append({
            "specialization": track.specialization,
            "declared_grade": track.declared_grade,
            "status": "verified" if track.verified_grade else (
                "in_progress" if (track.candidate_profile_id, track.specialization) in active_keys else "requested"
            ),
            "verified_grade": track.verified_grade,
        })
    for candidate in candidates:
        primary = candidate.verified_specialization or candidate.specialization
        if not primary:
            continue
        item = {
            "specialization": primary,
            "declared_grade": candidate.declared_grade,
            "status": "verified" if candidate.verified_grade else "requested",
            "verified_grade": candidate.verified_grade,
        }
        candidate_items = result.setdefault(candidate.id, [])
        candidate_items[:] = [track for track in candidate_items
                              if track["specialization"].casefold() != primary.casefold()]
        candidate_items.insert(0, item)
    return result


class MatchingService:
    @staticmethod
    async def match_candidates_for_need(
        db: AsyncSession, need_id: uuid.UUID, current_user: User | None = None
    ) -> MatchingCandidatesResponse:
        need = await db.scalar(
            select(EmployerNeed)
            .options(joinedload(EmployerNeed.employer))
            .where(EmployerNeed.id == need_id)
        )
        if need is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Потребность не найдена")
        if current_user and need.employer and need.employer.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чужая потребность недоступна")

        matching_tracks = select(CandidateSpecializationTrack.candidate_profile_id).where(
            func.lower(CandidateSpecializationTrack.specialization) == need.specialization.casefold(),
            func.lower(CandidateSpecializationTrack.verified_grade) == need.required_grade.casefold(),
        )
        candidates = (await db.scalars(
            select(CandidateProfile)
            .options(
                joinedload(CandidateProfile.fsp_achievements),
                joinedload(CandidateProfile.user),
                selectinload(CandidateProfile.test_sessions),
                defer(CandidateProfile.telegram),
                defer(CandidateProfile.middle_name),
            )
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
                or_(
                    and_(
                        func.lower(CandidateProfile.verified_grade) == need.required_grade.casefold(),
                        or_(
                            func.lower(CandidateProfile.verified_specialization) == need.specialization.casefold(),
                            and_(
                                CandidateProfile.verified_specialization.is_(None),
                                func.lower(CandidateProfile.specialization) == need.specialization.casefold(),
                            ),
                        ),
                    ),
                    CandidateProfile.id.in_(matching_tracks),
                ),
            )
        )).unique().all()
        if not candidates:
            return MatchingCandidatesResponse(need_id=need.id, need_title=need.title, total=0, candidates=[])

        cand_ids = [item.id for item in candidates]
        by_id = {item.id: item for item in candidates}
        matching_track_rows = (await db.scalars(select(CandidateSpecializationTrack).where(
            CandidateSpecializationTrack.candidate_profile_id.in_(cand_ids),
            func.lower(CandidateSpecializationTrack.specialization) == need.specialization.casefold(),
            func.lower(CandidateSpecializationTrack.verified_grade) == need.required_grade.casefold(),
        ))).all()
        declared_by_candidate = {row.candidate_profile_id: row.declared_grade for row in matching_track_rows}
        assessments_rows = (await db.execute(
            select(
                GradeAssessment.id,
                GradeAssessment.candidate_profile_id,
                GradeAssessment.target_grade,
                GradeAssessment.specialization,
                GradeAssessment.percentage,
            )
            .where(
                GradeAssessment.candidate_profile_id.in_(cand_ids),
                GradeAssessment.status == "completed",
                GradeAssessment.passed.is_(True),
            )
            .order_by(GradeAssessment.completed_at.desc())
        )).all()
        confirmed_results: dict[uuid.UUID, float] = {}
        confirmed_assessments: dict[uuid.UUID, uuid.UUID] = {}
        for row in assessments_rows:
            candidate = by_id.get(row.candidate_profile_id)
            if (
                candidate is not None
                and candidate.id not in confirmed_results
                and row.target_grade.casefold() == need.required_grade.casefold()
                and row.specialization.casefold() == need.specialization.casefold()
            ):
                confirmed_results[candidate.id] = row.percentage
                confirmed_assessments[candidate.id] = row.id

        unconfirmed_ids = [c.id for c in candidates if c.id not in confirmed_results]
        if unconfirmed_ids:
            legacy_sessions = (await db.execute(
                select(
                    TestSession.candidate_profile_id,
                    TestSession.target_grade,
                    TestSession.specialization,
                    TestSession.percentage,
                )
                .where(
                    TestSession.candidate_profile_id.in_(unconfirmed_ids),
                    TestSession.assessment_id.is_(None),
                    TestSession.status == "completed",
                    TestSession.passed.is_(True),
                )
                .order_by(TestSession.completed_at.desc(), TestSession.created_at.desc())
            )).all()
            for session in legacy_sessions:
                candidate = by_id.get(session.candidate_profile_id)
                if (
                    candidate is not None
                    and candidate.id not in confirmed_results
                    and session.target_grade.casefold() == need.required_grade.casefold()
                    and session.specialization.casefold() == need.specialization.casefold()
                ):
                    confirmed_results[candidate.id] = session.percentage

        aliases = (
            BACKEND_MATCHING_SKILL_CODES if need.specialization.casefold() == "backend"
            else DS_MATCHING_SKILL_CODES if need.specialization.casefold() == "data science / ml"
            else {}
        )
        requested_codes = {
            aliases.get(str(item.get("name") or "").strip().casefold())
            for item in (need.required_skills or []) if isinstance(item, dict)
        } - {None}
        sessions = (await db.execute(
            select(
                TestSession.id,
                TestSession.candidate_profile_id,
                TestSession.assessment_id,
                TestSession.skill_code,
                TestSession.target_grade,
                TestSession.specialization,
                TestSession.percentage,
                TestSession.passed,
                TestSession.completed_at,
            )
            .where(
                TestSession.candidate_profile_id.in_(cand_ids),
                TestSession.status == "completed",
                TestSession.skill_code.in_(requested_codes),
                or_(
                    TestSession.assessment_id.in_(list(confirmed_assessments.values())),
                    TestSession.assessment_id.is_(None),
                ),
            )
            .order_by(TestSession.completed_at.desc(), TestSession.created_at.desc())
        )).all() if requested_codes else []
        base_by_candidate: dict[uuid.UUID, dict[str, Any]] = {}
        additional_by_candidate: dict[uuid.UUID, dict[str, Any]] = {}
        for session in sessions:
            candidate = by_id[session.candidate_profile_id]
            if session.specialization.casefold() != need.specialization.casefold():
                continue
            if session.assessment_id is not None and session.assessment_id == confirmed_assessments.get(candidate.id) and session.target_grade.casefold() == need.required_grade.casefold():
                base_by_candidate.setdefault(candidate.id, {}).setdefault(session.skill_code, session)
            elif session.assessment_id is None and session.target_grade == "all" and session.passed:
                additional_by_candidate.setdefault(candidate.id, {}).setdefault(session.skill_code, session)
        need_reqs = _parse_need_requirements(need)
        skill_tests_by_candidate = {
            candidate.id: _requested_skill_tests_dict(
                need_reqs,
                aliases,
                base_by_candidate.get(candidate.id, {}),
                additional_by_candidate.get(candidate.id, {}),
            )
            for candidate in candidates
        }
        additional_specializations = await _additional_specializations_by_candidate(db, candidates)
        need_dict = {
            "specialization": need.specialization,
            "required_grade": need.required_grade,
            "required_skills": need.required_skills or [],
            "work_format": need.work_format,
            "city": need.city,
            "salary_max": need.salary_max,
            "salary_tax_type": need.salary_tax_type,
        }
        ranked = rank_candidates(
            need_dict,
            [_candidate_data(item, confirmed_results.get(item.id), skill_tests_by_candidate[item.id], need.specialization, need.required_grade) for item in candidates],
        )
        items = [
            _match_item(
                by_id[result["candidate_id"]], result, confirmed_results.get(result["candidate_id"]), need,
                [RequestedSkillTestResult(**r) for r in skill_tests_by_candidate[result["candidate_id"]]],
                additional_specializations.get(result["candidate_id"], []),
                declared_by_candidate.get(result["candidate_id"], by_id[result["candidate_id"]].declared_grade),
            )
            for result in ranked
        ]
        return MatchingCandidatesResponse(need_id=need.id, need_title=need.title, total=len(items), candidates=items)

    @staticmethod
    async def search_candidates(
        db: AsyncSession,
        specialization: str | None = None,
        grade: str | None = None,
        skill: str | None = None,
        stack: str | None = None,
        work_format: str | None = None,
        city: str | None = None,
        education_level: str | None = None,
        university_course_group: str | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        fsp_only: bool = False,
        verified_only: bool = False,
    ) -> list[CandidateMatchItem]:
        track_query = select(CandidateSpecializationTrack.candidate_profile_id).where(
            CandidateSpecializationTrack.verified_grade.is_not(None),
        )
        primary_filters = [CandidateProfile.verified_grade.is_not(None)]
        if specialization:
            track_query = track_query.where(func.lower(CandidateSpecializationTrack.specialization) == specialization.casefold())
            primary_filters.append(func.lower(func.coalesce(CandidateProfile.verified_specialization, CandidateProfile.specialization)) == specialization.casefold())
        if grade:
            track_query = track_query.where(func.lower(CandidateSpecializationTrack.verified_grade) == grade.casefold())
            primary_filters.append(func.lower(CandidateProfile.verified_grade) == grade.casefold())
        stmt = (
            select(CandidateProfile)
            .options(
                joinedload(CandidateProfile.fsp_achievements),
                joinedload(CandidateProfile.user),
                selectinload(CandidateProfile.test_sessions),
                defer(CandidateProfile.telegram),
                defer(CandidateProfile.middle_name),
            )
            .where(
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
                or_(and_(*primary_filters), CandidateProfile.id.in_(track_query)),
            )
        )
        if work_format:
            stmt = stmt.where(CandidateProfile.work_format == work_format)
        if city:
            stmt = stmt.where(CandidateProfile.city.ilike(f"%{city}%"))
        if fsp_only:
            stmt = stmt.where(CandidateProfile.fsp_verified.is_(True))
        if education_level:
            stmt = stmt.where(CandidateProfile.education_level == education_level)
        if university_course_group == "junior":
            stmt = stmt.where(CandidateProfile.university_course.in_([1, 2]))
        elif university_course_group == "senior":
            stmt = stmt.where(CandidateProfile.university_course >= 3)
        current_year = datetime.now().year
        if age_min is not None:
            stmt = stmt.where(CandidateProfile.birth_year <= current_year - age_min)
        if age_max is not None:
            stmt = stmt.where(CandidateProfile.birth_year >= current_year - age_max)

        candidates = (await db.scalars(stmt)).unique().all()

        filter_text = (stack or skill or "").strip()
        if filter_text:
            raw = filter_text.replace(";", ",")
            if "," in raw:
                tokens = [t.strip().casefold() for t in raw.split(",") if t.strip()]
            else:
                tokens = [t.strip().casefold() for t in raw.split() if t.strip()]
            if tokens:
                candidates = [
                    candidate for candidate in candidates
                    if all(
                        any(token in candidate_skill.casefold() for candidate_skill in (candidate.skills or []))
                        for token in tokens
                    )
                ]

        from app.services.trust_score_service import calculate_trust_score
        from app.services.resume_versions import labeled_work_entries
        additional_specializations = await _additional_specializations_by_candidate(db, candidates)
        items = []
        for candidate in candidates:
            primary_spec = candidate.verified_specialization or candidate.specialization
            primary_matches = bool(candidate.verified_grade and (
                not specialization or (primary_spec or "").casefold() == specialization.casefold()
            ) and (not grade or candidate.verified_grade.casefold() == grade.casefold()))
            track = next((item for item in additional_specializations.get(candidate.id, [])
                if item["verified_grade"] and (not specialization or item["specialization"].casefold() == specialization.casefold())
                and (not grade or item["verified_grade"].casefold() == grade.casefold())), None)
            selected_spec = primary_spec if primary_matches else track["specialization"]
            selected_grade = candidate.verified_grade if primary_matches else track["verified_grade"]
            selected_declared = candidate.declared_grade if primary_matches else track["declared_grade"]
            trust_score_val, trust_flags_val = calculate_trust_score(candidate)
            items.append(
                CandidateMatchItem(
                    candidate_id=candidate.id,
                    is_demo=not candidate.user.is_active and candidate.user.email.endswith("@example.test"),
                    profile_completeness=calculate_profile_completeness(candidate, email_verified=candidate.user.is_verified),
                    first_name=candidate.first_name,
                    last_name=candidate.last_name,
                    specialization=selected_spec,
                    verified_grade=selected_grade,
                    declared_grade=selected_declared,
                    city=candidate.city,
                    work_format=candidate.work_format,
                    fsp_id=candidate.fsp_id,
                    fsp_verified=candidate.fsp_verified,
                    fsp_sport_category=candidate.fsp_achievements[0].sport_category if candidate.fsp_achievements else None,
                    fsp_rating=candidate.fsp_achievements[0].score_or_rating if candidate.fsp_achievements else None,
                    achievements_count=len(candidate.fsp_achievements),
                    skills=candidate.skills or [],
                    bio=candidate.bio,
                    hobbies=candidate.hobbies,
                    education_level=candidate.education_level,
                    university_course=candidate.university_course,
                    birth_year=candidate.birth_year,
                    photo_url=f"/candidate/{candidate.id}/photo" if candidate.photo_filename else None,
                    github_url=candidate.github_url,
                    resume_text=None,
                    resume_employers=list(dict.fromkeys(
                        company for company, _role in labeled_work_entries(candidate.resume_text or "").values()
                    )),
                    resume_url=None,
                    salary_expectation=candidate.salary_expectation,
                    salary_tax_type=candidate.salary_tax_type,
                    test_percentage=None,
                    activity_status=_candidate_activity_status(candidate.last_active_at),
                    match_score=0,
                    match_explanation=MatchExplanation(
                        grade_match=True,
                        matched_skills=[],
                        missing_skills=[],
                        fsp_bonus=False,
                        summary="Кандидат с подтверждённой категорией. Балл для конкретной потребности здесь не рассчитывается.",
                    ),
                    additional_specializations=additional_specializations.get(candidate.id, []),
                    trust_score=trust_score_val,
                    trust_flags=trust_flags_val,
                    profile_updated_at=candidate.updated_at,
                )
            )
        return items


matching_service = MatchingService()
