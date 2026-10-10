"""Создать две независимые формы оценки пар «потребность — кандидат»."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data" / "synthetic_v1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def review_rows(data: Path = DATA) -> list[dict]:
    candidates = {item["id"]: item for item in read_json(data / "candidates.json")}
    needs = {item["id"]: item for item in read_json(data / "needs.json")}
    rows = []
    for line in (data / "all_pairs.jsonl").read_text(encoding="utf-8").splitlines():
        pair = json.loads(line)
        candidate = candidates[pair["candidate_id"]]
        need = needs[pair["need_id"]]
        if candidate["specialization"] != need["specialization"]:
            continue
        if candidate["verified_grade"] != need["required_grade"]:
            continue
        rows.append({
            "pair_id": f"{need['synthetic_code']}:{candidate['synthetic_code']}",
            "need": need["title"],
            "need_skills": [item["name"] for item in need["required_skills"]],
            "need_format": need["work_format"],
            "need_city": need["city"],
            "need_salary_max_gross_rub": need["salary_max"],
            "candidate_skills": candidate["skills"],
            "candidate_format": candidate["work_format"],
            "candidate_city": candidate["city"],
            "candidate_salary_min_gross_rub": candidate["salary_expectation_min"],
            "candidate_resume_summary": candidate["resume_summary"],
            "candidate_fsp_demo": bool(candidate["fsp_achievements"]),
            "label": None,
            "reason": "",
        })
    return sorted(rows, key=lambda item: item["pair_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--reviewers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    rows = review_rows(args.data_dir)
    for reviewer in range(1, args.reviewers + 1):
        path = args.data_dir / f"relevance_reviewer_{reviewer}.jsonl"
        if path.exists():
            raise SystemExit(f"Файл уже существует, не перезаписываю: {path}")
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
        print(f"{path}: {len(rows)} пар")


if __name__ == "__main__":
    main()
