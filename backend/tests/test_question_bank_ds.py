"""Технические проверки банка вопросов Data Science (B-02)."""

from collections import Counter

from app.core.assessment_catalog_ds import DS_QUESTION_CODES, DS_TARGET_QUESTIONS

from app.core.question_bank_ds import (
    DS_FAMILIES,
    DS_RETAKE,
    ds_base_questions,
    ds_prepared_variants,
)
from app.core.question_bank_ds_retake import RETAKE_ROWS


def test_ds_families_count_and_grades():
    assert len(DS_FAMILIES) == 181  # 180 обязательных + отдельный NumPy Senior
    grades = [code.split("-")[1] for code in DS_FAMILIES]
    assert grades.count("JR") == 60
    assert grades.count("MID") == 60
    assert grades.count("SR") == 61


def test_ds_skills_coverage_across_grades():
    for grade, groups in DS_QUESTION_CODES.items():
        assert set(groups) == set(DS_TARGET_QUESTIONS)
        for skill, codes in groups.items():
            assert len(codes) == DS_TARGET_QUESTIONS[skill], (grade, skill)
            assert len({DS_FAMILIES[code]["skill"] for code in codes}) == len(codes)
            assert all(DS_FAMILIES[code]["skill_code"] == skill for code in codes)


def test_ds_question_family_has_three_distinct_wordings_and_four_distinct_answers():
    for grade_groups in DS_QUESTION_CODES.values():
        for codes in grade_groups.values():
            for code in codes:
                variants = ds_prepared_variants(code)
                assert len({v["question_text"] for v in variants}) == 3
                assert len(DS_FAMILIES[code]["options"]) == 4
                assert len(set(DS_FAMILIES[code]["options"])) == 4
                assert all(v["source_url"].startswith("https://") for v in variants)


def test_ds_grade_has_the_same_required_skills_without_reusing_families():
    for grade_groups in DS_QUESTION_CODES.values():
        codes = [code for group in grade_groups.values() for code in group]
        assert len(codes) == len(set(codes)) == 60
    assert Counter(family["skill_code"] for family in DS_FAMILIES.values())["ds_numpy"] == 1


def test_every_ds_question_has_three_distinct_versions():
    for code, family in DS_FAMILIES.items():
        variants = ds_prepared_variants(code)
        assert len(variants) == 3, code
        assert [v["variant_id"] for v in variants] == ["v1", "v2", "v3"]
        assert len({v["question_text"] for v in variants}) == 3, code
        assert all(v["family_code"] == code for v in variants)
        assert all(v["specialization"] == "Data Science / ML" for v in variants)
        assert variants[0]["skill"] == variants[2]["skill"] == family["skill"]
        assert variants[0]["rubric"] == variants[2]["rubric"] == family["rubric"]
        assert variants[1]["skill_code"] == family["skill_code"]
        assert all(v["source_url"].startswith("https://") for v in variants)


def test_ds_variant_answers_match_expected_text_after_rotation():
    for code, family in DS_FAMILIES.items():
        for version, (variant, (_, answer_idx, _)) in enumerate(zip(ds_prepared_variants(code), family["cases"]), 1):
            expected_text = DS_RETAKE[code][1] if version == 2 and code in DS_RETAKE else family["options"][answer_idx]
            correct_key = variant["correct_answers"][0]
            selected_text = next(o["text"] for o in variant["options"] if o["id"] == correct_key)
            assert selected_text == expected_text, f"Key mismatch in {variant['code']}"


def test_retake_bank_has_independent_questions_for_every_required_ds_skill():
    assert len(RETAKE_ROWS) == 18
    assert len(DS_RETAKE) == 180
    for grade, groups in DS_QUESTION_CODES.items():
        for skill_code, codes in groups.items():
            assert len(codes) == 10
            for code in codes:
                first, retake = ds_prepared_variants(code)[:2]
                assert retake["question_text"] != first["question_text"]
                assert set(option["text"] for option in retake["options"]) != set(option["text"] for option in first["options"])
                assert next(option["text"] for option in retake["options"] if option["id"] == retake["correct_answers"][0]) not in {
                    option["text"] for option in first["options"]
                }
                assert len({option["text"] for option in retake["options"]}) == 4
                assert retake["source_url"].startswith("https://")


def test_ds_options_and_structure_validity():
    all_variants = [v for code in DS_FAMILIES for v in ds_prepared_variants(code)]
    codes = [v["code"] for v in all_variants]
    assert len(codes) == len(set(codes)), "Variant codes must be unique"

    for v in all_variants:
        assert v["question_type"] == "single_choice"
        assert v["grade"] in ("junior", "middle", "senior")
        assert v["topic"]
        assert v["weight"] in (1.0, 1.5, 2.0)
        option_ids = [o["id"] for o in v["options"]]
        option_texts = [o["text"] for o in v["options"]]
        assert option_ids == ["A", "B", "C", "D"]
        assert len(option_texts) == 4
        assert len(set(option_texts)) == 4, f"Duplicate option in {v['code']}"
        assert v["correct_answers"][0] in option_ids


def test_prepared_variants_integration_for_ds_questions():
    from app.core.question_variants import prepared_variants, variant_for_attempt

    for code in DS_FAMILIES:
        variants = prepared_variants(code)
        assert len(variants) == 3
        v1 = variant_for_attempt(code, 0)
        v2 = variant_for_attempt(code, 1)
        v3 = variant_for_attempt(code, 2)
        assert v1["variant_id"] == "v1"
        assert v2["variant_id"] == "v2"
        assert v3["variant_id"] == "v3"
        assert variant_for_attempt(code, 3)["variant_id"] == "v1"

