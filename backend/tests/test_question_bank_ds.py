"""Тесты для банка вопросов Data Science (B-02)."""

from app.core.question_bank_ds import (
    DS_FAMILIES,
    ds_base_questions,
    ds_prepared_variants,
)


def test_ds_families_count_and_grades():
    assert len(DS_FAMILIES) == 12
    grades = [code.split("-")[1] for code in DS_FAMILIES]
    assert grades.count("JR") == 4
    assert grades.count("MID") == 4
    assert grades.count("SR") == 4


def test_ds_skills_coverage_across_grades():
    expected_skills = {
        "ds_python_pandas",
        "ds_sql_analytics",
        "ds_stats_ab",
        "ds_ml_modeling",
    }
    for grade_tag in ("JR", "MID", "SR"):
        grade_families = [f for code, f in DS_FAMILIES.items() if code.split("-")[1] == grade_tag]
        skills_in_grade = {f["skill_code"] for f in grade_families}
        assert skills_in_grade == expected_skills, f"Mismatch in {grade_tag}"


def test_every_ds_question_has_three_distinct_versions():
    for code, family in DS_FAMILIES.items():
        variants = ds_prepared_variants(code)
        assert len(variants) == 3, code
        assert [v["variant_id"] for v in variants] == ["v1", "v2", "v3"]
        assert len({v["question_text"] for v in variants}) == 3, code
        assert all(v["family_code"] == code for v in variants)
        assert all(v["specialization"] == "Data Science" for v in variants)
        assert all(v["skill"] == family["skill"] for v in variants)
        assert all(v["rubric"] == family["rubric"] for v in variants)
        assert all(v["source_url"].startswith("https://") for v in variants)


def test_ds_variant_answers_match_expected_text_after_rotation():
    for code, family in DS_FAMILIES.items():
        for variant, (_, answer_idx, _) in zip(ds_prepared_variants(code), family["cases"]):
            expected_text = family["options"][answer_idx]
            correct_key = variant["correct_answers"][0]
            selected_text = next(o["text"] for o in variant["options"] if o["id"] == correct_key)
            assert selected_text == expected_text, f"Key mismatch in {variant['code']}"


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

