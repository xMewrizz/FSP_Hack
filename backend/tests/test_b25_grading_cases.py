"""Сценарии проверки кода: ожидаемые ответы остаются у проверяющего процесса."""

import random

import pytest

from app.core.code_sandbox.run_job import build_cases


@pytest.mark.parametrize("question_code", ["OPEN-BE-CODE-01", "OPEN-BE-CODE-02"])
def test_each_supported_question_gets_multiple_cases(question_code):
    cases = build_cases(question_code, random.Random(7))
    assert len(cases) == 12
    assert all(expected for _, expected in cases)
    assert cases != build_cases(question_code, random.Random(8))


def test_rate_limiter_cases_cover_window_boundary_and_keys():
    cases = build_cases("OPEN-BE-CODE-01", random.Random(7))
    assert cases[0][1] == [True, True, False, True]
    assert cases[1][1] == [True, True, False, True]


def test_lru_cases_cover_eviction_and_updates():
    cases = build_cases("OPEN-BE-CODE-02", random.Random(7))
    assert cases[0][1] == [1, None, 1, 3]
    assert cases[1][1] == [None, 2, None]


def test_unsupported_question_has_no_syntax_only_success():
    with pytest.raises(ValueError):
        build_cases("OPEN-DS-CODE-01", random.Random(7))
