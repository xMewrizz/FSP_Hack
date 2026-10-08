"""Проверки учебного набора ранжирования и разделения данных."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script("build_ranking_experiment")
evaluator = load_script("evaluate_ranking_experiment")


class RankingExperimentTests(unittest.TestCase):
    def test_saved_data_reproduces_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = builder.write(Path(directory))
            saved = json.loads((builder.DATA / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(generated, saved)
            for name, digest in saved["files_sha256"].items():
                self.assertEqual(hashlib.sha256((builder.DATA / name).read_bytes()).hexdigest(), digest)

    def test_splits_and_all_labels_are_complete(self):
        data = builder.build()
        self.assertEqual((len(data["candidates"]), len(data["needs"]), len(data["pairs"])), (90, 48, 648))
        evaluator.validate(**data)
        labels = {split: {row["label"] for row in data["pairs"] if row["split"] == split} for split in builder.SPLITS}
        self.assertEqual(labels, {split: {0, 1, 2} for split in builder.SPLITS})

    def test_cross_split_pair_and_missing_label_are_rejected(self):
        data = builder.build()
        broken = copy.deepcopy(data)
        broken["pairs"][0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "Утечка"):
            evaluator.validate(**broken)
        broken = copy.deepcopy(data)
        broken["pairs"][0]["reason"] = ""
        with self.assertRaisesRegex(ValueError, "Нет оценки"):
            evaluator.validate(**broken)

    def test_model_predictions_require_full_holdout_and_finite_scores(self):
        data = builder.build()
        held_out = [row for row in data["pairs"] if row["split"] != "train"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            path.write_text("\n".join(json.dumps({"pair_id": row["pair_id"], "score": 0.5}) for row in held_out) + "\n", encoding="utf-8")
            result = evaluator.evaluate(path)
            self.assertIn("модель", result["validation"])
            self.assertIn("модель", result["test"])
            self.assertNotIn("модель", result["train"])
            path.write_text(json.dumps({"pair_id": held_out[0]["pair_id"], "score": 0.5}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ровно validation и test"):
                evaluator.evaluate(path)


if __name__ == "__main__":
    unittest.main()
