"""Достижения ФСП дают ограниченный бонус только при настоящей проверке."""

from app.core.ranking import score_candidate
from app.models.candidate import CandidateProfile
from app.models.fsp import FSPAchievement
from app.services.matching_service import _candidate_data


NEED = {"specialization": "Backend", "required_grade": "middle"}
BASE = {"id": "candidate", "specialization": "Backend", "verified_grade": "middle"}


def score(**fields):
    result = score_candidate(NEED, {**BASE, **fields})
    assert result is not None
    return result


def test_only_verified_non_demo_achievement_adds_five_points():
    no_fsp = score()
    demo = score(fsp_verified=True, fsp_achievements=[{"verified": True, "is_demo": True}])
    unverified = score(fsp_verified=True, fsp_achievements=[{"verified": False, "is_demo": False}])
    unrelated_id = score(fsp_verified=False, fsp_achievements=[{"verified": True, "is_demo": False}])
    real = score(fsp_verified=True, fsp_achievements=[{"verified": True, "is_demo": False}])
    multiple = score(fsp_verified=True, fsp_achievements=[
        {"verified": True, "is_demo": False}, {"verified": True, "is_demo": False},
    ])

    for item in (demo, unverified, unrelated_id):
        assert item["points"] == no_fsp["points"]
        assert item["fsp_bonus"] is False
    assert real["points"] - no_fsp["points"] == 5
    assert real["parts"]["fsp"] == multiple["parts"]["fsp"] == 5
    assert real["group"] == no_fsp["group"] == "confirmed"


def test_matching_projection_preserves_demo_flag():
    profile = CandidateProfile(
        specialization="Backend", verified_grade="middle", fsp_verified=True, skills=[],
    )
    profile.fsp_achievements = [FSPAchievement(
        fsp_id="FSP-DEMO", tournament_name="Тестовое достижение", year=2025,
        rank_or_place="1 место", verified=True, is_demo=True,
    )]
    result = score_candidate(NEED, _candidate_data(profile, None, []))
    assert result is not None
    assert result["fsp_bonus"] is False
    assert result["parts"]["fsp"] == 0
