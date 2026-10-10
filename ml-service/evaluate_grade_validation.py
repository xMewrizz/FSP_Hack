"""Compare grade decisions with independent judgments; never invent labels."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


GRADES = ("junior", "middle", "senior")


def read_attempts(path: Path) -> list[dict]:
    rows = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Строка {number}: неверный JSON") from exc
        attempt_id = row.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id.strip() or attempt_id in seen:
            raise ValueError(f"Строка {number}: отсутствует или повторяется attempt_id")
        seen.add(attempt_id)
        if row.get("specialization") not in ("Backend", "Data Science / ML"):
            raise ValueError(f"Строка {number}: неизвестная специализация")
        if row.get("target_grade") not in GRADES:
            raise ValueError(f"Строка {number}: неизвестный грейд")
        if type(row.get("system_passed")) is not bool or type(row.get("independent_passed")) is not bool:
            raise ValueError(f"Строка {number}: нужны два независимых решения true/false")
        rows.append(row)
    if not rows:
        raise ValueError("Нет размеченных прохождений")
    return rows


def summarize(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["specialization"], row["target_grade"])].append(row)

    def counts(items: list[dict]) -> dict:
        matrix = Counter((item["system_passed"], item["independent_passed"]) for item in items)
        return {
            "attempts": len(items),
            "both_confirmed": matrix[(True, True)],
            "both_rejected": matrix[(False, False)],
            "system_confirmed_expert_rejected": matrix[(True, False)],
            "system_rejected_expert_confirmed": matrix[(False, True)],
        }

    return {
        "total": counts(rows),
        "by_specialization_and_grade": {
            f"{spec} / {grade}": counts(items)
            for (spec, grade), items in sorted(groups.items())
        },
        "scope": "Сравнение решений для размеченных прохождений; надёжность на всей популяции не оценивается.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSONL с обезличенными прохождениями и независимыми оценками")
    args = parser.parse_args()
    print(json.dumps(summarize(read_attempts(args.input)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
