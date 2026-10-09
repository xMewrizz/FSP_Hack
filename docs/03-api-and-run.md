# API и локальный запуск

Ниже перечислены API, которые есть в коде. На 8 октября 2026 года прошли 28 backend-тестов; отдельный бенчмарк B-31 не уложился в свой порог времени ответа. Основной сценарий проверен на запущенном Compose с PostgreSQL.

Рядом с зарплатой в потребности, вакансии и приглашении надо писать: **«до вычета НДФЛ»** или **«на руки»**. Сейчас в API есть только сумма и валюта; пометку ещё нужно добавить. Жюри должно суметь пройти тест самостоятельно. Для запуска на их стенде не должны требоваться GPU и работающая LLM.

## Интерактивная документация (Swagger / ReDoc)

При запущенном бэкенде интерактивная документация доступна автоматически:
* **Swagger UI (интерактивное тестирование всех эндпоинтов):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc (детализированная спецификация):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI JSON схема:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Как запустить бэкенд локально

### Весь сервис через Docker Compose

Из корня репозитория:

```powershell
docker compose up --build -d
```

Откройте `http://localhost:5173` для интерфейса и `http://localhost:8000/docs` для API. Если порт 8000 занят, задайте другой порт и тот же адрес API для сборки frontend:

```powershell
$env:BACKEND_PORT = "18000"
$env:VITE_API_URL = "http://localhost:18000/api/v1"
docker compose up --build -d
```

Адрес `VITE_API_URL` встраивается при сборке frontend. После его изменения нужна повторная сборка. Для проверки сценария на работающем backend запустите из `backend/` команду `uv run python smoke_compose.py` (при другом порте сначала задайте `$env:FSP_API_BASE_URL = "http://localhost:18000/api/v1"`). Скрипт создаёт две тестовые учётные записи.

### Быстрый запуск через UV
Из корня репозитория в PowerShell:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Запуск всех интеграционных тестов:
```powershell
uv run pytest -v
```

Замер B-31 запускается отдельно: `uv run pytest tests/benchmark_performance_b31.py -q -s`. Он использует SQLite внутри процесса, поэтому его цифры не заменяют проверку работающего стенда с PostgreSQL.

Заполнение базы реалистичными демонстрационными данными (5 кандидатов, 2 работодателя, потребности, приглашения):
```powershell
# Можно вызвать через Swagger POST /api/v1/system/seed или curl:
curl -X POST http://localhost:8000/api/v1/system/seed
```

---

## Спецификация реализованных эндпоинтов (v1)

Базовый префикс всех маршрутов: `/api/v1`

### 1. Аутентификация и сессии (`/api/v1/auth`)

| Метод | URL | Описание | Авторизация | Тело запроса / Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Регистрация кандидата или работодателя | Нет | `{ "email": "user@example.com", "password": "...", "role": "candidate" \| "employer" }` | `201 Created`: `{ "message": "...", "email": "...", "verification_code": "123456" }` |
| `POST` | `/auth/verify-email` | Подтверждение email 6-значным кодом | Нет | `{ "email": "user@example.com", "code": "123456" }` | `200 OK`: `TokenResponse` (`access_token`, `refresh_token`, `role`, `user_id`, `onboarding_completed`) |
| `POST` | `/auth/resend-code` | Повторная отправка кода верификации | Нет | `{ "email": "user@example.com" }` | `200 OK`: `{ "message": "...", "email": "..." }` |
| `POST` | `/auth/login` | Вход по логину (email) и паролю | Нет | `{ "email": "user@example.com", "password": "..." }` | `200 OK`: `TokenResponse` (`access_token`, `refresh_token`, ...) |
| `POST` | `/auth/refresh` | Ротация токенов по refresh_token | Нет | `{ "refresh_token": "..." }` | `200 OK`: `TokenResponse` с новой парой токенов |
| `POST` | `/auth/logout` | Отзыв сессии / выход | Нет | `{ "refresh_token": "..." }` | `200 OK`: `{ "message": "Успешный выход из системы" }` |
| `GET` | `/auth/me` | Данные текущего пользователя и его роли | `Bearer JWT` | — | `200 OK`: `UserMeResponse` (роль, флаг `onboarding_completed`, профиль) |

