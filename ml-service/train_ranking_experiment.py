"""Повторить учебное сравнение формулы B-14 с двумя простыми моделями."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from evaluate_ranking_experiment import DATA, evaluate, read_jsonl, validate


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.ranking import score_candidate  # noqa: E402

SEED = 2027
FEATURES = ("skills", "test", "format", "city", "salary", "fsp")
FEATURE_LABELS = ("Навыки", "Тест", "Формат", "Город", "Зарплата", "ФСП")
plt.rcParams["svg.hashsalt"] = "fsp-ranking-2027"


def feature_values(need: dict, candidate: dict) -> list[float]:
    result = score_candidate(need, candidate)
    if result is None:
        raise ValueError("Пара не прошла проверку специализации и грейда")
    need_format = str(need.get("work_format") or "").casefold()
    candidate_format = str(candidate.get("work_format") or "").casefold()
    return [
        result["parts"]["skills"] / 55,
        result["parts"]["test"] / 20,
        float(need_format == candidate_format),
        float(need_format != "remote" and need.get("city") == candidate.get("city")),
        float(result["salary_match"] is True),
        result["parts"]["fsp"] / 5,
    ]


def load() -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    candidates = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    needs = json.loads((DATA / "needs.json").read_text(encoding="utf-8"))
    pairs = read_jsonl(DATA / "pairs.jsonl")
    validate(candidates, needs, pairs)
    return pairs, {item["id"]: item for item in candidates}, {item["id"]: item for item in needs}


def prediction_rows(model, pairs: list[dict], candidates: dict[str, dict], needs: dict[str, dict]) -> list[dict]:
    holdout = [pair for pair in pairs if pair["split"] in ("validation", "test")]
    matrix = [feature_values(needs[pair["need_id"]], candidates[pair["candidate_id"]]) for pair in holdout]
    probabilities = model.predict_proba(matrix)
    return [
        {
            "pair_id": pair["pair_id"],
            "score": round(float(sum(int(label) * probability for label, probability in zip(model.classes_, row))), 12),
        }
        for pair, row in zip(holdout, probabilities)
    ]


def write_predictions(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def save_charts(matrix: list[list[float]], labels: list[int], models: dict, results: dict) -> None:
    logistic = models["logistic"].named_steps["logisticregression"]
    boosting = models["boosting"]

    values = np.column_stack((matrix, labels))
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(np.corrcoef(values, rowvar=False), vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(7), (*FEATURE_LABELS, "Метка"), rotation=45, ha="right")
    ax.set_yticks(range(7), (*FEATURE_LABELS, "Метка"))
    for row in range(7):
        for column in range(7):
            ax.text(column, row, f"{image.get_array()[row, column]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(ROOT / "ml-service" / "feature_correlation.svg", metadata={"Date": None})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3))
    image = ax.imshow(logistic.coef_, vmin=-4, vmax=4, cmap="coolwarm")
    ax.set_xticks(range(6), FEATURE_LABELS)
    ax.set_yticks(range(3), ("Не подходит", "Можно рассмотреть", "Подходит"))
    for row in range(3):
        for column in range(6):
            ax.text(column, row, f"{logistic.coef_[row, column]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(ROOT / "ml-service" / "logistic_coefficients.svg", metadata={"Date": None})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.barh(FEATURE_LABELS[::-1], boosting.feature_importances_[::-1])
    ax.set_xlabel("Доля уменьшения ошибки")
    fig.tight_layout()
    fig.savefig(ROOT / "ml-service" / "boosting_importance.svg", metadata={"Date": None})
    plt.close(fig)

    names = ("B-14", "Логистическая", "Бустинг", "Простая")
    keys = (("reference", "B-14"), ("logistic", None), ("boosting", None), ("reference", "простая"))
    n4 = []
    top = []
    for section, key in keys:
        records = [results[section][split][key] if key else results[section][split] for split in ("validation", "test")]
        n4.append(sum(item["mean_ndcg_at_5"] for item in records) / 2)
        top.append(sum(item["first_relevant_at_1"] for item in records))
    fig, ax = plt.subplots(figsize=(8, 3))
    bars = ax.bar(names, n4)
    ax.set_ylim(0, 1.07)
    ax.set_ylabel("nDCG@5")
    for bar, count in zip(bars, top):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}; первый {count}/18", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "ml-service" / "logistic_vs_formula_val_test.svg", metadata={"Date": None})
    plt.close(fig)

    for name in (
        "feature_correlation.svg", "logistic_coefficients.svg",
        "boosting_importance.svg", "logistic_vs_formula_val_test.svg",
    ):
        path = ROOT / "ml-service" / name
        path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8", newline="\n")


def run() -> dict:
    pairs, candidates, needs = load()
    train = [pair for pair in pairs if pair["split"] == "train"]
    matrix = [feature_values(needs[pair["need_id"]], candidates[pair["candidate_id"]]) for pair in train]
    labels = [pair["label"] for pair in train]

    logistic = make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=2000, random_state=SEED),
    )
    boosting = GradientBoostingClassifier(
        n_estimators=100, max_depth=2, learning_rate=0.1, random_state=SEED,
    )
    summary = {"reference": evaluate()}
    models = {}
    for name, model in (("logistic", logistic), ("boosting", boosting)):
        model.fit(matrix, labels)
        models[name] = model
        rows = prediction_rows(model, pairs, candidates, needs)
        output = DATA / f"{name}_predictions.jsonl"
        write_predictions(output, rows)
        result = evaluate(output)
        summary[name] = {split: result[split]["модель"] for split in ("validation", "test")}
        if name == "logistic":
            summary[name]["class_2_coefficients"] = {
                feature: round(float(value), 3)
                for feature, value in zip(FEATURES, model.named_steps["logisticregression"].coef_[2])
            }
        else:
            summary[name]["feature_importances"] = {
                feature: round(float(value), 3)
                for feature, value in zip(FEATURES, model.feature_importances_)
            }
    all_matrix = [feature_values(needs[pair["need_id"]], candidates[pair["candidate_id"]]) for pair in pairs]
    save_charts(all_matrix, [pair["label"] for pair in pairs], models, summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
