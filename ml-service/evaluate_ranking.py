"""Собрать понятное сравнение формулы B-14 с простой сортировкой."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml-service"))
from app.core.ranking import baseline_rank, rank_candidates  # noqa: E402
from evaluate_independent_review import (  # noqa: E402
    checked_labels,
    first_relevant_rank,
    ndcg_at_5,
    precision_at_3,
    read_jsonl,
)


DATA = ROOT / "ml-service" / "data" / "synthetic_v1"
REPORT = ROOT / "docs" / "09-ranking-review.md"


def build_report() -> str:
    candidates = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    needs = json.loads((DATA / "needs.json").read_text(encoding="utf-8"))
    label_path = DATA / "relevance_reviewer_1.jsonl"
    review = read_jsonl(label_path)
    labels = checked_labels(review, set(review), label_path)
    lines = [
        "# Сравнение способов сортировки кандидатов",
        "",
        "Проверили, как два правила расставляют кандидатов **внутри уже подтверждённой категории**. Формула B-14 и простая сортировка получают одни и те же профили и потребности. Заявленный без теста грейд не даёт допуска в список.",
        "",
        "## Данные и правила",
        "",
        "В наборе B-03 есть 60 вымышленных профилей и пять потребностей. Для сравнения порядка пригодны три потребности Backend — Junior, Middle и Senior. Для каждой нашлось по четыре кандидата с подтверждённым в симуляции грейдом. Итого сравниваем 12 пар «потребность — кандидат». Результаты тестов и достижения ФСП тоже вымышлены.",
        "",
        "- **Простая сортировка** ставит выше кандидата с большим числом совпавших обязательных навыков. При равенстве порядок задаёт ID профиля.",
        "- **Формула B-14** учитывает вес совпавших навыков (до 55 баллов), результат теста (до 20), формат работы и город (до 10), сопоставимые ожидания зарплаты (до 10) и подтверждённое достижение ФСП (до 5). Отсутствие ФСП не исключает человека. Балл задаёт только место в списке — это не процент соответствия и не вероятность найма.",
        "",
        "Чтобы сравнить порядок, каждой из 12 пар заранее присвоили оценку: 0 — не подходит, 1 — можно рассмотреть, 2 — подходит. Оценки составил Codex по навыкам, формату и зарплате без просмотра баллов сортировки. Это **предварительная оценка вымышленных профилей**, а не мнение работодателя. В каждом из трёх запросов оценку 2 получил один кандидат.",
        "",
        "## Что получилось",
        "",
        "| Потребность | Первые три по B-14 | Первые три по навыкам | Место кандидата с оценкой 2: B-14 / простая | nDCG@4: B-14 / простая |",
        "|---|---|---|---:|---:|",
    ]
    rows = []
    for need in needs:
        code = need["synthetic_code"]
        eligible = [item for item in candidates if f"{code}:{item['synthetic_code']}" in labels]
        if not eligible:
            continue
        formula = [item["candidate_code"] for item in rank_candidates(need, eligible)]
        simple = baseline_rank(need, eligible)
        if set(formula) != set(simple) or len(formula) != len(simple):
            raise ValueError(f"Сортировки сравнивают разные профили для {code}")
        rows.append((need, formula, simple))
        lines.append(
            f"| {need['title']} | {', '.join(formula[:3])} | {', '.join(simple[:3])} | "
            f"{first_relevant_rank(formula, labels, code)} / {first_relevant_rank(simple, labels, code)} | "
            f"{ndcg_at_5(formula, labels, code):.3f} / {ndcg_at_5(simple, labels, code):.3f} |"
        )
    if len(rows) != 3 or sum(len(formula) for _, formula, _ in rows) != 12:
        raise ValueError("Ожидались три Backend-потребности и 12 оценённых пар")
    p3 = {(round(precision_at_3(order, labels, need["synthetic_code"]), 3)) for need, formula, simple in rows for order in (formula, simple)}
    if p3 != {0.333}:
        raise ValueError("Изменился результат P@3; обновите вывод отчёта")
    lines.extend((
        "",
        "По этой предварительной разметке B-14 поставила подходящего кандидата первым во всех трёх запросах; простая сортировка — вторым. nDCG@4 составила 1,000 против 0,797 в каждом запросе. P@3 у обеих — 0,333: подходящий кандидат один, и обе сортировки включили его в первую тройку. **Лучший порядок на этом наборе дала B-14**, поэтому в текущей выдаче оставлена формула.",
        "",
        "Этот результат не доказывает, что формула лучше на реальных кандидатах: и анкеты, и оценки вымышлены. Для такой проверки нужны реальные прохождения теста и оценки работодателей; она вынесена в B-32.",
        "",
        "## Как повторить",
        "",
        "Из корня репозитория:",
        "",
        "```bash",
        "python ml-service/evaluate_ranking.py",
        "python ml-service/evaluate_independent_review.py --ai-draft",
        "```",
        "",
        "Первый скрипт собирает этот документ, второй выводит метрики по каждому запросу. Исходные профили, потребности и предварительные оценки лежат в `ml-service/data/synthetic_v1`.",
        "Отдельный [эксперимент с обучаемыми моделями](15-ranking-model-experiment.md) использует другой синтетический набор; его результаты не входят в эту таблицу.",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    REPORT.write_text(build_report(), encoding="utf-8", newline="\n")
    print(REPORT)
