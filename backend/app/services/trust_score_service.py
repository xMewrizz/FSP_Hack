from datetime import datetime, timezone
from app.models.candidate import CandidateProfile
from app.services.resume_sanity import resume_warnings

def calculate_trust_score(candidate: CandidateProfile) -> tuple[float, list[dict]]:
    """Returns (score, flags) where score is 0.0-1.0 and flags explain the score."""
    score = 0.0
    flags = []

    # 1. Skill verification signal (0.40)
    skill_score = 0.0
    if candidate.verified_grade:
        skill_score += 0.25
    try:
        passed_sessions = [s for s in getattr(candidate, "test_sessions", []) if getattr(s, "passed", False)]
    except Exception:
        passed_sessions = []    
    if len(passed_sessions) > 0:
        skill_score += 0.15
        flags.append({
            "label": "Навыки",
            "status": "verified",
            "detail": f"Подтверждён грейд {candidate.verified_grade}, успешно пройдено тестов: {len(passed_sessions)}" if candidate.verified_grade else f"Успешно пройдено тестов: {len(passed_sessions)}"
        })
    elif candidate.verified_grade:
        flags.append({
            "label": "Навыки",
            "status": "verified",
            "detail": f"Подтверждён грейд {candidate.verified_grade}"
        })
    else:
        flags.append({
            "label": "Навыки",
            "status": "review",
            "detail": "Грейд и навыки пока не подтверждены тестами"
        })
    score += skill_score

    # A format check cannot establish that employment history is genuine.
    resume_score = 0.0
    if candidate.resume_text:
        warnings = resume_warnings(candidate.resume_text)
        if not warnings:
            resume_score = 0.10
            flags.append({
                "label": "Резюме",
                "status": "review",
                "detail": "Явных ошибок в датах и контактах не найдено; опыт и работодатели не подтверждены"
            })
        else:
            flags.append({
                "label": "Резюме",
                "status": "warning",
                "detail": f"Найдено возможных ошибок: {len(warnings)}; проверьте их в исходном резюме"
            })
    else:
        flags.append({
            "label": "Резюме",
            "status": "review",
            "detail": "Резюме не загружено или загружено без текста"
        })
    score += resume_score

    # 3. FSP verification signal (0.15)
    fsp_score = 0.0
    has_verified_achievement = any(
        a.verified and not a.is_demo for a in candidate.fsp_achievements
    ) if hasattr(candidate, 'fsp_achievements') else False
    if candidate.fsp_verified and has_verified_achievement:
        fsp_score = 0.15
        flags.append({
            "label": "ФСП",
            "status": "verified",
            "detail": "Есть привязка к ФСП и подтверждённые достижения"
        })
    elif candidate.fsp_verified:
        flags.append({
            "label": "ФСП",
            "status": "review",
            "detail": "Найдена демонстрационная запись ФСП; личность владельца записи не проверена"
        })
    else:
        flags.append({
            "label": "ФСП",
            "status": "review",
            "detail": "Профиль ФСП не привязан"
        })
    score += fsp_score

    # 4. Profile completeness & activity signal (0.20)
    profile_score = 0.0
    completeness = 0
    if candidate.bio: completeness += 1
    if candidate.skills: completeness += 1
    if candidate.city: completeness += 1
    if candidate.work_format: completeness += 1
    
    profile_score += (completeness / 4) * 0.10

    is_active = False
    if candidate.last_active_at:
        days_ago = (datetime.now(timezone.utc) - candidate.last_active_at).days
        if days_ago < 30:
            profile_score += 0.10
            is_active = True
        elif days_ago < 90:
            profile_score += 0.05
    
    if completeness >= 3 and is_active:
        flags.append({
            "label": "Профиль",
            "status": "review",
            "detail": "Профиль подробно заполнен и недавно использовался; сведения указаны кандидатом"
        })
    else:
        flags.append({
            "label": "Профиль",
            "status": "review",
            "detail": "Профиль заполнен частично или давно не обновлялся"
        })
    score += profile_score

    return round(score, 2), flags
