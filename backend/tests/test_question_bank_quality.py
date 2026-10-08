"""Проверки подготовленного банка B-02 без БД и app.models."""

from collections import Counter

from app.core.catalog import TESTABLE_PAIRS
from app.core.question_bank import PREDEFINED_QUESTIONS
from app.core.question_variants import BACKEND_FAMILIES, prepared_variants


def test_every_active_backend_question_has_three_distinct_versions():
    active = {q["code"]: q for q in PREDEFINED_QUESTIONS if q["specialization"] == "Backend"}
    assert set(BACKEND_FAMILIES) == set(active)
    for code, family in BACKEND_FAMILIES.items():
        variants = prepared_variants(code)
        assert len(variants) == 3, code
        assert [v["variant_id"] for v in variants] == ["v1", "v2", "v3"]
        assert len({v["question_text"] for v in variants}) == 3, code
        assert family["cases"][0]["params"] != family["cases"][1]["params"], code
        assert all(v["family_code"] == code for v in variants)
        assert all(v["skill"] == family["skill"] and v["rubric"] == family["rubric"] for v in variants)


def test_keys_and_metadata_are_valid_for_every_version():
    all_versions = [q for code in BACKEND_FAMILIES for q in prepared_variants(code)]
    all_versions += [q for q in PREDEFINED_QUESTIONS if q["specialization"] != "Backend"]
    codes = [q["code"] for q in all_versions]
    assert len(codes) == len(set(codes))
    for q in all_versions:
        assert q["question_type"] == "single_choice", q["code"]
        assert q["specialization"] and q["grade"] and q["topic"]
        assert q["question_text"] and q["explanation"]
        assert q["weight"] > 0
        ids = [o["id"] for o in q["options"]]
        texts = [o["text"] for o in q["options"]]
        assert ids == ["A", "B", "C", "D"], q["code"]
        assert len(texts) == len(set(texts)) and all(texts), q["code"]
        assert len(q["correct_answers"]) == 1 and q["correct_answers"][0] in ids, q["code"]


def test_three_testable_pairs_have_several_questions_and_unchanged_reserve():
    coverage = Counter((q["specialization"], q["grade"]) for q in PREDEFINED_QUESTIONS)
    assert all(coverage[pair] >= 4 for pair in TESTABLE_PAIRS)
    assert coverage[("Frontend", "junior")] == 1
    assert coverage[("DevOps / SRE", "junior")] == 1


def test_reference_keys_for_corrected_questions():
    by_code = {q["code"]: q for q in PREDEFINED_QUESTIONS}
    assert by_code["BE-MID-02"]["correct_answers"] == ["C"]
    assert "skip scan" in by_code["BE-MID-02"]["explanation"]
    assert by_code["BE-MID-03"]["options"][0]["text"] == "1"
    assert by_code["BE-SR-01"]["correct_answers"] == ["C"]
    assert "ключ" in by_code["BE-SR-01"]["explanation"]
    assert by_code["BE-SR-02"]["options"][2]["text"] == "Примерно 1/6"
    assert by_code["BE-SR-02"]["correct_answers"] == ["C"]
    assert by_code["BE-SR-03"]["correct_answers"] == ["B"]
    assert by_code["BE-SR-04"]["correct_answers"] == ["C"]


def test_numeric_variant_keys_follow_their_parameters():
    for variant in prepared_variants("BE-MID-03")[1:]:
        key = variant["correct_answers"][0]
        answer_text = next(o["text"] for o in variant["options"] if o["id"] == key)
        assert answer_text == str(variant["parameters"]["keys"])

    for variant in prepared_variants("BE-SR-02")[1:]:
        key = variant["correct_answers"][0]
        answer_text = next(o["text"] for o in variant["options"] if o["id"] == key)
        assert answer_text == f"Примерно 1/{variant['parameters']['nodes'] + 1}"

    assert [v["correct_answers"] for v in prepared_variants("BE-SR-03")] == [
        ["B"], ["A"], ["C"],
    ]
