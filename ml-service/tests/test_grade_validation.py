import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_grade_validation.py"
spec = importlib.util.spec_from_file_location("evaluate_grade_validation", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GradeValidationTests(unittest.TestCase):
    def test_counts_false_confirmations_separately(self):
        rows = [
            {"specialization": "Backend", "target_grade": "middle", "system_passed": True, "independent_passed": False},
            {"specialization": "Backend", "target_grade": "middle", "system_passed": False, "independent_passed": True},
            {"specialization": "Backend", "target_grade": "middle", "system_passed": True, "independent_passed": True},
        ]
        result = module.summarize(rows)
        self.assertEqual(result["total"]["system_confirmed_expert_rejected"], 1)
        self.assertEqual(result["total"]["system_rejected_expert_confirmed"], 1)

    def test_missing_or_nonindependent_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attempts.jsonl"
            path.write_text(json.dumps({
                "attempt_id": "one", "specialization": "Backend", "target_grade": "junior",
                "system_passed": True, "independent_passed": None,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "два независимых решения"):
                module.read_attempts(path)


if __name__ == "__main__":
    unittest.main()
