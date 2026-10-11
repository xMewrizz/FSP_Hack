"""Заполненность считается одинаково для кабинета и выдачи работодателя."""

from types import SimpleNamespace

from app.schemas.matching import CandidateMatchItem, MatchExplanation
from app.services.profile_completeness import calculate_profile_completeness


def profile(**changes):
    fields = dict(
        first_name="Анна", last_name="Иванова", phone="+79990000000",
        specialization="Backend", programming_language="Python",
        declared_grade="middle", city="Москва", work_format="remote",
        salary_expectation=150000, resume_text="Разрабатывала сервисы",
        resume_url="attached.pdf",
        skills=["Python"], verified_grade="middle",
    )
    fields.update(changes)
    return SimpleNamespace(**fields)


def test_full_profile_and_missing_phone():
    full = calculate_profile_completeness(profile(), email_verified=True)
    assert (full.score, full.status, full.missing) == (100, "complete", [])

    no_phone = calculate_profile_completeness(profile(phone="  "), email_verified=True)
    assert (no_phone.score, no_phone.status) == (70, "partial")
    assert no_phone.missing == ["номер телефона"]


def test_empty_and_unverified_profile():
    empty = profile(
        first_name="", last_name="", phone=None, specialization=None,
        programming_language=None, declared_grade=None, city=None,
        work_format=None, salary_expectation=None, resume_text=None, resume_url=None,
        skills=[], verified_grade=None,
    )
    result = calculate_profile_completeness(empty, email_verified=False)
    assert result.score == 0
    assert result.status == "insufficient"
    assert len(result.missing) == 8

    result = calculate_profile_completeness(profile(), email_verified=False)
    assert result.score == 80
    assert result.status == "partial"


def test_attached_resume_adds_ten_points_but_text_alone_does_not():
    without_description = calculate_profile_completeness(
        profile(resume_text=None, resume_url=None), email_verified=True
    )
    assert without_description.score == 90
    assert "прикреплённое резюме" in without_description.missing
    assert calculate_profile_completeness(profile(resume_text=None), email_verified=True).score == 100
    assert calculate_profile_completeness(profile(resume_url=None), email_verified=True).score == 90


def test_employer_contract_omits_private_completion_hints():
    result = calculate_profile_completeness(profile(phone=None), email_verified=True)
    item = CandidateMatchItem(
        candidate_id="00000000-0000-0000-0000-000000000001",
        profile_completeness=result,
        first_name="Анна", last_name="Иванова", specialization="Backend",
        verified_grade="middle", declared_grade="middle", city="Москва",
        work_format="remote", fsp_id=None, fsp_verified=False,
        fsp_sport_category=None, fsp_rating=None, achievements_count=0,
        skills=["Python"], test_percentage=None, match_score=0,
        match_explanation=MatchExplanation(
            grade_match=True, matched_skills=[], missing_skills=[],
            fsp_bonus=False, summary="",
        ),
    )
    assert item.model_dump()["profile_completeness"] == {"score": 70, "status": "partial"}
