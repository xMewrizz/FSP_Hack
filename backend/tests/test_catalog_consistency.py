"""B-01: согласованность справочника и запрет подмены вопросов.

Pure-тест: не импортирует app.models и БД (их нет в репозитории),
поэтому работает даже пока backend не стартует.
"""

import pytest

from app.core.catalog import (
    ALL_GRADES,
    ALL_SPECIALIZATIONS,
    MIN_QUESTIONS_PER_PAIR,
    TESTABLE_PAIRS,
    CatalogError,
    assert_no_substitution,
    catalog_coverage,
    is_testable,
    normalize_grade,
    normalize_specialization,
    suggest_upshift_grade,
    validate_test_pair,
)
from app.core.question_bank import PREDEFINED_QUESTIONS


def test_testable_pairs_match_first_scenario():
    assert TESTABLE_PAIRS == {
        ("Backend", "junior"),
        ("Backend", "middle"),
        ("Backend", "senior"),
    }


def test_lead_kept_in_data_but_hidden_from_test():
    assert "lead" in ALL_GRADES  # из данных не удаляем
    assert not is_testable("Backend", "lead")
    with pytest.raises(CatalogError):
        validate_test_pair("Backend", "lead")


def test_other_specializations_kept_but_hidden():
    assert "Frontend" in ALL_SPECIALIZATIONS  # данные не удаляем
    assert not is_testable("Frontend", "middle")
    with pytest.raises(CatalogError, match="пока недоступен"):
        validate_test_pair("Frontend", "middle")


def test_each_testable_pair_has_enough_questions():
    coverage = catalog_coverage(PREDEFINED_QUESTIONS)
    for pair in TESTABLE_PAIRS:
        count = coverage.get(pair, 0)
        assert count >= MIN_QUESTIONS_PER_PAIR, f"{pair}: всего {count}"


def test_normalize_is_case_insensitive():
    assert normalize_specialization("backend") == "Backend"
    assert normalize_specialization("  Backend  ") == "Backend"
    assert normalize_grade("Junior") == "junior"
    assert normalize_grade("MIDDLE") == "middle"
    assert validate_test_pair("backend", "Junior") == ("Backend", "junior")


def test_unknown_pair_gives_clear_error_not_silent_fallback():
    with pytest.raises(CatalogError, match="Backend"):
        validate_test_pair("GameDev", "junior")
    with pytest.raises(CatalogError, match="Backend"):
        validate_test_pair("Backend", "architect")


def test_no_substitution_detector():
    ok_questions = [q for q in PREDEFINED_QUESTIONS if (q["specialization"], q["grade"]) == ("Backend", "junior")]
    assert_no_substitution("Backend", "junior", ok_questions)

    mixed = ok_questions[:1] + [
        q for q in PREDEFINED_QUESTIONS if (q["specialization"], q["grade"]) == ("Frontend", "junior")
    ][:1]
    with pytest.raises(CatalogError, match="подмена"):
        assert_no_substitution("Backend", "junior", mixed)


def test_missing_spec_or_grade_is_explicit_error_not_default():
    # Ни запрос, ни профиль не задали пару — дефолта Backend/junior больше нет.
    with pytest.raises(CatalogError, match="Не указаны"):
        validate_test_pair(None, None)
    with pytest.raises(CatalogError, match="Не указаны"):
        validate_test_pair("Backend", None)
    with pytest.raises(CatalogError, match="Не указаны"):
        validate_test_pair(None, "middle")
    with pytest.raises(CatalogError, match="Не указаны"):
        validate_test_pair("  ", "junior")


def test_upshift_never_suggests_untestable_grade():
    assert suggest_upshift_grade("Backend", "junior") == "middle"
    assert suggest_upshift_grade("Backend", "middle") == "senior"
    # Lead недоступен для теста — после уверенного Senior ничего не предлагаем.
    assert suggest_upshift_grade("Backend", "senior") is None
    assert suggest_upshift_grade("Backend", "lead") is None
    assert suggest_upshift_grade("Frontend", "middle") is None
    assert suggest_upshift_grade("Backend", "architect") is None
    assert suggest_upshift_grade(None, "middle") is None
