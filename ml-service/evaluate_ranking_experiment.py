"""Сравнить сортировки на синтетическом наборе; при наличии — оценки обученной модели."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml-service" / "data" / "ranking_experiment_v1"
sys.path.insert(0, str(ROOT / "backend"))
from app.core.ranking import baseline_rank, rank_candidates  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(candidates: list[dict], needs: list[dict], pairs: list[dict]) -> None:
    candidate_by_id = {item["id"]: item for item in candidates}
    need_by_id = {item["id"]: item for item in needs}
    if len(candidate_by_id) != len(candidates) or len(need_by_id) != len(needs):
        raise ValueError("Повторяющийся кандидат или запрос")
    if len({item["pair_id"] for item in pairs}) != len(pairs):
        raise ValueError("Повторяющаяся пара")
    pairs_by_need: dict[str, set[str]] = defaultdict(set)
    for pair in pairs:
        candidate = candidate_by_id[pair["candidate_id"]]
        need = need_by_id[pair["need_id"]]
        if candidate["split"] != pair["split"] or need["split"] != pair["split"]:
            raise ValueError(f"Утечка между частями набора: {pair['pair_id']}")
        if candidate["verified_grade"] != need["required_grade"] or candidate["specialization"] != need["specialization"]:
            raise ValueError(f"В паре неверная подтверждённая категория: {pair['pair_id']}")
        if type(pair["label"]) is not int or pair["label"] not in (0, 1, 2) or not pair["reason"]:
            raise ValueError(f"Нет оценки или объяснения: {pair['pair_id']}")
        if pair["pair_id"] != f"{need['synthetic_code']}:{candidate['synthetic_code']}":
            raise ValueError(f"Неверный pair_id: {pair['pair_id']}")
        pairs_by_need[need["id"]].add(candidate["id"])
    for need in needs:
        expected = {
            item["id"] for item in candidates
            if item["split"] == need["split"]
            and item["specialization"] == need["specialization"]
            and item["verified_grade"] == need["required_grade"]
        }
        if pairs_by_need[need["id"]] != expected:
            raise ValueError(f"Не все допустимые кандидаты оценены для {need['synthetic_code']}")
    split_candidates = {split: {item["id"] for item in candidates if item["split"] == split} for split in ("train", "validation", "test")}
    split_needs = {split: {item["id"] for item in needs if item["split"] == split} for split in ("train", "validation", "test")}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if split_candidates[left] & split_candidates[right] or split_needs[left] & split_needs[right]:
            raise ValueError("Кандидаты или запросы повторяются между частями набора")


def ndcg_at_5(order: list[str], labels: dict[str, int]) -> float:
    def dcg(values: list[int]) -> float:
        return sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(values[:5]))
    actual = dcg([labels[code] for code in order])
    ideal = dcg(sorted(labels.values(), reverse=True))
    return actual / ideal if ideal else 0.0


def metrics(order: list[str], labels: dict[str, int]) -> tuple[float, float, int | None]:
    p3 = sum(labels[code] == 2 for code in order[:3]) / min(3, len(order)) if order else 0.0
    first = next((index for index, code in enumerate(order, start=1) if labels[code] == 2), None)
    return p3, ndcg_at_5(order, labels), first


def evaluate(predictions_path: Path | None = None) -> dict:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files_sha256"].items():
        if hashlib.sha256((DATA / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Файл {name} отличается от зафиксированной версии набора")
    candidates = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    needs = json.loads((DATA / "needs.json").read_text(encoding="utf-8"))
    pairs = read_jsonl(DATA / "pairs.jsonl")
    validate(candidates, needs, pairs)
    predictions: dict[str, float] = {}
    if predictions_path is not None:
        rows = read_jsonl(predictions_path)
        predictions = {item["pair_id"]: item["score"] for item in rows}
        expected = {pair["pair_id"] for pair in pairs if pair["split"] in ("validation", "test")}
        if len(predictions) != len(rows) or set(predictions) != expected:
            raise ValueError("Оценки модели должны покрывать ровно validation и test без повторов")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in predictions.values()):
            raise ValueError("Оценки модели должны быть конечными числами")

    candidates_by_id = {item["id"]: item for item in candidates}
    pairs_by_need: dict[str, list[dict]] = defaultdict(list)
    for pair in pairs:
        pairs_by_need[pair["need_id"]].append(pair)
    results: dict[str, dict[str, list[tuple[float, float, int | None]]]] = defaultdict(lambda: defaultdict(list))
    for need in needs:
        group = pairs_by_need[need["id"]]
        eligible = [candidates_by_id[item["candidate_id"]] for item in group]
        labels = {candidate["synthetic_code"]: pair["label"] for candidate, pair in zip(eligible, group)}
        orders = {
            "B-14": [item["candidate_code"] for item in rank_candidates(need, eligible)],
            "простая": baseline_rank(need, eligible),
        }
        if predictions and need["split"] != "train":
            orders["модель"] = [
                candidate["synthetic_code"]
                for candidate in sorted(eligible, key=lambda item: (-predictions[f"{need['synthetic_code']}:{item['synthetic_code']}"], item["id"]))
            ]
        for name, order in orders.items():
            if set(order) != set(labels) or len(order) != len(labels):
                raise ValueError(f"Сортировка {name} потеряла кандидата для {need['synthetic_code']}")
            results[need["split"]][name].append(metrics(order, labels))

    summary = {}
    for split in ("train", "validation", "test"):
        summary[split] = {}
        for name, rows in results[split].items():
            summary[split][name] = {
                "needs": len(rows),
                "mean_p_at_3": round(sum(item[0] for item in rows) / len(rows), 3),
                "mean_ndcg_at_5": round(sum(item[1] for item in rows) / len(rows), 3),
                "first_relevant_at_1": sum(item[2] == 1 for item in rows),
            }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="JSONL с pair_id и score для validation и test")
    args = parser.parse_args()
    print("Синтетические метки: результат не показывает качество на реальных кандидатах")
    print(json.dumps(evaluate(args.predictions), ensure_ascii=False, indent=2))
