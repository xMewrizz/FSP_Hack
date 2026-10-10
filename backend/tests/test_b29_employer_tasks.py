import pytest
from httpx import AsyncClient


async def register_and_login(
    client: AsyncClient, email: str, role: str, company_name: str | None = None
) -> tuple[str, dict]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": role},
    )
    assert reg_resp.status_code == 201, reg_resp.text
    ver_code = reg_resp.json()["verification_code"]

    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": ver_code},
    )
    assert ver_resp.status_code == 200, ver_resp.text
    token = ver_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    if role == "employer":
        onboard_resp = await client.post(
            "/api/v1/employer/onboarding",
            headers=headers,
            json={
                "company_name": company_name or "Тестовая Компания",
                "description": "Описание компании",
                "industry": "IT",
                "website": "https://company.ru",
                "contact_person": "HR Менеджер",
                "city": "Москва",
            },
        )
        assert onboard_resp.status_code == 200, onboard_resp.text
    elif role == "candidate":
        onboard_resp = await client.post(
            "/api/v1/candidate/onboarding",
            headers=headers,
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "specialization": "Backend",
                "declared_grade": "junior",
                "programming_language": "Python",
                "work_format": "remote",
                "city": "Москва",
                "agreed_152_fz": True,
                "agreed_publication": True,
                "visibility_public": True,
            },
        )
        assert onboard_resp.status_code == 200, onboard_resp.text

    return token, headers


