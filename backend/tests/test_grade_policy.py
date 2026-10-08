import pytest

from app.core.grade_policy import SkillResult, assess_grade


SKILLS = ("python", "sql", "api", "reliability")


def results(scores):
    return [SkillResult(code, score, 3) for code, score in zip(SKILLS, scores)]


def test_grade_waits_for_every_mandatory_skill():
    decision = assess_grade(SKILLS, results((3, 3, 3)))
    assert not decision.complete and not decision.passed
    assert decision.missing_skills == ("reliability",)


def test_exact_75_percent_and_skill_minimum_pass():
    decision = assess_grade(SKILLS, results((3, 2, 2, 2)))
    assert decision.complete and decision.passed
    assert decision.overall_ratio == 0.75


def test_overall_pass_does_not_hide_weak_skill():
    decision = assess_grade(SKILLS, results((3, 3, 3, 1)))
    assert decision.overall_ratio > 0.75
    assert not decision.passed
    assert decision.below_minimum == ("reliability",)


def test_lower_overall_fails_even_if_each_skill_passes():
    decision = assess_grade(SKILLS, results((2, 2, 2, 2)))
    assert not decision.passed
    assert decision.below_minimum == ()


def test_unequal_skill_maximum_is_rejected():
    with pytest.raises(ValueError, match="одинаковый максимум"):
        assess_grade(("python", "sql"), [
            SkillResult("python", 9, 10), SkillResult("sql", 1, 2),
        ])


def test_frozen_policy_can_differ_from_current_default():
    decision = assess_grade(("python", "sql"), [
        SkillResult("python", 7, 10), SkillResult("sql", 7, 10),
    ], overall_minimum=0.70, skill_minimum=0.60)
    assert decision.passed


def test_display_score_is_relative_to_grade():
    assert SkillResult("python", 6, 10).level_out_of_ten == 6.0


def test_invalid_input_does_not_produce_grade():
    with pytest.raises(ValueError):
        assess_grade(SKILLS, results((3, 3, 3, 3)) + [SkillResult("spark", 3, 3)])
    with pytest.raises(ValueError):
        SkillResult("python", 4, 3)
