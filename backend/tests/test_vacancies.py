import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vacancy_and_application_lifecycle_b30(client: AsyncClient):
    # 1. Регистрация и верификация работодателя 1
    emp1_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "boss1@company.com", "password": "Password123!", "role": "employer"},
    )
    assert emp1_reg.status_code == 201
    code1 = emp1_reg.json()["verification_code"]

    emp1_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "boss1@company.com", "code": code1},
    )
    emp1_token = emp1_ver.json()["access_token"]
    emp1_headers = {"Authorization": f"Bearer {emp1_token}"}

    # Онбординг работодателя 1
    onb1 = await client.post(
        "/api/v1/employer/onboarding",
        headers=emp1_headers,
        json={
            "company_name": "ООО СберТех Инновации",
            "contact_person": "Иван Смирнов",
            "description": "Разработка финтех продуктов",
            "industry": "IT",
            "website": "https://sbertech.ru",
            "city": "Москва",
        },
    )
    assert onb1.status_code == 200

    # 2. Регистрация и верификация кандидата
    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sultan.dev@fsp.ru", "password": "Password123!", "role": "candidate"},
    )
    assert cand_reg.status_code == 201
    cand_code = cand_reg.json()["verification_code"]

    cand_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "sultan.dev@fsp.ru", "code": cand_code},
    )
    cand_token = cand_ver.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # Онбординг кандидата (152-ФЗ, контакты)
    cand_onb = await client.post(
        "/api/v1/candidate/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Султан",
            "last_name": "Разработчик",
            "phone": "+7 999 111-22-33",
            "telegram": "@sultan_dev",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "senior",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AsyncIO"],
            "salary_expectation": 300000.0,
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )
    assert cand_onb.status_code == 200

    # 3. Проверка валидации зарплаты: min > max должна давать 422
    invalid_salary_resp = await client.post(
        "/api/v1/vacancies",
        headers=emp1_headers,
        json={
            "title": "Invalid Salary Developer",
            "specialization": "Backend",
            "required_grade": "Senior",
            "salary_min": 350000.0,
            "salary_max": 200000.0,  # Ошибка!
            "salary_tax_type": "gross",
            "work_format": "remote",
        },
    )
    assert invalid_salary_resp.status_code == 422

    draft_resp = await client.post(
        "/api/v1/vacancies",
        headers=emp1_headers,
        json={
            "title": "Backend Developer — черновик",
            "specialization": "Backend",
            "required_grade": "middle",
            "salary_min": 200000,
            "salary_max": 260000,
            "salary_tax_type": "net",
            "is_published": False,
        },
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.json()["id"]
    assert draft_resp.json()["is_published"] is False
    assert draft_resp.json()["salary_tax_type"] == "net"
    assert all(item["id"] != draft_id for item in (await client.get("/api/v1/vacancies")).json())
    assert (await client.get(f"/api/v1/vacancies/{draft_id}")).status_code == 404
    assert (await client.post(
        f"/api/v1/vacancies/{draft_id}/apply",
        headers=cand_headers,
        json={"cover_letter": ""},
    )).status_code == 400
    publish_resp = await client.patch(
        f"/api/v1/vacancies/{draft_id}",
        headers=emp1_headers,
        json={"is_published": True},
    )
    assert publish_resp.status_code == 200
    assert publish_resp.json()["is_published"] is True

    # 4. Работодатель 1 успешно публикует вакансию с пометкой «до вычета НДФЛ» (gross)
    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=emp1_headers,
        json={
            "title": "Senior Python Backend Developer",
            "specialization": "Backend",
            "required_grade": "Senior",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "salary_min": 250000.0,
            "salary_max": 350000.0,
            "salary_tax_type": "gross",
            "currency": "RUB",
            "work_format": "remote",
            "city": "Москва",
            "description": "Ищем сильного бэкендера в команду платформы",
        },
    )
    assert create_resp.status_code == 201
    vacancy_data = create_resp.json()
    vacancy_id = vacancy_data["id"]
    assert vacancy_data["title"] == "Senior Python Backend Developer"
    assert vacancy_data["salary_tax_type"] == "gross"
    assert vacancy_data["company"]["company_name"] == "ООО СберТех Инновации"

    # 5. Кандидат ищет вакансии по фильтрам
    search_resp = await client.get(
        "/api/v1/vacancies",
        params={
            "specialization": "Backend",
            "salary_tax_type": "gross",
            "min_salary": 200000.0,
        },
    )
    assert search_resp.status_code == 200
    vacancies = search_resp.json()
    assert len(vacancies) >= 1
    assert any(v["id"] == vacancy_id for v in vacancies)

    # 6. Кандидат откликается на вакансию (B-30)
    apply_resp = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/apply",
        headers=cand_headers,
        json={"cover_letter": "Добрый день! Имею опыт в FastAPI и высоконагруженных сервисах."},
    )
    assert apply_resp.status_code == 201
    application = apply_resp.json()
    application_id = application["id"]
    assert application["status"] == "pending"
    assert application["vacancy_title"] == "Senior Python Backend Developer"

    # Повторный отклик должен вернуть 400
    dup_apply = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/apply",
        headers=cand_headers,
        json={"cover_letter": "Второй раз"},
    )
    assert dup_apply.status_code == 400

    # 7. Кандидат видит свои отклики
    my_apps = await client.get("/api/v1/vacancies/applications/my", headers=cand_headers)
    assert my_apps.status_code == 200
    my_apps_data = my_apps.json()
    assert len(my_apps_data) == 1
    assert my_apps_data[0]["id"] == application_id
    assert my_apps_data[0]["status"] == "pending"

    # 8. Регистрация другого работодателя 2 (проверка 152-ФЗ изоляции)
    emp2_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "boss2@other.com", "password": "Password123!", "role": "employer"},
    )
    emp2_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "boss2@other.com", "code": emp2_reg.json()["verification_code"]},
    )
    emp2_headers = {"Authorization": f"Bearer {emp2_ver.json()['access_token']}"}
    onb2 = await client.post(
        "/api/v1/employer/onboarding",
        headers=emp2_headers,
        json={"company_name": "ООО Другая Компания", "contact_person": "Алексей Петров", "city": "СПб"},
    )
    assert onb2.status_code == 200

    # Отклик создаёт приватный диалог между кандидатом и работодателем.
    employer_threads = await client.get(
        "/api/v1/vacancies/applications/conversations", headers=emp1_headers
    )
    assert employer_threads.status_code == 200
    assert employer_threads.json()[0]["id"] == application_id
    assert employer_threads.json()[0]["candidate_name"] == "Султан Разработчик"
    candidate_threads = await client.get(
        "/api/v1/vacancies/applications/conversations", headers=cand_headers
    )
    assert candidate_threads.status_code == 200
    assert candidate_threads.json()[0]["id"] == application_id
    assert (await client.get(
        "/api/v1/vacancies/applications/conversations", headers=emp2_headers
    )).json() == []

    message_url = f"/api/v1/vacancies/applications/{application_id}/messages"
    assert (await client.get(message_url, headers=emp2_headers)).status_code == 404
    assert (await client.post(message_url, headers=emp2_headers, json={"body": "Чужой чат"})).status_code == 404
    sent = await client.post(message_url, headers=emp1_headers, json={"body": "  Здравствуйте!  "})
    assert sent.status_code == 201
    assert sent.json()["body"] == "Здравствуйте!"
    assert (await client.post(message_url, headers=cand_headers, json={"body": "  "})).status_code == 422
    reply = await client.post(message_url, headers=cand_headers, json={"body": "Добрый день!"})
    assert reply.status_code == 201
    employer_messages = (await client.get(message_url, headers=emp1_headers)).json()["messages"]
    candidate_messages = (await client.get(message_url, headers=cand_headers)).json()["messages"]
    assert [item["body"] for item in employer_messages] == ["Здравствуйте!", "Добрый день!"]
    assert [item["is_mine"] for item in employer_messages] == [True, False]
    assert [item["is_mine"] for item in candidate_messages] == [False, True]
    assert (await client.get(
        "/api/v1/vacancies/applications/conversations", headers=emp1_headers
    )).json()[0]["last_message"] == "Добрый день!"

    # Другой работодатель НЕ МОЖЕТ смотреть отклики чужой вакансии (152-ФЗ)
    forbidden_resp = await client.get(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        headers=emp2_headers,
    )
    assert forbidden_resp.status_code == 403

    # 9. Законный работодатель 1 видит отклики с РАСКРЫТЫМИ контактами кандидата
    emp_apps_resp = await client.get(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        headers=emp1_headers,
    )
    assert emp_apps_resp.status_code == 200
    emp_apps = emp_apps_resp.json()
    assert len(emp_apps) == 1
    cand_info = emp_apps[0]["candidate"]
    # 152-ФЗ: контактные данные раскрыты работодателю после добровольного отклика!
    assert cand_info["email"] == "sultan.dev@fsp.ru"
    assert cand_info["phone"] == "+7 999 111-22-33"
    assert cand_info["telegram"] == "@sultan_dev"
    assert cand_info["first_name"] == "Султан"

    # 10. Работодатель одобряет отклик (статус accepted)
    status_update_resp = await client.patch(
        f"/api/v1/vacancies/applications/{application_id}/status",
        headers=emp1_headers,
        json={"status": "accepted"},
    )
    assert status_update_resp.status_code == 200
    assert status_update_resp.json()["new_status"] == "accepted"

    # 11. Кандидат проверяет свои отклики и видит статус accepted
    my_apps_updated = await client.get("/api/v1/vacancies/applications/my", headers=cand_headers)
    assert my_apps_updated.json()[0]["status"] == "accepted"

    close_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=emp1_headers,
        json={"is_published": False},
    )
    assert close_resp.status_code == 200
    assert all(item["id"] != vacancy_id for item in (await client.get("/api/v1/vacancies")).json())
    closed_application = await client.get("/api/v1/vacancies/applications/my", headers=cand_headers)
    assert closed_application.json()[0]["id"] == application_id
    assert closed_application.json()[0]["status"] == "accepted"