---

### 2. Профиль и онбординг кандидата (`/api/v1/candidate` и `/api/v1/candidates`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/candidates/onboarding` | Заполнение профиля и выбор согласий | `Bearer JWT` (Candidate) | `{ "first_name": "Иван", "last_name": "Иванов", "specialization": "Backend", "declared_grade": "junior" \| "middle" \| "senior" \| "lead", "work_format": "remote" \| "office" \| "hybrid", "city": "Москва", "fsp_id": "FSP-77-001", "agreed_152_fz": true, "agreed_publication": false, "visibility_public": false, "agreed_osint": false }` | `200 OK`: `CandidateProfileResponse` (включая достижения ФСП и настройки видимости) |
| `GET` | `/candidates/profile` | Получить профиль текущего кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: `CandidateProfileResponse` |
| `PUT` | `/candidates/profile` | Частичное обновление данных и настроек видимости | `Bearer JWT` (Candidate) | Поля для обновления (город, стек, резюме, грейд, `agreed_publication`, `visibility_public` и др.) | `200 OK`: `CandidateProfileResponse` |
| `POST` | `/candidates/link-fsp` | Привязать или обновить ФСП ID | `Bearer JWT` (Candidate) | `{ "fsp_id": "FSP-78-042" }` | `200 OK`: `CandidateProfileResponse` с обновленными достижениями |
| `DELETE` | `/candidates/link-fsp` | Отвязать ФСП ID от профиля и удалить достижения | `Bearer JWT` (Candidate) | — | `200 OK`: `CandidateProfileResponse` |
| `POST` | `/candidates/resume/upload` | Загрузить PDF-резюме и извлечь данные (парсинг `pypdf`) | `Bearer JWT` (Candidate) | Multipart Form (`file: UploadFile`) | `200 OK`: `ResumeParsedData` (email, телефон, контакты, стек, предложенный грейд) |
| `GET` | `/candidates/profile/pdf` | Скачать стандартизированный PDF-профиль текущего кандидата (`reportlab` с поддержкой кириллицы) | `Bearer JWT` (Candidate) | `include_contacts: bool = True` | `200 OK`: PDF-файл (`application/pdf`) с подтвержденными навыками и статусом ФСП |
| `GET` | `/candidates/{candidate_id}/pdf` | Скачать стандартизированный PDF-профиль кандидата (Работодатель, 152-ФЗ) | `Bearer JWT` (Employer) | `candidate_id: UUID` | `200 OK`: PDF-файл (контакты скрыты до принятия приглашения, 152-ФЗ) |

---

### 3. Тестирование и подтверждение категории (`/api/v1/testing`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/testing/start` | Начать тест на заявленный грейд и специализацию (проверка правила 90 дней и разблокировки по рекомендации) | `Bearer JWT` (Candidate) | `{ "specialization": "Backend", "target_grade": "senior" }` | `201 Created`: `TestStartResponse` (сессия, вопросы без ответов, варианты, темы) |
| `GET` | `/testing/status` | Текущий статус подтверждения грейда, кулдаун 90 дней, рекомендации и доступные тесты (B-12) | `Bearer JWT` (Candidate) | — | `200 OK`: `TestingStatusResponse` (`verified_grade`, `cooldown_active`, `cooldown_days_remaining`, `recommended_action`, `available_grades`) |
| `POST` | `/testing/{session_id}/submit` | Отправить ответы на тест и получить подтвержденный грейд | `Bearer JWT` (Candidate) | `{ "answers": [ { "question_id": "...", "selected_answers": ["B"] } ] }` | `200 OK`: `TestResultResponse` (баллы, процент, статус сдачи, разбивка по навыкам, присвоенный грейд, рекомендации) |
| `GET` | `/testing/history` | История попыток тестирования кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: Список пройденных сессий |
| `GET` | `/testing/{session_id}` | Детальные результаты конкретной сессии | `Bearer JWT` (Candidate) | — | `200 OK`: `TestResultResponse` |

