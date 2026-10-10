"""Load an unpublished assessment bank without placing its keys in Git."""

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def private_bank() -> dict[str, Any] | None:
    mode = os.getenv("ASSESSMENT_BANK_MODE", "demo").strip().lower()
    if mode == "demo":
        return None
    if mode != "private":
        raise RuntimeError("ASSESSMENT_BANK_MODE должен быть demo или private")
    filename = os.getenv("ASSESSMENT_BANK_FILE", "").strip()
    if not filename:
        raise RuntimeError("Для закрытого банка задайте ASSESSMENT_BANK_FILE")
    path = Path(filename)
    if not path.is_file():
        raise RuntimeError(f"Файл закрытого банка не найден: {path}")
    try:
        bank = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Закрытый банк не удалось прочитать как JSON") from exc
    if not isinstance(bank, dict) or bank.get("version") != 1:
        raise RuntimeError("Закрытый банк должен иметь version=1")
    if not isinstance(bank.get("bank_id"), str) or not bank["bank_id"].strip() or bank["bank_id"] == "demo":
        raise RuntimeError("Закрытому банку нужен отдельный bank_id")
    if not isinstance(bank.get("closed_variants"), dict) or not isinstance(bank.get("open_questions"), list):
        raise RuntimeError("В закрытом банке нужны closed_variants и open_questions")
    return bank


def active_bank_id() -> str:
    bank = private_bank()
    return bank["bank_id"] if bank is not None else "demo"


def validate_assessment_bank_ids(policies: list[dict]) -> None:
    """Do not mix confirmed grades from a public demo and a private bank."""
    current = active_bank_id()
    if any((policy or {}).get("bank_id", "demo") != current for policy in policies):
        raise RuntimeError("База содержит наборы другого банка заданий; используйте отдельную базу")


