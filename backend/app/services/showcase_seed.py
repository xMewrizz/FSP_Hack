"""Explicit, repeatable import of the fictional showcase dataset.

This is deliberately a CLI operation, never a public API endpoint. Synthetic
accounts cannot sign in and their IDs are deterministic so reruns add nothing.
"""

from __future__ import annotations

import json
import secrets
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.grade_policy import SkillResult, assess_grade
from app.core.security import hash_password
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.employer_task import EmployerTask
from app.models.fsp import FSPAchievement
from app.models.test import GradeAssessment, TestSession
from app.models.user import User
from app.models.vacancy import Vacancy


NAMESPACE = uuid.UUID("44dc9e30-3cb2-4db2-9668-e3bd93e2b34d")


def showcase_id(kind: str, code: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"platform-showcase-v1:{kind}:{code}")


def load_dataset(directory: Path) -> dict[str, list[dict]]:
    data = {name: json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("manifest", "candidates", "companies", "vacancies", "tasks")}
    manifest = data["manifest"]
    for name in ("candidates", "companies", "vacancies", "tasks"):
        if len(data[name]) != manifest[name]:
            raise ValueError(f"Число {name} не совпадает с manifest.json")
        codes = [item["id"] for item in data[name]]
        if len(codes) != len(set(codes)):
            raise ValueError(f"Повторяющийся ID в {name}")
    companies = {item["id"] for item in data["companies"]}
    vacancies = {item["id"]: item for item in data["vacancies"]}
    for vacancy in vacancies.values():
        if vacancy["company_id"] not in companies:
            raise ValueError(f"Неизвестная компания у {vacancy['id']}")
    for task in data["tasks"]:
        vacancy = vacancies.get(task["vacancy_id"])
        if vacancy is None or vacancy["company_id"] != task["company_id"]:
            raise ValueError(f"Несогласованная вакансия у {task['id']}")
    pairs = Counter((item["specialization"], item["declared_grade"]) for item in data["candidates"])
    expected = {(item["specialization"], item["grade"]): manifest["candidates_per_pair"]
                for item in manifest["pairs"]}
    if pairs != expected:
        raise ValueError("Кандидаты распределены по специализациям и грейдам неверно")
    for candidate in data["candidates"]:
        if not candidate["email"].endswith("@example.test"):
            raise ValueError(f"Недемонстрационный email у {candidate['id']}")
        results = candidate["required_test_results"]
        present = [item for item in results if item["percentage"] is not None]
        if candidate["verified_grade"]:
            if candidate["verified_grade"] != candidate["declared_grade"] or len(present) != len(results):
                raise ValueError(f"Некорректный подтверждённый грейд у {candidate['id']}")
            decision = assess_grade(tuple(item["code"] for item in results), [
                SkillResult(item["code"], item["correct"], item["total"]) for item in present
            ])
            if not decision.passed:
                raise ValueError(f"Баллы не подтверждают грейд у {candidate['id']}")
        for item in present + candidate["additional_test_results"]:
            if item["correct"] is None or item["percentage"] != 100 * item["correct"] / item["total"]:
                raise ValueError(f"Баллы и число ответов расходятся у {candidate['id']} / {item['code']}")
    return data


