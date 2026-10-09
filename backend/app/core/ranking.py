"""Расчёт порядка кандидатов по потребности без БД и моделей ORM (B-14)."""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _skill_requirements(need: dict[str, Any]) -> list[tuple[str, float]]:
    requirements: dict[str, float] = {}
    for item in need.get("required_skills") or []:
        if not isinstance(item, dict):
            continue
        name = _norm(item.get("name"))
        if not name:
            continue
        try:
            weight = float(item.get("weight", 1))
        except (TypeError, ValueError):
            continue
        if weight > 0:
            requirements[name] = max(weight, requirements.get(name, 0))
    return list(requirements.items())


def score_candidate(need: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    """Вернуть баллы для нужной категории либо None, если категория другая.

    Баллы нужны только для порядка внутри одной группы; это не вероятность найма
    и не оценка квалификации в процентах.
    """
    if _norm(candidate.get("specialization")) != _norm(need.get("specialization")):
        return None

    target_grade = _norm(need.get("required_grade"))
    if not target_grade:
        return None
    # Заявленный грейд допуска в выдачу по потребности не даёт.
    if _norm(candidate.get("verified_grade")) != target_grade:
        return None
    group = "confirmed"

    requirements = _skill_requirements(need)
    candidate_skills = {_norm(skill) for skill in candidate.get("skills") or []}
    for skill in tuple(candidate_skills):
        for part in skill.replace("/", " & ").split(" & "):
            if part.strip():
                candidate_skills.add(part.strip())
    matched = [name for name, _ in requirements if name in candidate_skills]
    missing = [name for name, _ in requirements if name not in candidate_skills]
    total_weight = sum(weight for _, weight in requirements)
    matched_weight = sum(weight for name, weight in requirements if name in candidate_skills)
    # Анкета показывает заявленные навыки, отдельные тесты — измеренные.
    profile_skill_points = 18 * matched_weight / total_weight if total_weight else 0.0
    tested_weight = 0.0
    tested_points = 0.0
    tested_results = {
        _norm(item.get("name")): item.get("percentage")
        for item in candidate.get("requested_skill_tests") or []
        if isinstance(item, dict)
    }
    for name, weight in requirements:
        result = tested_results.get(name)
        if result is None:
            continue
        try:
            percentage = max(0.0, min(float(result), 100.0))
        except (TypeError, ValueError):
            continue
        tested_weight += weight
        tested_points += weight * percentage / 100
    skill_test_points = 37 * tested_points / total_weight if total_weight else 0.0
    skills_points = profile_skill_points + skill_test_points

    test_result = candidate.get("test_percentage")
    try:
        test_points = 20 * max(0.0, min(float(test_result), 100.0)) / 100 if test_result is not None else 0.0
    except (TypeError, ValueError):
        test_points = 0.0

    need_format = _norm(need.get("work_format"))
    candidate_format = _norm(candidate.get("work_format"))
    format_match = bool(need_format and need_format == candidate_format)
    city_match = bool(_norm(need.get("city")) and _norm(need.get("city")) == _norm(candidate.get("city")))
    if need_format == "remote":
        work_points = 10.0 if format_match else 0.0
    else:
        work_points = (5.0 if format_match else 0.0) + (5.0 if format_match and city_match else 0.0)

    need_tax = _norm(need.get("salary_tax_type") or need.get("salary_basis"))
    cand_tax = _norm(candidate.get("salary_tax_type") or candidate.get("salary_basis"))
    cand_salary = (
        candidate.get("salary_expectation_min")
        if candidate.get("salary_expectation_min") is not None
        else candidate.get("salary_expectation")
    )
    salary_comparable = bool(
        need_tax
        and need_tax == cand_tax
        and need.get("salary_max") is not None
        and cand_salary is not None
    )
    try:
        salary_match = bool(
            salary_comparable
            and float(cand_salary) <= float(need["salary_max"])
        )
    except (TypeError, ValueError):
        salary_comparable = False
        salary_match = False
    salary_points = 10.0 if salary_match else 0.0

    fsp_bonus = bool(candidate.get("fsp_verified") and candidate.get("fsp_achievements"))
    fsp_points = 5.0 if fsp_bonus else 0.0
    points = round(skills_points + test_points + work_points + salary_points + fsp_points, 2)
    return {
        "candidate_id": candidate.get("id"),
        "candidate_code": candidate.get("synthetic_code"),
        "group": group,
        "points": points,
        "parts": {
            "skills": round(skills_points, 2),
            "profile_skills": round(profile_skill_points, 2),
            "tested_skills": round(skill_test_points, 2),
            "test": round(test_points, 2),
            "work": round(work_points, 2),
            "salary": salary_points,
            "fsp": fsp_points,
        },
        "matched_skills": matched,
        "missing_skills": missing,
        "tested_skill_count": sum(1 for name, _ in requirements if tested_results.get(name) is not None),
        "requested_skill_count": len(requirements),
        "format_match": format_match,
        "city_match": city_match if need_format != "remote" else None,
        "salary_match": salary_match if salary_comparable else None,
        "fsp_bonus": fsp_bonus,
    }


def rank_candidates(need: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Порядок кандидатов с подтверждённым грейдом нужной специализации."""
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        result = score_candidate(need, candidate)
        if result is not None:
            ranked.append(result)
    ranked.sort(key=lambda item: (-item["points"], str(item["candidate_id"])))
    return ranked


def baseline_rank(need: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    """Простое сравнение: та же категория, затем число совпавших навыков, затем ID."""
    items: list[tuple[int, str, str]] = []
    for candidate in candidates:
        result = score_candidate(need, candidate)
        if result is None:
            continue
        items.append((len(result["matched_skills"]), str(candidate.get("id")), str(candidate.get("synthetic_code"))))
    return [code for _, _, code in sorted(items, key=lambda item: (-item[0], item[1]))]