def validate_private_bank_coverage() -> None:
    """Refuse to start a private assessment with missing or invalid questions."""
    bank = private_bank()
    if bank is None:
        return

    from app.core.assessment_catalog import BACKEND_QUESTION_CODES
    from app.core.assessment_catalog_ds import DS_QUESTION_CODES
    from app.core.open_question_bank import GRADE_OPEN_CODES, GRADE_RETAKE_OPEN_CODES

    expected_closed = {
        code
        for grades in (BACKEND_QUESTION_CODES, DS_QUESTION_CODES)
        for skills in grades.values()
        for codes in skills.values()
        for code in codes
    }
    closed_pairs = {
        code: (specialization, grade)
        for specialization, grades in (("Backend", BACKEND_QUESTION_CODES), ("Data Science / ML", DS_QUESTION_CODES))
        for grade, skills in grades.items()
        for codes in skills.values()
        for code in codes
    }
    # Git Junior is currently the only additional test.
    expected_closed.update(("BE-JR-04", "BE-JR-11", "BE-JR-12"))
    closed_pairs.update({code: ("Backend", "junior") for code in ("BE-JR-04", "BE-JR-11", "BE-JR-12")})
    closed = bank["closed_variants"]
    if set(closed) != expected_closed:
        missing = sorted(expected_closed - set(closed))
        extra = sorted(set(closed) - expected_closed)
        raise RuntimeError(f"Закрытый банк: пропущены {missing[:5]}, лишние {extra[:5]}")
    for code, variants in closed.items():
        if not isinstance(variants, list) or len(variants) < 2:
            raise RuntimeError(f"Для {code} нужны минимум два разных варианта")
        texts: set[str] = set()
        variant_codes: set[str] = set()
        for index, variant in enumerate(variants):
            if (not isinstance(variant, dict) or variant.get("family_code") != code
                    or not isinstance(variant.get("code"), str)
                    or variant.get("variant_id") != f"v{index + 1}"
                    or not isinstance(variant.get("topic"), str)
                    or not variant["topic"].strip()
                    or variant.get("question_type") != "single_choice"
                    or (variant.get("specialization"), variant.get("grade")) != closed_pairs[code]
                    or type(variant.get("weight")) not in (int, float)
                    or variant["weight"] <= 0):
                raise RuntimeError(f"Неверная семья вопроса {code}")
            text = variant.get("question_text")
            if (index == 0 and variant["code"] != code) or variant["code"] in variant_codes:
                raise RuntimeError(f"У {code} неверный или повторяющийся код варианта")
            variant_codes.add(variant["code"])
            options = variant.get("options")
            answers = variant.get("correct_answers")
            if not isinstance(text, str) or not text.strip() or text in texts:
                raise RuntimeError(f"У {code} повторяется или отсутствует условие")
            texts.add(text)
            if not isinstance(options, list) or len(options) < 2 or not isinstance(answers, list) or len(answers) != 1:
                raise RuntimeError(f"У {code} нет вариантов или ключа")
            if any(
                not isinstance(item, dict)
                or not isinstance(item.get("id"), str) or not item["id"].strip()
                or not isinstance(item.get("text"), str) or not item["text"].strip()
                for item in options
            ):
                raise RuntimeError(f"У {code} неполные варианты ответа")
            option_ids = {item["id"] for item in options}
            if len(option_ids) != len(options) or not set(answers) <= option_ids:
                raise RuntimeError(f"Ключ вопроса {code} не соответствует вариантам ответа")
            if not isinstance(variant.get("explanation"), str) or not variant["explanation"].strip():
                raise RuntimeError(f"У {code} нет объяснения")

    expected_open = {
        code
        for spec in GRADE_OPEN_CODES
        for grades in (GRADE_OPEN_CODES[spec], GRADE_RETAKE_OPEN_CODES[spec])
        for codes in grades.values()
        for code in codes
    }
    open_pairs = {
        code: (spec, grade)
        for spec in GRADE_OPEN_CODES
        for grades in (GRADE_OPEN_CODES[spec], GRADE_RETAKE_OPEN_CODES[spec])
        for grade, codes in grades.items()
        for code in codes
    }
    questions = bank["open_questions"]
    by_code = {question.get("code"): question for question in questions if isinstance(question, dict)}
    if len(by_code) != len(questions) or set(by_code) != expected_open:
        raise RuntimeError("Закрытый банк открытых заданий неполон или содержит повторяющиеся коды")
    for code, question in by_code.items():
        criteria = question.get("rubric_criteria")
        critical = question.get("critical_criteria", [])
        if (not isinstance(question.get("title"), str) or not question["title"].strip()
                or (question.get("specialization"), question.get("grade")) != open_pairs[code]
                or not isinstance(question.get("skill"), str) or not question["skill"].strip()
                or question.get("question_type") not in ("code", "free_text")
                or not isinstance(question.get("question_text"), str)
                or not question["question_text"].strip()
                or not isinstance(question.get("reference_solution"), str)
                or not question["reference_solution"].strip()
                or not isinstance(criteria, list) or len(criteria) < 3
                or any(not isinstance(item, str) or not item.strip() for item in criteria)
                or not isinstance(critical, list)
                or any(type(index) is not int or index < 1 or index > len(criteria) for index in critical)):
            raise RuntimeError(f"Неполное открытое задание {code}")
        if question["question_type"] == "code":
            contract = question.get("sandbox_contract")
            if (not isinstance(contract, dict)
                    or not isinstance(contract.get("function_name"), str)
                    or not re.fullmatch(r"[a-z][a-z0-9_]*", contract["function_name"])
                    or not isinstance(contract.get("cases"), list)
                    or len(contract["cases"]) < 5
                    or any(not isinstance(case, dict)
                           or not isinstance(case.get("args"), list)
                           or "expected" not in case
                           for case in contract["cases"])):
                raise RuntimeError(f"У задания {code} нет закрытого контракта проверки кода")