async def import_showcase(db: AsyncSession, directory: Path) -> dict[str, int]:
    data = load_dataset(directory)  # Validate everything before touching the database.
    now = datetime.now(timezone.utc)
    unavailable_password = hash_password(secrets.token_urlsafe(48))
    created = {"candidates": 0, "companies": 0, "vacancies": 0, "tasks": 0}

    async def add_user(email: str, role: UserRole, code: str) -> User | None:
        uid = showcase_id("user", code)
        existing = await db.get(User, uid)
        if existing:
            return None
        if await db.scalar(select(User.id).where(User.email == email)):
            raise ValueError(f"Email {email} уже принадлежит другому пользователю")
        user = User(id=uid, email=email, hashed_password=unavailable_password,
                    role=role, is_active=False, is_verified=True)
        db.add(user)
        await db.flush()
        return user

    for item in data["companies"]:
        code = item["id"]
        user = await add_user(f"showcase-{code}@example.test", UserRole.EMPLOYER, f"company:{code}")
        if user is None:
            continue
        db.add(EmployerProfile(
            id=showcase_id("company", code), user_id=user.id,
            company_name=f"Демо · {item['company_name']}", industry=item["industry"],
            city=item["city"], contact_person="Демонстрационная компания",
            description="Вымышленная компания для демонстрации возможностей платформы.",
        ))
        created["companies"] += 1

    for item in data["candidates"]:
        code = item["id"]
        user = await add_user(item["email"], UserRole.CANDIDATE, f"candidate:{code}")
        if user is None:
            continue
        profile_id = showcase_id("candidate", code)
        has_grade = bool(item["verified_grade"])
        profile = CandidateProfile(
            id=profile_id, user_id=user.id,
            first_name=f"{item['first_name']} (демо)", last_name=item["last_name"],
            city=item["city"], bio=item["bio"], hobbies=item["hobbies"],
            specialization=item["specialization"], programming_language=item["programming_language"],
            declared_grade=item["declared_grade"], verified_grade=item["verified_grade"],
            verified_specialization=item["specialization"] if has_grade else None,
            verified_grade_updated_at=now if has_grade else None,
            work_format=item["work_format"], salary_expectation=item["salary_expectation"],
            salary_tax_type=item["salary_tax_type"], skills=item["skills"],
            fsp_id=item["fsp_id"], fsp_verified=bool(item["fsp_verified"]),
            agreed_152_fz=True, agreed_152_fz_at=now,
            agreed_publication=True, agreed_publication_at=now,
            visibility_public=item["visibility_public"],
            mentor_available=item["mentor_available"],
            onboarding_completed=item["onboarding_completed"],
            # No fake phone, Telegram, GitHub or dead resume links are published.
        )
        db.add(profile)
        await db.flush()
        achievement = item["fsp_achievement"]
        if achievement:
            db.add(FSPAchievement(
                candidate_profile_id=profile_id, fsp_id=item["fsp_id"],
                tournament_name=achievement["tournament_name"], year=achievement["year"],
                rank_or_place=achievement["rank_or_place"],
                sport_category=achievement["sport_category"],
                score_or_rating=achievement["score_or_rating"],
                verified=True, is_demo=True,
            ))
        results = [result for result in item["required_test_results"] if result["percentage"] is not None]
        assessment_id = None
        if results:
            earned = sum(result["correct"] for result in results)
            maximum = sum(result["total"] for result in results)
            passed = bool(item["verified_grade"])
            assessment_id = showcase_id("assessment", code)
            db.add(GradeAssessment(
                id=assessment_id, user_id=user.id, candidate_profile_id=profile_id,
                specialization=item["specialization"], programming_language=item["programming_language"],
                target_grade=item["declared_grade"],
                required_skills=[result["code"] for result in item["required_test_results"]],
                question_codes={}, question_snapshots={}, retake_question_snapshots={},
                scoring_policy={"overall": 0.75, "skill": 0.5},
                status="completed", score=earned, max_score=maximum,
                percentage=round(100 * earned / maximum, 1), passed=passed, completed_at=now,
            ))
        for result in results + item["additional_test_results"]:
            additional = result["kind"] == "additional"
            db.add(TestSession(
                id=showcase_id("test", f"{code}:{result['kind']}:{result['code']}"),
                user_id=user.id, candidate_profile_id=profile_id,
                specialization=item["specialization"],
                target_grade="all" if additional else item["declared_grade"],
                assessment_id=None if additional else assessment_id,
                skill_code=result["code"], status="completed",
                score=result["correct"], max_score=result["total"],
                percentage=result["percentage"],
                passed=result["percentage"] >= (75 if additional else 50),
                feedback="Демонстрационный результат, созданный для показа интерфейса.",
                completed_at=now,
            ))
        created["candidates"] += 1

    for item in data["vacancies"]:
        vid = showcase_id("vacancy", item["id"])
        if await db.get(Vacancy, vid):
            continue
        db.add(Vacancy(
            id=vid, employer_id=showcase_id("company", item["company_id"]),
            title=f"Демо · {item['title']}", specialization=item["specialization"],
            required_grade=item["required_grade"], required_skills=item["required_skills"],
            salary_min=item["salary_min"], salary_max=item["salary_max"],
            salary_tax_type=item["salary_tax_type"], currency=item["currency"],
            work_format=item["work_format"], city=item["city"],
            description=f"Демонстрационная вакансия вымышленной компании. {item['description']}",
            is_published=item["is_published"],
        ))
        created["vacancies"] += 1

    for item in data["tasks"]:
        tid = showcase_id("task", item["id"])
        if await db.get(EmployerTask, tid):
            continue
        db.add(EmployerTask(
            id=tid, employer_id=showcase_id("company", item["company_id"]),
            vacancy_id=showcase_id("vacancy", item["vacancy_id"]),
            title=f"Демо · {item['title']}",
            description=f"Демонстрационное задание вымышленной компании. {item['description']}",
            task_type="manual_review", reference_answer=item["reference_answer"],
            evaluation_criteria=item["evaluation_criteria"],
            specialization=item["specialization"], min_grade=item["min_grade"],
            max_grade=item["max_grade"], max_score=item["max_score"],
            is_active=item["is_active"],
        ))
        created["tasks"] += 1
    await db.commit()
    return created
