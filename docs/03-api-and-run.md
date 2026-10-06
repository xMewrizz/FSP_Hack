# API и локальный запуск

## Интерактивная документация (Swagger / ReDoc)

При запущенном бэкенде интерактивная документация доступна автоматически:
* **Swagger UI (интерактивное тестирование эндпоинтов):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc (детализированная спецификация):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI JSON схема:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Как запустить бэкенд локально

### Вариант 1. Через UV (рекомендуемый, быстрый)
Из корня репозитория в PowerShell:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Запуск тестов:
```powershell
uv run pytest -v
```

### Вариант 2. Через Docker Compose
Из корня проекта:
```powershell
docker compose up --build backend db
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

### 2. Профиль и онбординг кандидата (`/api/v1/candidates`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/candidates/onboarding` | Прохождение онбординга (152-ФЗ, грейд, ФСП ID, OSINT) | `Bearer JWT` (Candidate) | `{ "first_name": "Иван", "last_name": "Иванов", "specialization": "Backend", "declared_grade": "junior" \| "middle" \| "senior" \| "lead", "work_format": "remote" \| "office" \| "hybrid", "city": "Москва", "fsp_id": "FSP-77-001", "agreed_152_fz": true, "agreed_osint": true }` | `200 OK`: `CandidateProfileResponse` (включая верифицированные награды ФСП) |
| `GET` | `/candidates/profile` | Получить профиль текущего кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: `CandidateProfileResponse` |
| `PUT` | `/candidates/profile` | Частичное обновление данных профиля | `Bearer JWT` (Candidate) | Поля для обновления (город, стек, резюме, грейд и др.) | `200 OK`: `CandidateProfileResponse` |
| `POST` | `/candidates/fsp/link` | Привязать или обновить ФСП ID | `Bearer JWT` (Candidate) | `{ "fsp_id": "FSP-78-042" }` | `200 OK`: `CandidateProfileResponse` с обновленными достижениями |

---

### 3. Профиль работодателя (`/api/v1/employers`)

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/employers/onboarding` | Заполнение профиля компании | `Bearer JWT` (Employer) | `{ "company_name": "ООО Технологии", "description": "...", "industry": "IT", "website": "https://...", "contact_person": "Анна", "city": "Москва" }` | `200 OK`: `EmployerProfileResponse` |
| `GET` | `/employers/profile` | Получить профиль компании | `Bearer JWT` (Employer) | — | `200 OK`: `EmployerProfileResponse` |
| `PUT` | `/employers/profile` | Обновить данные профиля компании | `Bearer JWT` (Employer) | Поля компании для обновления | `200 OK`: `EmployerProfileResponse` |

---

### 4. Реестр ФСП и Keycloak OIDC Mock (`/api/v1/fsp`)

| Метод | URL | Описание | Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/fsp/athletes` | Список спортсменов демонстрационного реестра | — | `200 OK`: Массив спортсменов с рейтингом и разрядами |
| `GET` | `/fsp/verify/{fsp_id}` | Проверка ФСП ID и подтягивание турниров | `fsp_id` (например, `FSP-77-001`, `FSP-78-042`) | `200 OK`: `FSPVerificationResult` (`found`, `athlete_name`, `sport_category`, `achievements`) |
| `GET` | `/fsp/keycloak/userinfo` | OIDC Keycloak UserInfo эндпоинт | `fsp_id` | `200 OK`: JSON профиля спортсмена для OAuth2 SSO |
| `POST` | `/fsp/login-by-fsp-id` | Быстрый вход (SSO) в 1 клик по ФСП ID | `fsp_id` в Query | `200 OK`: `TokenResponse` (автоматическая регистрация и авторизация) |

---

### 5. Системные маршруты

| Метод | URL | Описание | Ответ |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Проверка здоровья сервиса | `{"status": "ok"}` |
| `GET` | `/docs-health` | Ссылки на документацию | `{"swagger": "/docs", "redoc": "/redoc"}` |
