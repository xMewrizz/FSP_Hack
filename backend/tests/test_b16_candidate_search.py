import uuid
import pytest
from httpx import AsyncClient
from datetime import datetime
import app.models  # noqa: F401
from app.models.candidate import CandidateProfile
from conftest import TestingSessionLocal


async def register_user(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    created = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPassword123!", "role": role},
    )
    assert created.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": created.json()["verification_code"]},
    )
    assert verified.status_code == 200
    return {"Authorization": f"Bearer {verified.json()['access_token']}"}


async def set_verified_grade(candidate_id: str, verified_grade: str | None, fsp_verified: bool = False):
    async with TestingSessionLocal() as session:
        cand = await session.get(CandidateProfile, uuid.UUID(candidate_id))
        assert cand is not None
        cand.verified_grade = verified_grade
        cand.fsp_verified = fsp_verified
        await session.commit()


@pytest.mark.asyncio
async def test_search_declared_grade_does_not_open_profile_b16(client: AsyncClient):
    """
    Task B-16:
    Заявленный грейд не открывает профиль работодателю.
    1. Кандидат с неподтверждённым грейдом (verified_grade is None) вообще не попадает
       в поисковую выдачу банка кандидатов работодателю.
    2. Поиск по банку кандидатов с фильтром грейда (например, ?grade=senior)
       выдаёт ТОЛЬКО кандидатов с подтверждённым грейдом senior.
    3. Кандидат, у которого грейд заявлен как senior, но подтверждён как middle,
       не открывается работодателю при поиске по грейду senior.
    """
    emp_headers = await register_user(client, "emp_b16_grade@fsp.ru", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={"company_name": "ООО СберТех", "contact_person": "HR Анна"},
    )

    # 1. Регистрация кандидата с заявленным грейдом senior, без подтверждения грейда
    cand_headers = await register_user(client, "cand_unverified_sr@fsp.ru", "candidate")
    cand_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Пётр",
            "last_name": "Заявленный",
            "specialization": "Backend",
            "declared_grade": "senior",
            "work_format": "remote",
            "city": "Москва",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )
    assert cand_resp.status_code == 200
    cand_id = cand_resp.json()["id"]

    # Открываем видимость профиля (152-ФЗ)
    pub_resp = await client.put(
        "/api/v1/candidates/profile",
        headers=cand_headers,
        json={"agreed_publication": True, "visibility_public": True},
    )
    assert pub_resp.status_code == 200
    assert pub_resp.json()["verified_grade"] is None
    assert pub_resp.json()["declared_grade"] == "senior"

    # 2. Работодатель ищет с фильтром grade=senior
    # Заявленный грейд НЕ должен открыть профиль работодателю!
    search_sr = await client.get(
        "/api/v1/matching/search?specialization=Backend&grade=senior",
        headers=emp_headers,
    )
    assert search_sr.status_code == 200
    sr_ids = [item["candidate_id"] for item in search_sr.json()]
    assert cand_id not in sr_ids, "Кандидат без подтверждённого грейда не должен открываться работодателю"

    # 3. Общий поиск по банку кандидатов — выдача ограничена подтверждёнными профилями
    search_all = await client.get(
        "/api/v1/matching/search?specialization=Backend",
        headers=emp_headers,
    )
    assert search_all.status_code == 200
    all_ids = [item["candidate_id"] for item in search_all.json()]
    assert cand_id not in all_ids, "Неподтверждённый профиль не должен открываться работодателю в банке кандидатов"

    # 4. Кандидат Сергей: заявлен senior, но подтверждён middle
    sergey_headers = await register_user(client, "cand_sergey_b16@fsp.ru", "candidate")
    sergey_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=sergey_headers,
        json={
            "first_name": "Сергей",
            "last_name": "Мидл",
            "specialization": "Backend",
            "declared_grade": "senior",
            "work_format": "remote",
            "city": "Москва",
            "skills": ["Python", "Django"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert sergey_resp.status_code == 200
    sergey_id = sergey_resp.json()["id"]
    await set_verified_grade(sergey_id, "middle")

    # Поиск grade=senior не должен открывать Сергея, несмотря на declared_grade=senior!
    search_sr2 = await client.get(
        "/api/v1/matching/search?specialization=Backend&grade=senior",
        headers=emp_headers,
    )
    assert search_sr2.status_code == 200
    sr2_ids = [item["candidate_id"] for item in search_sr2.json()]
    assert sergey_id not in sr2_ids, "Заявленный senior не должен открывать профиль при фильтре grade=senior"

    # Поиск grade=middle ДОЛЖЕН открыть Сергея, так как verified_grade=middle
    search_mid = await client.get(
        "/api/v1/matching/search?specialization=Backend&grade=middle",
        headers=emp_headers,
    )
    assert search_mid.status_code == 200
    mid_ids = [item["candidate_id"] for item in search_mid.json()]
    assert sergey_id in mid_ids
    found_item = next(item for item in search_mid.json() if item["candidate_id"] == sergey_id)
    assert found_item["verified_grade"] == "middle"
    assert found_item["declared_grade"] == "senior"


@pytest.mark.asyncio
async def test_search_stack_filtering_b16(client: AsyncClient):
    """
    Task B-16:
    Поиск по банку кандидатов с фильтрацией по стеку технологий (stack/skill).
    """
    emp_headers = await register_user(client, "emp_b16_stack@fsp.ru", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={"company_name": "ООО Т-Технологии", "contact_person": "HR Мария"},
    )

    # Кандидат 1: Python, FastAPI, PostgreSQL
    c1_headers = await register_user(client, "cand_python_b16@fsp.ru", "candidate")
    c1 = await client.post(
        "/api/v1/candidates/onboarding",
        headers=c1_headers,
        json={
            "first_name": "Алексей",
            "last_name": "Питонист",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert c1.status_code == 200
    c1_id = c1.json()["id"]
    await set_verified_grade(c1_id, "middle")

    # Кандидат 2: Golang, gRPC, Docker, Kubernetes
    c2_headers = await register_user(client, "cand_go_b16@fsp.ru", "candidate")
    c2 = await client.post(
        "/api/v1/candidates/onboarding",
        headers=c2_headers,
        json={
            "first_name": "Сергей",
            "last_name": "Гофер",
            "city": "Санкт-Петербург",
            "specialization": "Backend",
            "declared_grade": "middle",
            "skills": ["Go", "gRPC", "Docker", "Kubernetes"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert c2.status_code == 200
    c2_id = c2.json()["id"]
    await set_verified_grade(c2_id, "middle")

    # 1. Поиск по стеку "PostgreSQL"
    res_pg = await client.get("/api/v1/matching/search?stack=PostgreSQL", headers=emp_headers)
    assert res_pg.status_code == 200
    ids_pg = [item["candidate_id"] for item in res_pg.json()]
    assert c1_id in ids_pg
    assert c2_id not in ids_pg

    # 2. Поиск по стеку "Docker"
    res_docker = await client.get("/api/v1/matching/search?stack=Docker", headers=emp_headers)
    assert res_docker.status_code == 200
    ids_docker = [item["candidate_id"] for item in res_docker.json()]
    assert c2_id in ids_docker
    assert c1_id not in ids_docker

    # 3. Поиск по нескольким технологиям "Python, FastAPI"
    res_multi = await client.get("/api/v1/matching/search?stack=Python,FastAPI", headers=emp_headers)
    assert res_multi.status_code == 200
    ids_multi = [item["candidate_id"] for item in res_multi.json()]
    assert c1_id in ids_multi
    assert c2_id not in ids_multi

    # 4. Поиск через параметр skill
    res_skill = await client.get("/api/v1/matching/search?skill=Kubernetes", headers=emp_headers)
    assert res_skill.status_code == 200
    ids_skill = [item["candidate_id"] for item in res_skill.json()]
    assert c2_id in ids_skill
    assert c1_id not in ids_skill

    # 5. Поиск по несуществующему стеку
    res_none = await client.get("/api/v1/matching/search?stack=Rust,Blockchain", headers=emp_headers)
    assert res_none.status_code == 200
    ids_none = [item["candidate_id"] for item in res_none.json()]
    assert c1_id not in ids_none
    assert c2_id not in ids_none


@pytest.mark.asyncio
async def test_search_fsp_only_and_parameters_b16(client: AsyncClient):
    """
    Task B-16:
    - Фильтр достижений ФСП (fsp_only=True)
    - Фильтры по городу, формату работы и специализации
    """
    emp_headers = await register_user(client, "emp_b16_fsp@fsp.ru", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={"company_name": "ООО ВК", "contact_person": "HR Ольга"},
    )

    # Кандидат с ФСП верификацией
    fsp_headers = await register_user(client, "cand_fsp_b16@fsp.ru", "candidate")
    fsp_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=fsp_headers,
        json={
            "first_name": "Елена",
            "last_name": "ФСП",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "work_format": "remote",
            "skills": ["Python", "FastAPI"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert fsp_resp.status_code == 200
    fsp_id = fsp_resp.json()["id"]
    await set_verified_grade(fsp_id, "middle", fsp_verified=True)

    # Обычный кандидат без ФСП
    norm_headers = await register_user(client, "cand_norm_b16@fsp.ru", "candidate")
    norm_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=norm_headers,
        json={
            "first_name": "Иван",
            "last_name": "Обычный",
            "city": "Санкт-Петербург",
            "specialization": "Backend",
            "declared_grade": "middle",
            "work_format": "office",
            "skills": ["Python", "Django"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert norm_resp.status_code == 200
    norm_id = norm_resp.json()["id"]
    await set_verified_grade(norm_id, "middle", fsp_verified=False)

    # 1. Поиск с fsp_only=True
    res_fsp = await client.get("/api/v1/matching/search?fsp_only=true", headers=emp_headers)
    assert res_fsp.status_code == 200
    ids_fsp = [item["candidate_id"] for item in res_fsp.json()]
    assert fsp_id in ids_fsp
    assert norm_id not in ids_fsp

    # 2. Поиск по городу Москва
    res_city = await client.get("/api/v1/matching/search?city=Москва", headers=emp_headers)
    assert res_city.status_code == 200
    ids_city = [item["candidate_id"] for item in res_city.json()]
    assert fsp_id in ids_city
    assert norm_id not in ids_city

    # 3. Поиск по формату работы office
    res_fmt = await client.get("/api/v1/matching/search?work_format=office", headers=emp_headers)
    assert res_fmt.status_code == 200
    ids_fmt = [item["candidate_id"] for item in res_fmt.json()]
    assert norm_id in ids_fmt
    assert fsp_id not in ids_fmt


@pytest.mark.asyncio
async def test_search_education_age_and_course_filters(client: AsyncClient):
    employer = await register_user(client, "employer_education@example.com", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=employer,
        json={"company_name": "Тест", "contact_person": "HR"},
    )
    current_year = datetime.now().year
    candidate_ids: list[str] = []
    for email, first_name, course, birth_year in (
        ("junior_student@example.com", "Младший", 2, current_year - 20),
        ("senior_student@example.com", "Старший", 4, current_year - 24),
    ):
        headers = await register_user(client, email, "candidate")
        created = await client.post(
            "/api/v1/candidates/onboarding",
            headers=headers,
            json={
                "first_name": first_name,
                "last_name": "Кандидат",
                "specialization": "Backend",
                "declared_grade": "middle",
                "city": "Москва",
                "agreed_152_fz": True,
                "agreed_publication": True,
                "visibility_public": True,
            },
        )
        assert created.status_code == 200, created.text
        candidate_id = created.json()["id"]
        candidate_ids.append(candidate_id)
        updated = await client.put(
            "/api/v1/candidates/profile",
            headers=headers,
            json={
                "education_level": "incomplete_higher",
                "university_course": course,
                "birth_year": birth_year,
                "hobbies": f"Хобби {first_name}",
            },
        )
        assert updated.status_code == 200, updated.text
        await set_verified_grade(candidate_id, "middle")

    senior_search = await client.get(
        "/api/v1/matching/search?education_level=incomplete_higher&university_course_group=senior&age_min=22&age_max=26",
        headers=employer,
    )
    assert senior_search.status_code == 200, senior_search.text
    results = senior_search.json()
    assert [item["candidate_id"] for item in results] == [candidate_ids[1]]
    assert results[0]["hobbies"] == "Хобби Старший"
