import pytest
from httpx import AsyncClient


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


@pytest.mark.asyncio
async def test_search_declared_grade_does_not_open_profile_b16(client: AsyncClient):
    """
    Task B-16:
    Заявленный грейд не открывает профиль работодателю.
    Поиск по банку кандидатов с фильтром грейда (например, ?grade=senior)
    выдаёт ТОЛЬКО кандидатов с подтверждённым грейдом (verified_grade),
    а кандидат, у которого грейд только заявлен (declared_grade=senior, verified_grade=None),
    в выдачу по этому грейду не попадает.
    """
    emp_headers = await register_user(client, "emp_b16_grade@fsp.ru", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={"company_name": "ООО СберТех", "contact_person": "HR Анна"},
    )

    # 1. Регистрация кандидата с заявленным грейдом senior, без прохождения теста
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
    assert cand_id not in sr_ids, "Кандидат с неподтверждённым грейдом не должен находиться по фильтру grade=senior"

    # 3. В общей выдаче без указания грейда кандидат виден, но с verified_grade=None
    search_all = await client.get(
        "/api/v1/matching/search?specialization=Backend",
        headers=emp_headers,
    )
    assert search_all.status_code == 200
    all_items = {item["candidate_id"]: item for item in search_all.json()}
    assert cand_id in all_items
    assert all_items[cand_id]["verified_grade"] is None
    assert all_items[cand_id]["declared_grade"] == "senior"
    assert all_items[cand_id]["match_explanation"]["grade_match"] is False

    # 4. Проходим тест на грейд senior успешно (набираем 100%)
    start_test = await client.post(
        "/api/v1/testing/start",
        headers=cand_headers,
        json={"specialization": "Backend", "target_grade": "senior"},
    )
    assert start_test.status_code == 201
    sess_id = start_test.json()["session_id"]
    questions = start_test.json()["questions"]

    # Отправляем правильные ответы для подтверждения грейда
    # Получаем правильные ответы из снимка/вариантов вопроса
    correct_answers = []
    for q in questions:
        # Для закрытых вопросов выбираем первый вариант (в сессии сохраняется правильный ключ)
        # Получаем данные сессии через прохождение
        correct_answers.append({"question_id": q["id"], "selected_answers": [q["options"][0]["id"]]})

    # Чтобы гарантированно подтвердить грейд senior:
    # Используем правильные ключи из question_variants
    from app.core.question_variants import prepared_variants
    answers_payload = []
    for q in questions:
        family = q["code"].split("-V")[0]
        # Находим вариант по code
        variants = prepared_variants(family)
        matching_var = next((v for v in variants if v["code"] == q["code"]), variants[0])
        answers_payload.append({
            "question_id": q["id"],
            "selected_answers": matching_var["correct_answers"],
        })

    submit_resp = await client.post(
        f"/api/v1/testing/{sess_id}/submit",
        headers=cand_headers,
        json={"answers": answers_payload},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["passed"] is True
    assert submit_resp.json()["verified_grade"] == "senior"

    # 5. Теперь, когда грейд подтверждён, поиск grade=senior ОБЯЗАН найти кандидата!
    search_sr_after = await client.get(
        "/api/v1/matching/search?specialization=Backend&grade=senior",
        headers=emp_headers,
    )
    assert search_sr_after.status_code == 200
    sr_ids_after = [item["candidate_id"] for item in search_sr_after.json()]
    assert cand_id in sr_ids_after
    found_item = next(item for item in search_sr_after.json() if item["candidate_id"] == cand_id)
    assert found_item["verified_grade"] == "senior"
    assert found_item["match_explanation"]["grade_match"] is True


@pytest.mark.asyncio
async def test_search_stack_filtering_b16(client: AsyncClient):
    """
    Task B-16:
    Поиск по банку кандидатов с фильтрацией по стеку технологий (stack).
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

    # 4. Поиск по несуществующему стеку
    res_none = await client.get("/api/v1/matching/search?stack=Rust,Blockchain", headers=emp_headers)
    assert res_none.status_code == 200
    ids_none = [item["candidate_id"] for item in res_none.json()]
    assert c1_id not in ids_none
    assert c2_id not in ids_none


@pytest.mark.asyncio
async def test_search_verified_only_and_ordering_b16(client: AsyncClient):
    """
    Task B-16:
    - verified_only=True возвращает только кандидатов с подтверждённым грейдом.
    - В общем поиске подтверждённые кандидаты всегда идут первыми.
    """
    emp_headers = await register_user(client, "emp_b16_verified_only@fsp.ru", "employer")
    await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={"company_name": "ООО ВК", "contact_person": "HR Ольга"},
    )

    # Неподтверждённый кандидат
    unver_headers = await register_user(client, "cand_unver_order@fsp.ru", "candidate")
    unver_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=unver_headers,
        json={
            "first_name": "Дмитрий",
            "last_name": "Несдавший",
            "city": "Казань",
            "specialization": "Backend",
            "declared_grade": "junior",
            "skills": ["Python"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert unver_resp.status_code == 200
    unver_id = unver_resp.json()["id"]

    # Подтверждённый кандидат
    ver_headers = await register_user(client, "cand_ver_order@fsp.ru", "candidate")
    ver_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=ver_headers,
        json={
            "first_name": "Елена",
            "last_name": "Сдавшая",
            "city": "Новосибирск",
            "specialization": "Backend",
            "declared_grade": "junior",
            "skills": ["Python", "FastAPI"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert ver_resp.status_code == 200
    ver_id = ver_resp.json()["id"]

    # Сдаём Junior тест для Елены
    from app.core.question_variants import prepared_variants
    t_start = await client.post(
        "/api/v1/testing/start",
        headers=ver_headers,
        json={"specialization": "Backend", "target_grade": "junior"},
    )
    assert t_start.status_code == 201
    sess = t_start.json()
    ans = []
    for q in sess["questions"]:
        family = q["code"].split("-V")[0]
        variants = prepared_variants(family)
        matching_var = next((v for v in variants if v["code"] == q["code"]), variants[0])
        ans.append({"question_id": q["id"], "selected_answers": matching_var["correct_answers"]})
    sub = await client.post(f"/api/v1/testing/{sess['session_id']}/submit", headers=ver_headers, json={"answers": ans})
    assert sub.status_code == 200
    assert sub.json()["verified_grade"] == "junior"

    # 1. Поиск с verified_only=True
    resp_ver_only = await client.get("/api/v1/matching/search?verified_only=true", headers=emp_headers)
    assert resp_ver_only.status_code == 200
    ids_ver_only = [item["candidate_id"] for item in resp_ver_only.json()]
    assert ver_id in ids_ver_only
    assert unver_id not in ids_ver_only

    # 2. В общем поиске подтверждённая Елена идёт раньше неподтверждённого Дмитрия
    resp_all = await client.get("/api/v1/matching/search?specialization=Backend", headers=emp_headers)
    assert resp_all.status_code == 200
    items = resp_all.json()
    pos_ver = next(i for i, item in enumerate(items) if item["candidate_id"] == ver_id)
    pos_unver = next(i for i, item in enumerate(items) if item["candidate_id"] == unver_id)
    assert pos_ver < pos_unver, "Подтверждённые кандидаты должны располагаться выше неподтверждённых"
