import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_independent_review.py"
spec = importlib.util.spec_from_file_location("evaluate_independent_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class IndependentReviewTest(unittest.TestCase):
    def test_metrics_use_only_adjudicated_labels(self):
        labels = {"N01:A": 2, "N01:B": 0, "N01:C": 1, "N01:D": 2}
        self.assertAlmostEqual(review.precision_at_3(["A", "B", "C", "D"], labels, "N01"), 1 / 3)
        better = review.ndcg_at_5(["A", "D", "C", "B"], labels, "N01")
        worse = review.ndcg_at_5(["B", "C", "D", "A"], labels, "N01")
        self.assertAlmostEqual(better, 1.0)
        self.assertGreater(better, worse)

    def test_incomplete_or_unexplained_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.jsonl"
            with self.assertRaises(ValueError):
                review.checked_labels({"N01:A": {"label": 2, "reason": ""}}, {"N01:A"}, path)
            with self.assertRaises(ValueError):
                review.checked_labels({"N01:A": {"label": None, "reason": "навыки"}}, {"N01:A"}, path)
            with self.assertRaises(ValueError):
                review.checked_labels({"N01:A": {"label": 2, "reason": "навыки"}}, {"N01:A", "N01:B"}, path)

    def test_reviewers_must_see_the_same_candidate_data(self):
        first = {"N01:A": {"pair_id": "N01:A", "candidate_skills": ["Python"],
                            "label": 2, "reason": "подходит", "reviewer_type": "AI draft (Codex)"}}
        second = {"N01:A": {"pair_id": "N01:A", "candidate_skills": ["Python"],
                             "label": None, "reason": ""}}
        review.check_same_context(first, second)
        second["N01:A"]["candidate_skills"] = ["Java"]
        with self.assertRaises(ValueError):
            review.check_same_context(first, second)


if __name__ == "__main__":
    unittest.main()
