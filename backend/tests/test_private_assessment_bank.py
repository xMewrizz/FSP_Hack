"""The published demo bank cannot silently stand in for a private bank."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from app.core import assessment_bank
from app.core.assessment_catalog import BACKEND_QUESTION_CODES
from app.core.assessment_catalog_ds import DS_QUESTION_CODES
from app.core.open_question_bank import GRADE_OPEN_CODES, GRADE_RETAKE_OPEN_CODES, OPEN_QUESTIONS
from app.core.question_variants import prepared_variants


def example_pack() -> dict:
    codes = {
        code
        for grades in (BACKEND_QUESTION_CODES, DS_QUESTION_CODES)
        for skills in grades.values()
        for selected in skills.values()
        for code in selected
    } | {"BE-JR-04", "BE-JR-11", "BE-JR-12"}
    open_codes = {
        code
        for spec in GRADE_OPEN_CODES
        for grades in (GRADE_OPEN_CODES[spec], GRADE_RETAKE_OPEN_CODES[spec])
        for selected in grades.values()
        for code in selected
    }
    return {
        "version": 1,
        "bank_id": "test-private-v1",
        "closed_variants": {code: deepcopy(prepared_variants(code)) for code in sorted(codes)},
        "open_questions": [deepcopy(q) for q in OPEN_QUESTIONS if q["code"] in open_codes],
    }


def test_private_mode_requires_a_file(monkeypatch):
    assessment_bank.private_bank.cache_clear()
    monkeypatch.setenv("ASSESSMENT_BANK_MODE", "private")
    monkeypatch.delenv("ASSESSMENT_BANK_FILE", raising=False)
    with pytest.raises(RuntimeError, match="ASSESSMENT_BANK_FILE"):
        assessment_bank.private_bank()
    assessment_bank.private_bank.cache_clear()


def test_private_bank_rejects_missing_question(monkeypatch):
    pack = example_pack()
    monkeypatch.setattr(assessment_bank, "private_bank", lambda: pack)
    assessment_bank.validate_private_bank_coverage()
    pack["closed_variants"].pop("BE-JR-02")
    with pytest.raises(RuntimeError, match="пропущены"):
        assessment_bank.validate_private_bank_coverage()


def test_private_bank_rejects_incomplete_variant(monkeypatch):
    pack = example_pack()
    monkeypatch.setattr(assessment_bank, "private_bank", lambda: pack)
    pack["closed_variants"]["BE-JR-02"][1].pop("variant_id")
    with pytest.raises(RuntimeError, match="Неверная семья"):
        assessment_bank.validate_private_bank_coverage()


def test_private_mode_rejects_demo_assessment_history(monkeypatch):
    monkeypatch.setattr(assessment_bank, "private_bank", lambda: {"bank_id": "test-private-v1"})
    with pytest.raises(RuntimeError, match="другого банка"):
        assessment_bank.validate_assessment_bank_ids([{"bank_id": "demo"}])
    assessment_bank.validate_assessment_bank_ids([{"bank_id": "test-private-v1"}])


def test_private_bank_is_used_for_both_question_types(tmp_path: Path):
    pack = example_pack()
    pack["closed_variants"]["BE-JR-02"][0]["question_text"] = "Закрытое задание из внешнего файла"
    next(q for q in pack["open_questions"] if q["code"] == "OPEN-BE-ARCH-JR-01")[
        "question_text"
    ] = "Открытое задание из внешнего файла"
    path = tmp_path / "assessment-bank.json"
    path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    script = (
        "from app.core.question_variants import prepared_variants; "
        "from app.core.open_question_bank import get_open_question_by_code; "
        "from app.core.assessment_bank import validate_private_bank_coverage; "
        "validate_private_bank_coverage(); "
        "assert prepared_variants('BE-JR-02')[0]['question_text'] == 'Закрытое задание из внешнего файла'; "
        "assert get_open_question_by_code('OPEN-BE-ARCH-JR-01')['question_text'] == 'Открытое задание из внешнего файла'"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "ASSESSMENT_BANK_MODE": "private", "ASSESSMENT_BANK_FILE": str(path)},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
