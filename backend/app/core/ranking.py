"""Расчёт порядка кандидатов без БД и моделей ORM (заготовка B-14)."""

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
    verified = _norm(candidate.get("verified_grade"))
    declared = _norm(candidate.get("declared_grade"))
    if verified == target_grade:
        group = "confirmed"
    elif not verified and declared == target_grade:
        group = "unconfirmed"
    else:
        return None

    requirements = _skill_requirements(need)
    candidate_skills = {_norm(skill) for skill in candidate.get("skills") or []}
    matched = [name for name, _ in requirements if name in candidate_skills]
    missing = [name for name, _ in requirements if name not in candidate_skills]
    total_weight = sum(weight for _, weight in requirements)
    matched_weight = sum(weight for name, weight in requirements if name in candidate_skills)
    skills_points = 55 * matched_weight / total_weight if total_weight else 0.0

    test_result = candidate.get("test_percentage") if group == "confirmed" else None
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
            "test": round(test_points, 2),
            "work": round(work_points, 2),
            "salary": salary_points,
            "fsp": fsp_points,
        },
        "matched_skills": matched,
        "missing_skills": missing,
        "format_match": format_match,
        "city_match": city_match if need_format != "remote" else None,
        "salary_match": salary_match if salary_comparable else None,
        "fsp_bonus": fsp_bonus,
    }


def rank_candidates(need: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Сортировать две группы отдельно; не смешивать заявленный грейд с подтверждённым."""
    groups: dict[str, list[dict[str, Any]]] = {"confirmed": [], "unconfirmed": []}
    for candidate in candidates:
        result = score_candidate(need, candidate)
        if result is not None:
            groups[result["group"]].append(result)
    for items in groups.values():
        items.sort(key=lambda item: (-item["points"], str(item["candidate_id"])))
    return groups


def baseline_rank(need: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Простое сравнение: категория, затем число совпавших навыков, затем ID."""
    groups: dict[str, list[tuple[int, str, str]]] = {"confirmed": [], "unconfirmed": []}
    for candidate in candidates:
        result = score_candidate(need, candidate)
        if result is None:
            continue
        groups[result["group"]].append((len(result["matched_skills"]), str(candidate.get("id")), str(candidate.get("synthetic_code"))))
    return {
        group: [code for _, _, code in sorted(items, key=lambda item: (-item[0], item[1]))]
        for group, items in groups.items()
    }
