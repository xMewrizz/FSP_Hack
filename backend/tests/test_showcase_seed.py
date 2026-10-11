import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.employer_task import EmployerTask
from app.models.need import EmployerNeed
from app.models.test import GradeAssessment, TestSession as SessionModel
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.showcase_seed import import_showcase, load_dataset
from app.services.matching_service import MatchingService
from app.services.showcase_seed import showcase_id
from app.services.invitation_service import InvitationService
from app.services.vacancy_service import VacancyService
from app.services.employer_task_service import EmployerTaskService
from app.schemas.invitation import InvitationCreate
from app.schemas.vacancy import ApplicationCreate
from app.schemas.employer_task import EmployerTaskSubmissionCreate
from conftest import TestingSessionLocal


DATA = Path(__file__).resolve().parents[2] / "data" / "platform_showcase_v1"


@pytest.mark.asyncio
async def test_showcase_import_is_real_and_repeatable():
    async with TestingSessionLocal() as db:
        assert await import_showcase(db, DATA) == {
            "candidates": 60, "companies": 8, "vacancies": 15, "tasks": 6,
        }
        assert await import_showcase(db, DATA) == {
            "candidates": 0, "companies": 0, "vacancies": 0, "tasks": 0,
        }
        for model, expected in ((CandidateProfile, 60), (EmployerProfile, 8),
                                (Vacancy, 15), (EmployerTask, 6)):
            assert await db.scalar(select(func.count()).select_from(model)) == expected
        assert await db.scalar(select(func.count()).select_from(GradeAssessment).where(
            GradeAssessment.passed.is_(True))) == 48
        assert await db.scalar(select(func.count()).select_from(SessionModel).where(
            SessionModel.assessment_id.is_not(None))) > 0
        assert await db.scalar(select(func.count()).select_from(User).where(
            User.is_active.is_(True))) == 0
        profiles = (await db.scalars(select(CandidateProfile))).all()
        assert all(profile.phone is None and profile.telegram is None and profile.resume_url is None
                   for profile in profiles)
        need = EmployerNeed(
            employer_id=showcase_id("company", "northline"),
            title="Проверка импорта", specialization="Backend", required_grade="junior",
            required_skills=[{"name": "Python для Backend", "weight": 5}],
            salary_min=80000, salary_max=250000, salary_tax_type="gross",
            currency="RUB", work_format="remote", is_active=True,
        )
        db.add(need)
        await db.flush()
        matches = await MatchingService.match_candidates_for_need(db, need.id)
        assert matches.total == 8
        assert all("(демо)" in item.first_name for item in matches.candidates)
        assert all(item.test_percentage >= 75 for item in matches.candidates)
        company_user = await db.get(User, showcase_id("user", "company:northline"))
        candidate = await db.get(CandidateProfile, showcase_id("candidate", "cand-001"))
        with pytest.raises(HTTPException) as invitation_error:
            await InvitationService.create_invitation(db, company_user, InvitationCreate(
                candidate_id=candidate.id, offer_description="Приглашаем обсудить работу",
                contact_method="email", salary_min=100000, salary_max=200000,
            ))
        assert invitation_error.value.status_code == 409
        with pytest.raises(HTTPException) as application_error:
            await VacancyService.apply_to_vacancy(
                db, candidate.id, showcase_id("vacancy", "vac-001"), ApplicationCreate(),
            )
        assert application_error.value.status_code == 409
        with pytest.raises(HTTPException) as task_error:
            await EmployerTaskService.submit_task_solution(
                db, candidate, showcase_id("task", "task-01"),
                EmployerTaskSubmissionCreate(answer_text="Пример ответа"),
            )
        assert task_error.value.status_code == 409


def test_showcase_rejects_false_grade_before_import(tmp_path: Path):
    for name in ("manifest", "candidates", "companies", "vacancies", "tasks"):
        (tmp_path / f"{name}.json").write_bytes((DATA / f"{name}.json").read_bytes())
    candidates = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))
    candidates[0]["required_test_results"][0]["percentage"] = 40
    candidates[0]["required_test_results"][0]["correct"] = 4
    (tmp_path / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="Баллы не подтверждают грейд"):
        load_dataset(tmp_path)