---

### 4. Профиль работодателя (`/api/v1/employer` и `/api/v1/employers`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/employers/onboarding` | Заполнение профиля компании | `Bearer JWT` (Employer) | `{ "company_name": "ООО Технологии", "description": "...", "industry": "IT", "website": "https://...", "contact_person": "Анна", "city": "Москва" }` | `200 OK`: `EmployerProfileResponse` |
| `GET` | `/employers/profile` | Получить профиль компании | `Bearer JWT` (Employer) | — | `200 OK`: `EmployerProfileResponse` |
| `PUT` | `/employers/profile` | Обновить данные профиля компании | `Bearer JWT` (Employer) | Поля компании для обновления | `200 OK`: `EmployerProfileResponse` |

---

### 5. Потребности компании / Вакансии (`/api/v1/needs`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/needs` | Создать потребность в кандидате (с валидацией `min_salary <= max_salary`) | `Bearer JWT` (Employer) | `{ "title": "Senior Python Backend", "specialization": "Backend", "required_grade": "senior", "required_skills": [{"name": "PostgreSQL", "weight": 1.0}], "salary_min": 250000, "salary_max": 350000, "currency": "RUB", "work_format": "remote", "city": "Москва", "description": "..." }` | `201 Created`: `EmployerNeedResponse` |
| `GET` | `/needs` | Список потребностей текущей компании | `Bearer JWT` (Employer) | — | `200 OK`: Массив `EmployerNeedResponse` |
| `GET` | `/needs/{id}` | Детали потребности | Любая авторизация | — | `200 OK`: `EmployerNeedResponse` |
| `PUT` | `/needs/{id}` | Обновить параметры потребности | `Bearer JWT` (Employer) | Поля для обновления | `200 OK`: `EmployerNeedResponse` |
| `DELETE` | `/needs/{id}` | Удалить потребность | `Bearer JWT` (Employer) | — | `200 OK`: `{ "message": "Потребность успешно удалена" }` |

---

### 6. Обратный подбор и поиск кандидатов (`/api/v1/matching`)

| Метод | URL | Описание | Авторизация | Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/matching/for-need/{need_id}` | Обратный подбор кандидатов под конкретную потребность (ранжирование, % соответствия, объяснение) | `Bearer JWT` (Employer) | `need_id` | `200 OK`: `MatchingCandidatesResponse` (ранжированные кандидаты, match_score, match_explanation, ФСП бонус) |
| `GET` | `/matching/search` | Поиск по банку кандидатов с подтвержденными категориями | `Bearer JWT` (Employer) | Query: `specialization`, `grade` (только подтверждённый), `stack` (стек/навыки), `work_format`, `city`, `fsp_only`, `verified_only` | `200 OK`: Массив `CandidateMatchItem` |

---

### 7. Прямые приглашения / Офферы (`/api/v1/invitations`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/invitations` | Отправить прямое приглашение кандидату (контакты скрыты до принятия) | `Bearer JWT` (Employer) | `{ "candidate_id": "...", "need_id": "...", "offer_description": "...", "contact_method": "...", "salary_min": 250000, "salary_max": 350000, "currency": "RUB" }` | `201 Created`: `InvitationResponse` (`status="sent"`, `candidate_contacts=None`) |
| `GET` | `/invitations/sent` | Список отправленных компанией приглашений | `Bearer JWT` (Employer) | — | `200 OK`: Список приглашений (контакты раскрываются только если `status="accepted"`) |
| `GET` | `/invitations/my` | Входящие приглашения кандидата (автоматически переводит статус в `viewed`) | `Bearer JWT` (Candidate) | — | `200 OK`: Список входящих офферов |
| `POST` | `/invitations/{id}/accept` | Принять приглашение (раскрывает контакты работодателю) | `Bearer JWT` (Candidate) | `{ "reply": "Спасибо, согласен!" }` | `200 OK`: `InvitationResponse` (`status="accepted"`) |
| `POST` | `/invitations/{id}/reject` | Отклонить приглашение | `Bearer JWT` (Candidate) | `{ "reply": "Не подходит зарплатная вилка" }` | `200 OK`: `InvitationResponse` (`status="rejected"`) |

