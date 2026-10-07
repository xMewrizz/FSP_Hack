"""Проверки данных B-03 без backend, БД и дополнительных зависимостей."""

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


GENERATOR_PATH = Path(__file__).resolve().parents[1] / "generate_synthetic.py"
spec = importlib.util.spec_from_file_location("generate_synthetic", GENERATOR_PATH)
assert spec and spec.loader
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class SyntheticDatasetTests(unittest.TestCase):
    def test_default_size_coverage_and_unlabeled_pairs(self):
        data = generator.generate()
        candidates, needs = data["candidates"], data["needs"]
        pairs, sample = data["all_pairs"], data["review_sample"]
        self.assertEqual((len(candidates), len(needs), len(pairs), len(sample)), (60, 5, 300, 30))
        cells = Counter((c["specialization"], c["declared_grade"]) for c in candidates)
        self.assertEqual(len(cells), 9)
        self.assertTrue(all(number >= 6 for number in cells.values()))
        self.assertTrue(all("final_label" not in p for p in pairs))
        self.assertTrue(all(p["reviewer_1"] is None and p["reviewer_2"] is None and p["final_label"] is None for p in sample))
        self.assertEqual(Counter(p["need_code"] for p in sample), {f"N{i:02d}": 6 for i in range(1, 6)})
        self.assertEqual(len({(p["need_id"], p["candidate_id"]) for p in sample}), 30)
        self.assertTrue({(p["need_id"], p["candidate_id"]) for p in sample}.issubset({(p["need_id"], p["candidate_id"]) for p in pairs}))
        self.assertEqual(len({c["id"] for c in candidates}), 60)
        self.assertEqual(len({n["id"] for n in needs}), 5)
        by_candidate = {c["id"]: c for c in candidates}
        by_need = {n["id"]: n for n in needs}
        for pair in pairs:
            self.assertEqual(pair["candidate_specialization"], by_candidate[pair["candidate_id"]]["specialization"])
            self.assertEqual(pair["need_grade"], by_need[pair["need_id"]]["required_grade"])

    def test_verification_and_fsp_are_clearly_synthetic(self):
        candidates = generator.generate()["candidates"]
        for candidate in candidates:
            if candidate["verified_grade"]:
                self.assertEqual(candidate["specialization"], "Backend")
                self.assertEqual(candidate["verification_source"], "synthetic_test")
                self.assertGreaterEqual(candidate["test_percentage"], 70)
            else:
                self.assertIsNone(candidate["test_percentage"])
            if candidate["fsp_verified"]:
                self.assertEqual(candidate["fsp_source"], "synthetic_fixture")
                self.assertTrue(candidate["fsp_achievements"])
        for grade in generator.GRADES:
            group = [c for c in candidates if c["specialization"] == "Backend" and c["declared_grade"] == grade]
            self.assertTrue(any(c["verified_grade"] for c in group))
            self.assertTrue(any(not c["verified_grade"] for c in group))
        self.assertTrue(any(c["resume_summary"] is None for c in candidates))
        self.assertTrue(any(not c["fsp_verified"] for c in candidates))

    def test_each_need_has_a_plausible_candidate_without_creating_labels(self):
        data = generator.generate()
        for need in data["needs"]:
            required = {item["name"] for item in need["required_skills"]}
            plausible = [
                c for c in data["candidates"]
                if c["specialization"] == need["specialization"]
                and c["declared_grade"] == need["required_grade"]
                and required.issubset(c["skills"])
                and c["work_format"] == need["work_format"]
                and c["city"] == need["city"]
                and c["salary_expectation_min"] <= need["salary_max"]
            ]
            self.assertTrue(plausible, need["synthetic_code"])

    def test_files_reproduce_byte_for_byte_and_manifest_hashes_match(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_dir, second_dir = Path(first), Path(second)
            manifest = generator.write_dataset(first_dir)
            generator.write_dataset(second_dir)
            for file in sorted(first_dir.iterdir()):
                self.assertEqual(file.read_bytes(), (second_dir / file.name).read_bytes())
            for name, expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256((first_dir / name).read_bytes()).hexdigest(), expected)
            self.assertEqual(json.loads((first_dir / "manifest.json").read_text(encoding="utf-8"))["pair_count"], 300)
            self.assertEqual(manifest["review_sample_count"], 30)

    def test_committed_dataset_matches_manifest(self):
        dataset_dir = GENERATOR_PATH.parent / "data" / generator.VERSION
        manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["files_sha256"].items():
            self.assertEqual(hashlib.sha256((dataset_dir / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
