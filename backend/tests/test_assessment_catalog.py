from app.core.assessment_catalog import (
    BACKEND_QUESTION_CODES,
    BACKEND_REQUIRED_SKILLS,
    backend_curriculum_gaps,
    validate_backend_question_mapping,
)


def test_mandatory_skill_list_is_the_same_at_every_grade():
    codes = {code for code, _ in BACKEND_REQUIRED_SKILLS}
    assert all(set(groups) == codes for groups in BACKEND_QUESTION_CODES.values())


def test_existing_questions_belong_to_the_declared_grade():
    validate_backend_question_mapping()


def test_curriculum_reports_exact_remaining_work():
    assert backend_curriculum_gaps() == []
    assert all(len(codes) == 10 for groups in BACKEND_QUESTION_CODES.values() for codes in groups.values())
