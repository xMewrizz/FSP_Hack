"""Создать синтетический набор для разработки ранжировщика, без реальных кандидатов."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))
from generate_synthetic import generate  # noqa: E402


SEED = 2027
DATA = ROOT / "ml-service" / "data" / "ranking_experiment_v1"
SPLITS = {"train": (18, 10), "validation": (6, 3), "test": (6, 3)}
SPLIT_CODES = {"train": "TR", "validation": "VA", "test": "TE"}
GRADES = ("junior", "middle", "senior")


def _label(need: dict, candidate: dict) -> tuple[int, str]:
    """Правило для учебной симуляции; не оценка работодателя и не балл B-14."""
    required = {item["name"].casefold() for item in need["required_skills"]}
    skills = {item.casefold() for item in candidate["skills"]}
    matched = required & skills
    format_ok = need["work_format"] == candidate["work_format"]
    city_ok = need["work_format"] == "remote" or need["city"] == candidate["city"]
    salary_ok = candidate["salary_basis"] == need["salary_basis"] and candidate["salary_expectation_min"] <= need["salary_max"]
    if len(matched) == len(required) and format_ok and city_ok and salary_ok:
        value = 2
    elif len(matched) >= 2 and (format_ok and city_ok or salary_ok):
        value = 1
    else:
        value = 0
    reason = (
        f"Навыки {len(matched)}/{len(required)}; "
        f"формат {'подходит' if format_ok else 'не подходит'}; "
        f"город {'подходит' if city_ok else 'не подходит'}; "
        f"зарплата {'в пределах бюджета' if salary_ok else 'не сопоставима или выше бюджета'}"
    )
    return value, reason


def build() -> dict:
    source = generate(seed=SEED, count=540)["candidates"]
    by_grade = {
        grade: sorted(
            (item for item in source if item["specialization"] == "Backend" and item["verified_grade"] == grade),
            key=lambda item: item["synthetic_code"],
        )
        for grade in GRADES
    }
    if any(len(items) != 30 for items in by_grade.values()):
        raise ValueError("Ожидалось 30 подтверждённых профилей каждого грейда")

    candidates: list[dict] = []
    needs: list[dict] = []
    pairs: list[dict] = []
    for grade in GRADES:
        offset = 0
        for split, (candidate_count, need_count) in SPLITS.items():
            group = by_grade[grade][offset:offset + candidate_count]
            offset += candidate_count
            candidates.extend({**item, "split": split} for item in group)
            for number in range(need_count):
                anchor = group[number]
                skills = sorted(anchor["skills"])
                selected = [skills[(number + position) % len(skills)] for position in range(3)]
                code = f"{grade[:2].upper()}-{SPLIT_CODES[split]}-{number + 1:02d}"
                need = {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"fsp/ranking-experiment/{SEED}/{code}")),
                    "synthetic_code": code,
                    "title": f"Backend {grade}: вариант {number + 1} ({split})",
                    "specialization": "Backend",
                    "required_grade": grade,
                    "required_skills": [
                        {"name": name, "weight": 3.0 if position == 0 else 1.0, "required": True}
                        for position, name in enumerate(selected)
                    ],
                    "work_format": anchor["work_format"],
                    "city": anchor["city"],
                    "salary_min": anchor["salary_expectation_min"] - 20_000,
                    "salary_max": anchor["salary_expectation_min"] + 20_000,
                    "salary_basis": "gross",
                    "split": split,
                }
                needs.append(need)
                for candidate in group:
                    label, reason = _label(need, candidate)
                    pairs.append({
                        "pair_id": f"{code}:{candidate['synthetic_code']}",
                        "need_id": need["id"],
                        "candidate_id": candidate["id"],
                        "split": split,
                        "label": label,
                        "reason": reason,
                        "label_source": "synthetic_rule_v1",
                    })

    for split in SPLITS:
        candidate_ids = {item["id"] for item in candidates if item["split"] == split}
        need_ids = {item["id"] for item in needs if item["split"] == split}
        assert candidate_ids and need_ids
        assert all(item["candidate_id"] in candidate_ids and item["need_id"] in need_ids for item in pairs if item["split"] == split)
    assert len({item["id"] for item in candidates}) == len(candidates)
    assert len({item["id"] for item in needs}) == len(needs)
    assert len({item["pair_id"] for item in pairs}) == len(pairs)
    return {"candidates": candidates, "needs": needs, "pairs": pairs}


def _payload(value: list[dict], *, jsonl: bool = False) -> bytes:
    if jsonl:
        return ("\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value) + "\n").encode("utf-8")
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write(output_dir: Path = DATA) -> dict:
    dataset = build()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "candidates.json": _payload(dataset["candidates"]),
        "needs.json": _payload(dataset["needs"]),
        "pairs.jsonl": _payload(dataset["pairs"], jsonl=True),
    }
    for name, payload in files.items():
        (output_dir / name).write_bytes(payload)
    counts = {
        split: {str(label): number for label, number in Counter(item["label"] for item in dataset["pairs"] if item["split"] == split).items()}
        for split in SPLITS
    }
    manifest = {
        "version": "ranking_experiment_v1",
        "seed": SEED,
        "label_source": "synthetic_rule_v1",
        "candidate_count": len(dataset["candidates"]),
        "need_count": len(dataset["needs"]),
        "pair_count": len(dataset["pairs"]),
        "labels_by_split": counts,
        "files_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()},
        "note": "Метки получены из вымышленных признаков отдельным правилом. Это набор для разработки кода, не проверка качества на реальных людях.",
    }
    (output_dir / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return manifest


if __name__ == "__main__":
    print(json.dumps(write(), ensure_ascii=False, indent=2))
