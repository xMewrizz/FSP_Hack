"""Единый расчёт заполненности анкеты кандидата.

Балл не является проверкой личности, достоверности резюме или профессионального уровня.
"""

from app.models.candidate import CandidateProfile
from app.schemas.profile_completeness import ProfileCompleteness


def calculate_profile_completeness(
    profile: CandidateProfile, *, email_verified: bool
) -> ProfileCompleteness:
    def filled(value: str | None) -> bool:
        return bool(value and value.strip())

    checks = [
        ("имя и фамилию", 5, filled(profile.first_name) and filled(profile.last_name)),
        ("подтверждение email", 20, email_verified),
        ("номер телефона", 30, filled(profile.phone)),
        (
            "специализацию, язык и заявленный грейд", 5,
            filled(profile.specialization) and filled(profile.programming_language)
            and filled(profile.declared_grade),
        ),
        (
            "город, формат и ожидания по зарплате", 5,
            filled(profile.city) and filled(profile.work_format)
            and profile.salary_expectation is not None and profile.salary_expectation > 0,
        ),
        ("навыки", 5, bool(profile.skills)),
        ("прикреплённое резюме", 10, filled(profile.resume_url)),
        ("подтверждение грейда тестом", 20, filled(profile.verified_grade)),
    ]
    score = sum(points for _, points, done in checks if done)
    status = "insufficient" if score < 40 else "partial" if score < 100 else "complete"
    return ProfileCompleteness(
        score=score,
        status=status,
        missing=[label for label, _, done in checks if not done],
    )
