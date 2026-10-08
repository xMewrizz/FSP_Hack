"""Проверить независимую разметку и сравнить две сортировки после согласования меток."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml-service" / "data" / "synthetic_v1"
sys.path.insert(0, str(ROOT / "backend"))
from app.core.ranking import baseline_rank, rank_candidates  # noqa: E402


def read_jsonl(path: Path) -> dict[str, dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {row["pair_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Повторяющийся pair_id: {path}")
    return result


def checked_labels(rows: dict[str, dict], expected_ids: set[str], path: Path) -> dict[str, int]:
    if set(rows) != expected_ids:
        raise ValueError(f"В {path} набор пар отличается от исходного")
    labels = {}
    for pair_id, row in rows.items():
        value = row.get("label")
        if type(value) is not int or value not in (0, 1, 2):
            raise ValueError(f"В {path} нет оценки 0, 1 или 2 для {pair_id}")
        if not str(row.get("reason") or "").strip():
            raise ValueError(f"В {path} нет краткого объяснения для {pair_id}")
        labels[pair_id] = value
    return labels


def precision_at_3(order: list[str], labels: dict[str, int], need_code: str) -> float:
    return sum(labels[f"{need_code}:{code}"] == 2 for code in order[:3]) / min(3, len(order))


def ndcg_at_5(order: list[str], labels: dict[str, int], need_code: str) -> float:
    values = [labels[f"{need_code}:{code}"] for code in order]
    def dcg(items: list[int]) -> float:
        return sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(items[:5]))
    ideal = dcg(sorted(values, reverse=True))
    return dcg(values) / ideal if ideal else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-labels", type=Path, help="Согласованные метки; JSONL с pair_id, label, reason")
    args = parser.parse_args()

    first_path = DATA / "relevance_reviewer_1.jsonl"
    second_path = DATA / "relevance_reviewer_2.jsonl"
    first = read_jsonl(first_path)
    second = read_jsonl(second_path)
    if set(first) != set(second):
        raise ValueError("Проверяющим достались разные наборы пар")
    expected = set(first)
    for path, rows in ((first_path, first), (second_path, second)):
        filled = sum(type(row.get("label")) is int and row["label"] in (0, 1, 2) for row in rows.values())
        print(f"{path.name}: {filled}/{len(expected)} оценок")
    if args.final_labels is None:
        return

    left = checked_labels(first, expected, first_path)
    right = checked_labels(second, expected, second_path)
    agreed = sum(left[pair_id] == right[pair_id] for pair_id in expected)
    print(f"Совпадение проверяющих: {agreed}/{len(expected)}")
    for pair_id in sorted(expected):
        if left[pair_id] != right[pair_id]:
            print(f"Расхождение {pair_id}: {left[pair_id]} и {right[pair_id]}")

    final = checked_labels(read_jsonl(args.final_labels), expected, args.final_labels)
    candidates = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    needs = json.loads((DATA / "needs.json").read_text(encoding="utf-8"))
    print("Запрос | Сортировка | P@3 | nDCG@5 | Кандидатов")
    for need in needs:
        need_code = need["synthetic_code"]
        eligible = [item for item in candidates if f"{need_code}:{item['synthetic_code']}" in expected]
        if not eligible:
            continue
        ranked = [item["candidate_code"] for item in rank_candidates(need, eligible)["confirmed"]]
        baseline = baseline_rank(need, eligible)["confirmed"]
        if set(ranked) != {item["synthetic_code"] for item in eligible} or set(baseline) != set(ranked):
            raise ValueError(f"Сортировка потеряла кандидата для {need_code}")
        for name, order in (("Текущая", ranked), ("Простая", baseline)):
            print(f"{need_code} | {name} | {precision_at_3(order, final, need_code):.3f} | "
                  f"{ndcg_at_5(order, final, need_code):.3f} | {len(order)}")


if __name__ == "__main__":
    main()
