"""Сравнить две сортировки по предварительным или согласованным оценкам."""

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


def check_same_context(first: dict[str, dict], second: dict[str, dict]) -> None:
    if set(first) != set(second):
        raise ValueError("Проверяющим достались разные наборы пар")
    ignored = {"label", "reason", "reviewer_type"}
    for pair_id in first:
        left = {key: value for key, value in first[pair_id].items() if key not in ignored}
        right = {key: value for key, value in second[pair_id].items() if key not in ignored}
        if left != right:
            raise ValueError(f"Описание пары {pair_id} различается между формами")


def precision_at_3(order: list[str], labels: dict[str, int], need_code: str) -> float:
    return sum(labels[f"{need_code}:{code}"] == 2 for code in order[:3]) / min(3, len(order)) if order else 0.0


def first_relevant_rank(order: list[str], labels: dict[str, int], need_code: str) -> int | None:
    return next((index for index, code in enumerate(order, start=1) if labels[f"{need_code}:{code}"] == 2), None)


def ndcg_at_5(order: list[str], labels: dict[str, int], need_code: str) -> float:
    values = [labels[f"{need_code}:{code}"] for code in order]
    def dcg(items: list[int]) -> float:
        return sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(items[:5]))
    ideal = dcg(sorted(values, reverse=True))
    return dcg(values) / ideal if ideal else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-labels", type=Path, help="Согласованные метки; JSONL с pair_id, label, reason")
    parser.add_argument("--ai-draft", action="store_true", help="Предварительный расчёт по текущей разметке")
    args = parser.parse_args()
    if args.ai_draft and args.final_labels is not None:
        parser.error("Укажите только --ai-draft или --final-labels")

    first_path = DATA / "relevance_reviewer_1.jsonl"
    first = read_jsonl(first_path)
    expected = set(first)
    if args.ai_draft:
        final = checked_labels(first, expected, first_path)
        print("Предварительный расчёт на AI-оценках синтетических профилей. Независимой проверки нет.")
    else:
        second_path = DATA / "relevance_reviewer_2.jsonl"
        second = read_jsonl(second_path)
        check_same_context(first, second)
        for path, rows in ((first_path, first), (second_path, second)):
            filled = sum(type(row.get("label")) is int and row["label"] in (0, 1, 2) for row in rows.values())
            print(f"{path.name}: {filled}/{len(expected)} оценок")
        if args.final_labels is None:
            print("Согласованных меток нет; метрики подбора не рассчитывались")
            return
        if args.final_labels.resolve() in (first_path.resolve(), second_path.resolve()):
            raise ValueError("Согласованные метки нужно сохранить отдельно от исходных форм")
        left = checked_labels(first, expected, first_path)
        right = checked_labels(second, expected, second_path)
        agreed = sum(left[pair_id] == right[pair_id] for pair_id in expected)
        print(f"Совпадение предварительной AI-оценки и второго проверяющего: {agreed}/{len(expected)}")
        for pair_id in sorted(expected):
            if left[pair_id] != right[pair_id]:
                print(f"Расхождение {pair_id}: {left[pair_id]} и {right[pair_id]}")
        final = checked_labels(read_jsonl(args.final_labels), expected, args.final_labels)
    candidates = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    needs = json.loads((DATA / "needs.json").read_text(encoding="utf-8"))
    print("Сравнение прототипа B-14 с простой сортировкой; API подбора B-15 пока использует другую логику")
    print("Запрос | Сортировка | Первый релевантный | P@3 | nDCG@min(5,N) | Кандидатов | Максимум P@3")
    for need in needs:
        need_code = need["synthetic_code"]
        eligible = [item for item in candidates if f"{need_code}:{item['synthetic_code']}" in expected]
        if not eligible:
            continue
        ranked = [item["candidate_code"] for item in rank_candidates(need, eligible)["confirmed"]]
        baseline = baseline_rank(need, eligible)["confirmed"]
        if set(ranked) != {item["synthetic_code"] for item in eligible} or set(baseline) != set(ranked):
            raise ValueError(f"Сортировка потеряла кандидата для {need_code}")
        relevant_count = sum(final[f"{need_code}:{code}"] == 2 for code in ranked)
        maximum_p3 = min(relevant_count, 3) / min(3, len(ranked))
        for name, order in (("Прототип B-14", ranked), ("Простая", baseline)):
            first_rank = first_relevant_rank(order, final, need_code)
            print(f"{need_code} | {name} | {first_rank if first_rank is not None else 'нет'} | "
                  f"{precision_at_3(order, final, need_code):.3f} | "
                  f"{ndcg_at_5(order, final, need_code):.3f} | {len(order)} | {maximum_p3:.3f}")


if __name__ == "__main__":
    main()