@pytest.mark.asyncio
async def test_employer_creates_auto_check_task(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp1@b29.ru", "employer", "Яндекс")

    resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "SQL: Количество активных пользователей",
            "description": "Напишите SQL-запрос для подсчёта активных юзеров",
            "task_type": "auto_check",
            "reference_answer": "SELECT COUNT(*) FROM users WHERE is_active = TRUE;",
            "max_score": 10.0,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "SQL: Количество активных пользователей"
    assert data["task_type"] == "auto_check"
    assert data["reference_answer"] == "SELECT COUNT(*) FROM users WHERE is_active = TRUE;"
    assert data["max_score"] == 10.0
    assert data["is_active"] is True
    assert data["company_name"] == "Яндекс"


@pytest.mark.asyncio
async def test_employer_creates_auto_check_requires_reference(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp2@b29.ru", "employer", "Сбер")

    resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "Тестовое задание без эталона",
            "description": "Попробуем создать без эталонного ответа",
            "task_type": "auto_check",
            "reference_answer": "",
        },
    )
    assert resp.status_code == 400
    assert "эталонный ответ" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_candidate_views_tasks_reference_is_hidden(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp3@b29.ru", "employer", "VK")
    _, cand_headers = await register_and_login(client, "cand1@b29.ru", "candidate")

    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "Алгоритм поиска",
            "description": "Какой алгоритм работает за O(log N)?",
            "task_type": "auto_check",
            "reference_answer": "Бинарный поиск",
            "max_score": 10.0,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    # Кандидат запрашивает список заданий
    list_resp = await client.get("/api/v1/candidate/tasks", headers=cand_headers)
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert len(tasks) >= 1
    found = next((t for t in tasks if t["id"] == task_id), None)
    assert found is not None
    assert "reference_answer" not in found  # Защита: эталон СТРОГО скрыт от кандидата!
    assert found["company_name"] == "VK"

    # Кандидат запрашивает конкретное задание
    detail_resp = await client.get(f"/api/v1/candidate/tasks/{task_id}", headers=cand_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert "reference_answer" not in detail_data


@pytest.mark.asyncio
async def test_candidate_submits_auto_check_correct_answer_updates_activity(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp4@b29.ru", "employer", "Тинькофф")
    _, cand_headers = await register_and_login(client, "cand2@b29.ru", "candidate")

    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "HTTP статус создания ресурса",
            "description": "Укажите код HTTP статуса успешного создания",
            "task_type": "auto_check",
            "reference_answer": "201",
            "max_score": 10.0,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    # Кандидат отправляет верный ответ
    sub_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=cand_headers,
        json={"answer_text": "201"},
    )
    assert sub_resp.status_code == 200, sub_resp.text
    sub_data = sub_resp.json()
    assert sub_data["status"] == "graded"
    assert sub_data["score"] == 10.0
    assert sub_data["passed"] is True
    assert "совпал" in sub_data["feedback"].lower()

    # Проверяем обновление профиля (last_active_at)
    prof_resp = await client.get("/api/v1/candidate/profile", headers=cand_headers)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["last_active_at"] is not None

    # Проверяем ленту активности кандидата (B-29)
    act_resp = await client.get("/api/v1/candidate/activity", headers=cand_headers)
    assert act_resp.status_code == 200
    activities = act_resp.json()
    assert len(activities) >= 1
    assert activities[0]["activity_type"] == "employer_task_completed"
    assert "Тинькофф" in activities[0]["title"]
    assert "успешно" in activities[0]["description"].lower()


@pytest.mark.asyncio
async def test_candidate_submits_auto_check_incorrect_answer(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp5@b29.ru", "employer", "Авито")
    _, cand_headers = await register_and_login(client, "cand3@b29.ru", "candidate")

    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "Сложность поиска в хэш-таблице",
            "description": "Какова средняя асимптотическая сложность?",
            "task_type": "auto_check",
            "reference_answer": "O(1)",
            "max_score": 10.0,
        },
    )
    task_id = create_resp.json()["id"]

    # Кандидат отправляет неверный ответ
    sub_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=cand_headers,
        json={"answer_text": "O(N^2)"},
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "graded"
    assert sub_data["score"] == 0.0
    assert sub_data["passed"] is False


@pytest.mark.asyncio
async def test_manual_review_flow_and_activity_update(client: AsyncClient):
    _, emp_headers = await register_and_login(client, "emp6@b29.ru", "employer", "Озон")
    _, cand_headers = await register_and_login(client, "cand4@b29.ru", "candidate")

    # 1. Работодатель создает открытое задание
    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={
            "title": "Проектирование шардирования БД",
            "description": "Опишите стратегию выбора ключа шардирования для чатов",
            "task_type": "manual_review",
            "max_score": 10.0,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    # 2. Кандидат отправляет решение
    sub_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=cand_headers,
        json={"answer_text": "Использовать chat_id как ключ шардирования и consistent hashing..."},
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    submission_id = sub_data["id"]
    assert sub_data["status"] == "pending_review"
    assert sub_data["score"] is None
    assert sub_data["passed"] is None

    # Повторная отправка пока ожидает проверки возвращает 400
    dup_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=cand_headers,
        json={"answer_text": "Еще один ответ"},
    )
    assert dup_resp.status_code == 400

    # 3. Работодатель видит решение в списке ответов
    subs_list = await client.get(
        f"/api/v1/employer/tasks/{task_id}/submissions",
        headers=emp_headers,
    )
    assert subs_list.status_code == 200
    assert len(subs_list.json()) == 1
    assert subs_list.json()[0]["id"] == submission_id

    # 4. Работодатель проверяет и выставляет оценку
    review_resp = await client.post(
        f"/api/v1/employer/tasks/submissions/{submission_id}/review",
        headers=emp_headers,
        json={
            "score": 9.5,
            "passed": True,
            "feedback": "Отличная аргументация выбора consistent hashing!",
        },
    )
    assert review_resp.status_code == 200
    graded_data = review_resp.json()
    assert graded_data["status"] == "graded"
    assert graded_data["score"] == 9.5
    assert graded_data["passed"] is True
    assert graded_data["feedback"] == "Отличная аргументация выбора consistent hashing!"
    assert graded_data["reviewed_at"] is not None

    # 5. Кандидат видит обновленный результат в my-submissions
    my_subs = await client.get("/api/v1/candidate/tasks/my-submissions", headers=cand_headers)
    assert my_subs.status_code == 200
    assert len(my_subs.json()) == 1
    assert my_subs.json()[0]["score"] == 9.5
    assert my_subs.json()[0]["status"] == "graded"

    # 6. В ленте активности кандидата зафиксирована проверка работодателем (B-29)
    act_resp = await client.get("/api/v1/candidate/activity", headers=cand_headers)
    assert act_resp.status_code == 200
    activities = act_resp.json()
    assert any(a["activity_type"] == "employer_task_reviewed" for a in activities)
    reviewed_act = next(a for a in activities if a["activity_type"] == "employer_task_reviewed")
    assert "Озон" in reviewed_act["title"]
    assert "9.5/10.0" in reviewed_act["description"]


@pytest.mark.asyncio
async def test_foreign_employer_cannot_review_others_task(client: AsyncClient):
    _, emp1_headers = await register_and_login(client, "emp7@b29.ru", "employer", "Компания 1")
    _, emp2_headers = await register_and_login(client, "emp8@b29.ru", "employer", "Компания 2")
    _, cand_headers = await register_and_login(client, "cand5@b29.ru", "candidate")

    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp1_headers,
        json={
            "title": "Задача Компании 1",
            "description": "Условие задачи",
            "task_type": "manual_review",
        },
    )
    task_id = create_resp.json()["id"]

    sub_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=cand_headers,
        json={"answer_text": "Мое решение"},
    )
    submission_id = sub_resp.json()["id"]

    # Компания 2 пытается оценить решение по задаче Компании 1
    cheat_resp = await client.post(
        f"/api/v1/employer/tasks/submissions/{submission_id}/review",
        headers=emp2_headers,
        json={"score": 10.0, "passed": True},
    )
    assert cheat_resp.status_code == 403
    assert "другой компании" in cheat_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_role_enforcement_candidate_cannot_create_employer_task(client: AsyncClient):
    _, cand_headers = await register_and_login(client, "cand6@b29.ru", "candidate")
    _, emp_headers = await register_and_login(client, "emp9@b29.ru", "employer", "Компания 3")

    # Кандидат пытается создать задание
    resp = await client.post(
        "/api/v1/employer/tasks",
        headers=cand_headers,
        json={"title": "Взлом", "description": "...", "task_type": "manual_review"},
    )
    assert resp.status_code == 403

    # Работодатель пытается отправить решение
    create_resp = await client.post(
        "/api/v1/employer/tasks",
        headers=emp_headers,
        json={"title": "Задание 1", "description": "...", "task_type": "manual_review"},
    )
    task_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/candidate/tasks/{task_id}/submit",
        headers=emp_headers,
        json={"answer_text": "Ответ работодателя"},
    )
    assert submit_resp.status_code == 403
