"""Смысловые проверки расчёта B-14 без БД и app.models."""

import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.core.ranking import rank_candidates, score_candidate  # noqa: E402


SCRIPT_PATH = REPO_ROOT / "ml-service" / "evaluate_ranking.py"
spec = importlib.util.spec_from_file_location("evaluate_ranking", SCRIPT_PATH)
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


NEED = {
    "specialization": "Backend",
    "required_grade": "middle",
    "required_skills": [
        {"name": "Python", "weight": 2},
        {"name": "PostgreSQL", "weight": 1},
    ],
    "work_format": "remote",
    "city": "Москва",
    "salary_max": 250000,
    "salary_basis": "gross",
}


def candidate(**changes):
    value = {
        "id": "1",
        "synthetic_code": "C001",
        "specialization": "Backend",
        "declared_grade": "middle",
        "verified_grade": "middle",
        "skills": ["Python", "PostgreSQL"],
        "test_percentage": 80,
        "work_format": "remote",
        "city": "Казань",
        "salary_expectation_min": 200000,
        "salary_basis": "gross",
        "fsp_verified": False,
        "fsp_achievements": [],
    }
    value.update(changes)
    return value


class RankingTests(unittest.TestCase):
    def test_wrong_specialization_or_grade_never_gets_points(self):
        self.assertIsNone(score_candidate(NEED, candidate(specialization="Frontend")))
        self.assertIsNone(score_candidate(NEED, candidate(verified_grade="senior")))
        self.assertIsNone(score_candidate(NEED, candidate(verified_grade=None, declared_grade="junior")))

    def test_declared_grade_is_not_admitted(self):
        confirmed = candidate(id="1", skills=["Python"], test_percentage=70)
        declared_only = candidate(id="2", verified_grade=None, skills=["Python", "PostgreSQL"], test_percentage=None)
        self.assertIsNone(score_candidate(NEED, declared_only))
        ranked = rank_candidates(NEED, [declared_only, confirmed])
        self.assertEqual([item["candidate_id"] for item in ranked], ["1"])

    def test_required_skill_outweighs_fsp_bonus(self):
        full = score_candidate(NEED, candidate())
        missing_with_fsp = score_candidate(
            NEED,
            candidate(skills=["Python"], fsp_verified=True, fsp_achievements=[{"type": "хакатон"}]),
        )
        self.assertGreater(full["points"], missing_with_fsp["points"])
        self.assertEqual(missing_with_fsp["parts"]["fsp"], 5)
        self.assertEqual(missing_with_fsp["group"], "confirmed")

    def test_remote_city_ignored_and_salary_basis_matters(self):
        base = score_candidate(NEED, candidate())
        another_city = score_candidate(NEED, candidate(city="Москва"))
        net_salary = score_candidate(NEED, candidate(salary_basis="net"))
        self.assertEqual(base["parts"]["work"], another_city["parts"]["work"])
        self.assertEqual(base["parts"]["salary"], 10)
        self.assertEqual(net_salary["parts"]["salary"], 0)
        self.assertIsNone(net_salary["salary_match"])
        office_need = {**NEED, "work_format": "office"}
        wrong_format = score_candidate(office_need, candidate(work_format="remote", city="Москва"))
        self.assertEqual(wrong_format["parts"]["work"], 0)

    def test_weighted_skills_and_test_result_change_order(self):
        light = score_candidate(NEED, candidate(skills=["PostgreSQL"]))
        heavy = score_candidate(NEED, candidate(skills=["Python"]))
        self.assertGreater(heavy["parts"]["skills"], light["parts"]["skills"])
        low = score_candidate(NEED, candidate(test_percentage=70))
        high = score_candidate(NEED, candidate(test_percentage=90))
        self.assertGreater(high["parts"]["test"], low["parts"]["test"])

    def test_report_uses_all_five_needs_without_quality_claim(self):
        text = report.build_report()
        self.assertEqual(text.count("| Backend "), 3)
        self.assertIn("| Frontend Middle |", text)
        self.assertIn("| DevOps Junior |", text)
        self.assertIn("Независимых оценок релевантности пока нет", text)
        self.assertNotIn("Только заявили грейд", text)
        self.assertIn("Заявленный грейд допуска не даёт", text)
        self.assertIn("Пустая выдача: Frontend Middle, DevOps Junior", text)


if __name__ == "__main__":
    unittest.main()
