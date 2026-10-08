"""Воспроизводимый набор для проверки категорий и подбора (B-03).

Генератор не обращается к БД и не создаёт реальные учётные записи. Все профили,
достижения и результаты тестов в наборе вымышлены.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import uuid
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.core.catalog import ALL_SPECIALIZATIONS, TESTABLE_PAIRS  # noqa: E402


VERSION = "synthetic_v1"
GRADES = ("junior", "middle", "senior")
SPECIALIZATIONS = ("Backend", "Frontend", "DevOps / SRE")
CITIES = ("Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск")
FORMATS = ("remote", "hybrid", "office")
SKILLS = {
    "Backend": ("Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kafka", "Тестирование API"),
    "Frontend": ("JavaScript", "TypeScript", "React", "CSS", "Тестирование UI", "Web Vitals", "Дизайн-системы"),
    "DevOps / SRE": ("Linux", "Docker", "CI/CD", "Kubernetes", "Prometheus", "Terraform", "Сети"),
}

NEED_CASES = (
    ("Backend Junior", "Backend", "junior", ("Python", "PostgreSQL"), "remote", "Казань", 110_000, 160_000),
    ("Backend Middle", "Backend", "middle", ("FastAPI", "PostgreSQL", "Redis"), "hybrid", "Москва", 190_000, 270_000),
    ("Backend Senior", "Backend", "senior", ("PostgreSQL", "Docker", "Kafka"), "remote", "Санкт-Петербург", 290_000, 400_000),
    ("Frontend Middle", "Frontend", "middle", ("React", "TypeScript", "CSS"), "hybrid", "Москва", 180_000, 260_000),
    ("DevOps Junior", "DevOps / SRE", "junior", ("Linux", "Docker", "CI/CD"), "remote", "Новосибирск", 120_000, 180_000),
)


def _stable_id(seed: int, kind: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fsp/{VERSION}/{seed}/{kind}/{index}"))


def generate(seed: int = 2026, count: int = 60) -> dict[str, Any]:
    """Создать данные в памяти. Число кандидатов >= 18 покрывает все 9 категорий."""
    if count < 18:
        raise ValueError("Нужно не меньше 18 кандидатов: по два на каждую из 9 категорий")
    if not set(SPECIALIZATIONS).issubset(ALL_SPECIALIZATIONS):
        raise ValueError("Специализации набора расходятся со справочником B-01")

    rng = random.Random(seed)
    cells = [(spec, grade) for spec in SPECIALIZATIONS for grade in GRADES]
    assigned = [cells[i % len(cells)] for i in range(count)]
    rng.shuffle(assigned)

    candidates: list[dict[str, Any]] = []
    seen_in_cell: Counter[tuple[str, str]] = Counter()
    for index, (spec, grade) in enumerate(assigned, start=1):
        seen_in_cell[(spec, grade)] += 1
        verified = (spec, grade) in TESTABLE_PAIRS and seen_in_cell[(spec, grade)] % 2 == 1
        fsp = index % 4 == 0
        skill_count = {"junior": 3, "middle": 4, "senior": 5}[grade]
        skills = sorted(rng.sample(SKILLS[spec], skill_count))
        candidates.append({
            "id": _stable_id(seed, "candidate", index),
            "synthetic_code": f"C{index:03d}",
            "specialization": spec,
            "declared_grade": grade,
            "verified_grade": grade if verified else None,
            "verification_source": "synthetic_test" if verified else None,
            "test_percentage": rng.randint(72, 94) if verified else None,
            "skills": skills,
            "city": rng.choice(CITIES),
            "work_format": rng.choice(FORMATS),
            "salary_expectation_min": {"junior": 110_000, "middle": 190_000, "senior": 290_000}[grade] + rng.randrange(0, 60_001, 10_000),
            "salary_basis": "gross",
            "fsp_verified": fsp,
            "fsp_source": "synthetic_fixture" if fsp else None,
            "fsp_achievements": ([{"type": "хакатон", "result": "финалист", "source": "synthetic_fixture"}] if fsp else []),
            "resume_summary": None if index % 5 == 0 else f"Вымышленный профиль: {spec}, {grade}; навыки: {', '.join(skills[:2])}.",
        })

    needs: list[dict[str, Any]] = []
    for index, (title, spec, grade, skills, work_format, city, salary_min, salary_max) in enumerate(NEED_CASES, start=1):
        needs.append({
            "id": _stable_id(seed, "need", index),
            "synthetic_code": f"N{index:02d}",
            "title": title,
            "specialization": spec,
            "required_grade": grade,
            "required_skills": [
                {"name": skill, "weight": 2.0 if position == 0 else 1.0, "required": True}
                for position, skill in enumerate(skills)
            ],
            "work_format": work_format,
            "city": city,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": "RUB",
            "salary_basis": "gross",
            "description": f"Вымышленная потребность: {title}. Основные навыки: {', '.join(skills)}.",
        })

        # У каждой потребности есть хотя бы один явно подходящий по исходным
        # признакам кандидат. Это контроль покрытия, а не эталонная разметка.
        anchor = next(c for c in candidates if (c["specialization"], c["declared_grade"]) == (spec, grade))
        anchor["skills"] = sorted(set(anchor["skills"]) | set(skills))
        anchor["city"] = city
        anchor["work_format"] = work_format
        anchor["salary_expectation_min"] = salary_min
        if anchor["resume_summary"] is not None:
            anchor["resume_summary"] = f"Вымышленный профиль: {spec}, {grade}; навыки: {', '.join(anchor['skills'][:2])}."

    all_pairs = [
        {
            "need_id": need["id"],
            "need_code": need["synthetic_code"],
            "need_specialization": need["specialization"],
            "need_grade": need["required_grade"],
            "need_skills": [item["name"] for item in need["required_skills"]],
            "need_work_format": need["work_format"],
            "need_city": need["city"],
            "need_salary_max": need["salary_max"],
            "candidate_id": candidate["id"],
            "candidate_code": candidate["synthetic_code"],
            "candidate_specialization": candidate["specialization"],
            "candidate_declared_grade": candidate["declared_grade"],
            "candidate_verified_grade": candidate["verified_grade"],
            "candidate_skills": candidate["skills"],
            "candidate_work_format": candidate["work_format"],
            "candidate_city": candidate["city"],
            "candidate_salary_expectation_min": candidate["salary_expectation_min"],
            "candidate_fsp_verified": candidate["fsp_verified"],
        }
        for need in needs for candidate in candidates
    ]

    # Небольшая выборка для первого ручного разбора: по шесть разных профилей
    # на потребность. Все 300 сочетаний остаются в отдельном файле.
    review_sample = []
    for need in needs:
        required = {item["name"] for item in need["required_skills"]}
        chosen: list[dict[str, Any]] = []
        checks = (
            lambda c: c["specialization"] == need["specialization"] and c["declared_grade"] == need["required_grade"] and required.issubset(c["skills"]),
            lambda c: c["specialization"] == need["specialization"] and c["declared_grade"] == need["required_grade"] and not required.issubset(c["skills"]),
            lambda c: c["specialization"] == need["specialization"] and c["declared_grade"] != need["required_grade"],
            lambda c: c["specialization"] != need["specialization"],
            lambda c: c["specialization"] == need["specialization"] and not c["fsp_verified"],
            lambda c: c["resume_summary"] is None,
        )
        for check in checks:
            candidate = next((c for c in candidates if c not in chosen and check(c)), None)
            if candidate is not None:
                chosen.append(candidate)
        for candidate in candidates:
            if len(chosen) == 6:
                break
            if candidate not in chosen:
                chosen.append(candidate)
        by_candidate = {pair["candidate_id"]: pair for pair in all_pairs if pair["need_id"] == need["id"]}
        review_sample.extend({**by_candidate[c["id"]], "reviewer_1": None, "reviewer_2": None, "final_label": None} for c in chosen)

    return {"candidates": candidates, "needs": needs, "all_pairs": all_pairs, "review_sample": review_sample}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n").encode("utf-8")


def write_dataset(output_dir: Path, seed: int = 2026, count: int = 60) -> dict[str, Any]:
    data = generate(seed=seed, count=count)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "candidates.json": _json_bytes(data["candidates"]),
        "needs.json": _json_bytes(data["needs"]),
        "all_pairs.jsonl": _jsonl_bytes(data["all_pairs"]),
        "review_sample.jsonl": _jsonl_bytes(data["review_sample"]),
    }
    for name, payload in files.items():
        (output_dir / name).write_bytes(payload)

    coverage = Counter((c["specialization"], c["declared_grade"]) for c in data["candidates"])
    manifest = {
        "version": VERSION,
        "seed": seed,
        "candidate_count": len(data["candidates"]),
        "need_count": len(data["needs"]),
        "pair_count": len(data["all_pairs"]),
        "review_sample_count": len(data["review_sample"]),
        "coverage": {f"{spec} / {grade}": coverage[(spec, grade)] for spec in SPECIALIZATIONS for grade in GRADES},
        "files_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()},
        "note": "Все данные вымышлены. 300 сочетаний — полный набор; 30 пар — первая выборка для ручного разбора с пустыми полями оценок.",
    }
    (output_dir / "manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создать воспроизводимый проверочный набор B-03")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "ml-service" / "data" / VERSION)
    args = parser.parse_args()
    if (args.seed, args.count) != (2026, 60) and args.out_dir == REPO_ROOT / "ml-service" / "data" / VERSION:
        parser.error("Для другого seed или размера укажите --out-dir, чтобы не перезаписать проверочный набор v1")
    result = write_dataset(args.out_dir, seed=args.seed, count=args.count)
    print(f"{result['candidate_count']} candidates, {result['need_count']} needs, {result['pair_count']} pairs, {result['review_sample_count']} for review")