---

### 8. Реестр ФСП и Keycloak OIDC Mock (`/api/v1/fsp`)

| Метод | URL | Описание | Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/fsp/athletes` | Список спортсменов демонстрационного реестра | — | `200 OK`: Массив спортсменов с рейтингом и разрядами |
| `GET` | `/fsp/verify/{fsp_id}` | Проверка ФСП ID и подтягивание турниров | `fsp_id` (например, `FSP-77-001`, `FSP-78-042`) | `200 OK`: `FSPVerificationResult` (`found`, `athlete_name`, `sport_category`, `achievements`) |
| `GET` | `/fsp/keycloak/userinfo` | OIDC Keycloak UserInfo эндпоинт | `fsp_id` | `200 OK`: JSON профиля спортсмена для OAuth2 SSO |
| `POST` | `/fsp/login-by-fsp-id` | Быстрый вход (SSO) в 1 клик по ФСП ID | `fsp_id` в Query | `200 OK`: `TokenResponse` (автоматическая регистрация и авторизация) |

---

### 9. Системные маршруты и Demo Seeding (`/api/v1/system`)

| Метод | URL | Описание | Ответ |
| :--- | :--- | :--- | :--- |
| `POST` | `/system/seed` | Инициализация базы тестовыми кандидатами, компаниями, потребностями и приглашениями | `201 Created`: Инструкция с логинами и паролями (`Password123!`) |
| `GET` | `/api/v1/health` | Проверка здоровья сервиса | `{"status": "ok"}` |
| `GET` | `/docs-health` | Ссылки на документацию | `{"swagger": "/docs", "redoc": "/redoc"}` |

---

### 10. Публикация вакансий и отклики кандидатов (B-30) (`/api/v1/vacancies`)

| Метод | URL | Описание | Доступ | Тело / Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/vacancies` | Публикация вакансии с зарплатой («до вычета НДФЛ» / «на руки») | `Bearer JWT` (Employer) | `VacancyCreate` (`title`, `specialization`, `required_grade`, `salary_min`, `salary_max`, `salary_tax_type: "gross"|"net"`, `work_format`) | `201 Created`: `VacancyResponse` |
| `GET` | `/vacancies` | Поиск открытых вакансий по фильтрам | Публичный / Candidate | `specialization`, `required_grade`, `work_format`, `salary_tax_type`, `min_salary`, `city` | `200 OK`: `list[VacancyResponse]` |
| `GET` | `/vacancies/my` | Список вакансий компании | `Bearer JWT` (Employer) | — | `200 OK`: `list[VacancyResponse]` |
| `GET` | `/vacancies/{id}` | Детали вакансии | Публичный | — | `200 OK`: `VacancyResponse` |
| `PATCH` | `/vacancies/{id}` | Обновление вакансии | `Bearer JWT` (Employer) | `VacancyUpdate` | `200 OK`: `VacancyResponse` |
| `DELETE` | `/vacancies/{id}` | Удаление вакансии | `Bearer JWT` (Employer) | — | `204 No Content` |
| `POST` | `/vacancies/{id}/apply` | Самостоятельный отклик кандидата | `Bearer JWT` (Candidate) | `ApplicationCreate` (`cover_letter`) | `201 Created`: `ApplicationCandidateResponse` |
| `GET` | `/vacancies/applications/my` | Мои отклики на вакансии | `Bearer JWT` (Candidate) | — | `200 OK`: `list[ApplicationCandidateResponse]` |
| `GET` | `/vacancies/{id}/applications` | Список откликов (раскрывает контакты только автору вакансии, 152-ФЗ) | `Bearer JWT` (Employer) | — | `200 OK`: `list[ApplicationEmployerResponse]` (с контактами) |
| `PATCH` | `/vacancies/applications/{id}/status` | Изменение статуса отклика (`accepted`, `rejected`) | `Bearer JWT` (Employer) | `ApplicationStatusUpdate` (`status`) | `200 OK`: статус обновлен |
