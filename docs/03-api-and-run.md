# API и локальный запуск

Ниже перечислены API, которые есть в коде. Основной сценарий проверен на запущенном Compose с PostgreSQL. Отдельный бенчмарк B-31 пока не уложился в свой порог времени ответа.

Рядом с зарплатой в потребности, вакансии и приглашении показано: **«до вычета НДФЛ»** или **«на руки»**. Поле `salary_tax_type` хранится в соответствующих API. Интерфейсы публикации вакансий и откликов подключены к API; ручная проверка production-сценария с отдельными авторизованными ролями всё ещё нужна. На показе жюри должно суметь пройти тест самостоятельно. Для основного запуска не требуются GPU и работающая LLM.

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

По умолчанию предложения навыков и оценка отдельных открытых ответов используют локальную Ollama. На компьютере, где она запущена, загрузите модель командой `ollama pull qwen3:8b`. ML-сервис в Compose обращается к `http://host.docker.internal:11434` (`OLLAMA_BASE_URL`), модель — `qwen3:8b` (`OLLAMA_MODEL`). Для Qwen3 запрос отключает режим размышления и использует контекст 4096 токенов. Адрес `OLLAMA_BASE_URL` — настройка клиента внутри Compose; `OLLAMA_HOST` — настройка самого сервера Ollama. Не задавайте серверный `OLLAMA_HOST` в `.env` проекта вместо адреса клиента.

Если Ollama работает в Windows, а контейнер не видит её, задайте для приложения Ollama `OLLAMA_HOST=0.0.0.0:11434` и перезапустите его ([инструкция Ollama для Windows](https://docs.ollama.com/faq)). Порт 11434 должен быть доступен контейнеру; публиковать его в интернет не требуется. Проверить связь можно из корня репозитория: `docker compose exec ml-service python -c "import httpx; print(httpx.get('http://host.docker.internal:11434/api/tags').status_code)"` — ожидается `200`. После первого запроса `ollama ps` покажет, загружена ли модель на GPU. Ответ модели запрашивается в JSON по схеме и проверяется сервисом ([документация Ollama](https://docs.ollama.com/capabilities/structured-outputs)). Если Ollama не запущена или модель не установлена, ручное заполнение потребности остаётся доступным.

Для запуска через OpenRouter скопируйте `.env.example` в `.env` и задайте там `LLM_PROVIDER=openrouter` и свой `OPENROUTER_API_KEY`. Модель по умолчанию — [`qwen/qwen3-14b`](https://openrouter.ai/qwen/qwen3-14b); её можно заменить через `OPENROUTER_MODEL`. Затем пересоздайте ML-сервис: `docker compose up -d --build ml-service`. Ключ хранится только в локальном `.env`, который исключён из Git. OpenRouter получает текст потребности работодателя при запросе подсказки; при проверке открытого задания — вопрос, критерии, эталон и ответ кандидата. Не включайте в эти тексты лишние персональные данные. Без ключа подсказка вернёт ошибку. Ответ из базового набора при недоступной модели не сохраняется: кандидат увидит ошибку и сможет отправить его позже. Запросы с настоящим ключом проверены на локальном стенде; время и результаты полного прохождения записаны в [проверке тестов](./23-browser-grade-audit.md).

Пробный запуск кода для поддерживаемых заданий Backend выполняется в отдельном Docker-контейнере. Чтобы включить его на локальном стенде, добавьте в `.env` строки `COMPOSE_PROFILES=sandbox` и `SANDBOX_SERVICE_URL=http://sandbox-controller:8002`, затем выполните `docker compose up -d --build sandbox-controller backend`. Контроллеру нужен доступ к Docker socket; используйте этот профиль только на доверенном стенде. Проверка ограничений и очистки контейнеров: `docker compose exec -T -e PYTHONPATH=/app sandbox-controller python /app/tests/integration_b25_docker.py`.

После запуска выбранной модели можно выполнить `uv run --project backend python ml-service/check_need_suggestions.py` из корня репозитория. Скрипт выводит навыки, веса и время ответа для восьми вымышленных потребностей. Флаг `--direct` проверяет текущий код напрямую; для локальной Ollama задайте `OLLAMA_BASE_URL=http://127.0.0.1:11434`. Предложения модели остаются черновиком, который работодатель проверяет перед сохранением.

Если обычные порты заняты, можно запустить отдельный Compose-проект с пустой базой:

```powershell
$env:DB_PORT = "15432"
$env:REDIS_PORT = "16379"
$env:ML_PORT = "18001"
$env:BACKEND_PORT = "18010"
$env:FRONTEND_PORT = "15173"
$env:VITE_API_URL = "http://localhost:18010/api/v1"
docker compose -p fsp-check up --build -d
```

Интерфейс будет на `http://localhost:15173`. Для проверки API задайте `$env:FSP_API_BASE_URL = "http://localhost:18010/api/v1"` и запустите `uv run python smoke_compose.py` из `backend/`. По окончании остановите проверочный проект командой `docker compose -p fsp-check down`; его база остаётся в отдельном томе Docker.

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

Для замера работающего Compose с PostgreSQL после заполнения демо-данных запустите из `backend/`: `uv run python benchmark_live_b31.py --concurrency 50 --rounds 3`. Скрипт измеряет чтение истории теста, поиск и подбор по потребности. Он не создаёт новые тестовые попытки. Результат зависит от нагрузки на компьютер, поэтому сравнивать изменения нужно повторными прогонами на одном стенде.

Заполнение базы демонстрационными данными (14 кандидатов, 2 работодателя, потребности, приглашения):
```powershell
# Можно вызвать через Swagger POST /api/v1/system/seed или curl:
curl -X POST http://localhost:8000/api/v1/system/seed
```

Среди них девять вымышленных профилей Data Science / ML: по три Junior, Middle и Senior. У каждого свой стек и дополнительные навыки. Их грейды и общие результаты теста сгенерированы для показа подборки; это не реальные прохождения и не доказательство готовности теста Data Science. Повторный вызов не создаёт дублей.

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

Загрузка PDF только разбирает файл и возвращает предпросмотр; сервер не сохраняет извлечённые поля автоматически. Кандидат проверяет/редактирует их в профиле и отдельно вызывает `PUT /candidates/profile`.
Фото профиля можно загрузить отдельно (JPG, PNG или WebP, до 5 МБ). Работодатель получает его только для опубликованного профиля; собственное фото кандидат может просматривать независимо от публикации.
Эндпоинты: `POST /candidates/profile/photo` (multipart-поле `file`), `GET /candidates/profile/photo`, `DELETE /candidates/profile/photo` и `GET /candidate/{candidate_id}/photo` для работодателя.
Публикация профиля и связь с ID участника ФСП требуют отдельных согласий. Согласие на привязку ФСП ID передаётся как `agreed_fsp_id_link`; при его отзыве ID и загруженные достижения удаляются. Эндпоинт привязки ID отвечает `403`, если согласие не сохранено.

Профиль также поддерживает `hobbies`, `education_level`, `university_course` и `birth_year`. Год рождения используется только для примерного возрастного фильтра и не раскрывает работодателю точную дату рождения. В `/matching/search` доступны `education_level`, `university_course_group` (`junior` — 1–2 курс, `senior` — 3+ курс), `age_min` и `age_max`.

Перед просмотром материалов и началом тестирования кандидат должен сохранить `agreed_test_confidentiality=true`; иначе тестовые эндпоинты отвечают `403`. Согласие включает обязательство не распространять задания, ответы, решения и скриншоты.

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/candidates/onboarding` | Заполнение профиля и выбор согласий | `Bearer JWT` (Candidate) | `{ "first_name": "Иван", "last_name": "Иванов", "specialization": "Backend", "declared_grade": "junior" \| "middle" \| "senior" \| "lead", "work_format": "remote" \| "office" \| "hybrid", "city": "Москва", "fsp_id": "FSP-77-001", "agreed_152_fz": true, "agreed_publication": false, "visibility_public": false, "agreed_osint": false }` | `200 OK`: `CandidateProfileResponse` (включая достижения ФСП и настройки видимости) |
| `GET` | `/candidates/profile` | Получить профиль текущего кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: `CandidateProfileResponse` |
| `PUT` | `/candidates/profile` | Частичное обновление данных и настроек видимости | `Bearer JWT` (Candidate) | Поля для обновления (город, стек, резюме, грейд, `agreed_publication`, `visibility_public` и др.) | `200 OK`: `CandidateProfileResponse` |
| `POST` | `/candidates/link-fsp` | Привязать или обновить ФСП ID | `Bearer JWT` (Candidate) | `{ "fsp_id": "FSP-78-042" }` | `200 OK`: `CandidateProfileResponse` с обновленными достижениями |
| `POST` | `/candidates/resume/upload` | Загрузить PDF-резюме и извлечь данные (парсинг `pypdf`) | `Bearer JWT` (Candidate) | Multipart Form (`file: UploadFile`) | `200 OK`: `ResumeParsedData` (email, телефон, контакты, стек, предложенный грейд) |
| `GET` | `/candidates/profile/pdf` | Скачать PDF-профиль после согласия на публикацию | `Bearer JWT` (Candidate) | — | `200 OK`: PDF без контактов; `403`, если согласия нет. Самостоятельно указанные навыки не помечаются как подтверждённые, данные ФСП обозначены как демонстрационные. |

---

### 3. Тестирование и подтверждение категории (`/api/v1/testing`)

Новый сценарий Backend использует `/testing/roadmap`: четыре теста навыков и два закреплённых открытых задания можно проходить в течение трёх дней. В ответе есть `open_questions`, `expires_at` и `retake_used`; после неудачной пересдачи Junior — `retry_available_at`. Грейд присваивается после всех шести шагов либо после ручной проверки спорного открытого ответа. После завершения первого набора повторный `POST /testing/roadmap` с тем же грейдом открывает одну пересдачу с новым трёхдневным сроком. После второй неудачи Middle/Senior предлагается грейд ниже; Junior может открыть новый цикл через неделю. Прежний `/testing/start` остался для совместимости и не присваивает грейд. Правила — в [описании тестирования](02-testing-matching.md).

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/testing/roadmap` | Открыть или продолжить набор обязательных навыков выбранного Backend-грейда | `Bearer JWT` (Candidate) | `{ "specialization": "Backend", "target_grade": "junior" }` либо `{}` для данных профиля | `201 Created`: прогресс набора и четыре навыка |
| `GET` | `/testing/roadmap/current` | Последний набор кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: набор или `null` |
| `GET` | `/testing/roadmap/{assessment_id}` | Прогресс конкретного набора | `Bearer JWT` (Candidate) | — | `200 OK`: результаты навыков и итог, если набор завершён |
| `POST` | `/testing/roadmap/{assessment_id}/stop` | Прервать текущий набор перед переходом на уровень ниже | `Bearer JWT` (Candidate) | `{}` | `200 OK`: набор со статусом `cancelled` |
| `POST` | `/testing/roadmap/{assessment_id}/skills/{skill_code}/start` | Начать или продолжить обязательный навык | `Bearer JWT` (Candidate) | — | `201 Created`: задания навыка без ключей; завершённый навык или истёкший набор даёт `409` |
| `GET` | `/testing/additional` | Доступные дополнительные тесты текущего подтверждённого грейда | `Bearer JWT` (Candidate) | — | `200 OK`: навыки и последние результаты |
| `POST` | `/testing/additional/{skill_code}/start` | Начать дополнительный тест | `Bearer JWT` (Candidate) | `{ "target_grade": "junior" }` — текущий подтверждённый грейд | `201 Created`: вопросы навыка; неподдерживаемая пара даёт `400` |
| `POST` | `/testing/start` | Прежний общий тест, только для совместимости; грейд не присваивает | `Bearer JWT` (Candidate) | `{ "specialization": "Backend", "target_grade": "senior" }` | `201 Created`: 12 заданий без ключей |
| `POST` | `/testing/{session_id}/submit` | Отправить ответы на тест навыка или прежний общий тест | `Bearer JWT` (Candidate) | `{ "answers": [ { "question_id": "...", "selected_answers": ["B"] } ] }` | `200 OK`: результат навыка; после последнего обязательного навыка — решение о грейде |
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
| `POST` | `/needs/parse` | Предложить навыки и их веса по описанию через выбранную модель; ничего не сохраняет | `Bearer JWT` (Employer) | `{ "text": "Нужен специалист для API и работы с данными..." }` (20–5000 символов) | `200 OK`: предложения модели и явно найденные грейд, зарплата, тип зарплаты, формат. Если модель недоступна или ответ некорректен — `503`; ручная форма работает |
| `POST` | `/needs` | Создать потребность в кандидате (с проверкой `salary_min <= salary_max`) | `Bearer JWT` (Employer) | `{ "title": "Senior Python Backend", "specialization": "Backend", "required_grade": "senior", "required_skills": [{"name": "PostgreSQL", "weight": 3}], "salary_min": 250000, "salary_max": 350000, "salary_tax_type": "gross", "currency": "RUB", "work_format": "remote", "city": "Москва", "description": "..." }` | `201 Created`: `EmployerNeedResponse` |
| `GET` | `/needs` | Список потребностей текущей компании | `Bearer JWT` (Employer) | — | `200 OK`: Массив `EmployerNeedResponse` |
| `GET` | `/needs/{id}` | Детали потребности своей компании | `Bearer JWT` (Employer) | — | `200 OK`: `EmployerNeedResponse` |
| `PUT` | `/needs/{id}` | Обновить параметры потребности | `Bearer JWT` (Employer) | Поля для обновления | `200 OK`: `EmployerNeedResponse` |
| `DELETE` | `/needs/{id}` | Удалить потребность | `Bearer JWT` (Employer) | — | `200 OK`: `{ "message": "Потребность успешно удалена" }` |

---

### 6. Обратный подбор и поиск кандидатов (`/api/v1/matching`)

| Метод | URL | Описание | Авторизация | Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/matching/for-need/{need_id}` | Обратный подбор кандидатов под конкретную потребность (ранжирование, % соответствия, объяснение) | `Bearer JWT` (Employer) | `need_id` | `200 OK`: `MatchingCandidatesResponse` (ранжированные кандидаты, match_score, match_explanation, ФСП бонус) |
| `GET` | `/matching/search` | Поиск по банку опубликованных профилей с подтверждённым грейдом | `Bearer JWT` (Employer) | Query: `specialization`, `grade` (подтверждённый), `stack` или `skill` (навыки), `work_format`, `city`, `fsp_only`. Параметр `verified_only` оставлен для совместимости: без него выдача также ограничена подтверждёнными профилями. | `200 OK`: Массив `CandidateMatchItem` |

---

#### Командная HR-карточка кандидата

Организация создаётся только после явного действия работодателя или при отправке приглашения; простое открытие списка команды или карточки кандидата не создаёт личную команду. Для принятия приглашения нужны аккаунт работодателя и подтверждённый совпадающий email. Владелец приглашает тимлидов и HR, тимлид — HR; только владелец может назначить тимлида. Владелец и тимлид назначают права просмотра/редактирования по каждой вакансии, а HR видит только вакансии с выданным доступом. Общие заметки, статусы и обсуждения ограничены подтверждённым членством в одной организации и опубликованными профилями кандидатов.

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/employer/team` | Состав HR-команды и приглашения | Работодатель | — | `EmployerTeamResponse`; для получателя приглашения организация может быть `null` до принятия |
| `POST` | `/employer/team/workspace` | Явно создать HR-пространство компании | Работодатель | — | `EmployerTeamResponse` |
| `POST` | `/employer/team/invitations` | Пригласить HR или тимлида (тимлида назначает только владелец) | Работодатель с правом управления командой | `{ "email": "colleague@company.ru", "team_role": "hr" }` (`hr` или `team_lead`) | Обновлённый `EmployerTeamResponse` |
| `POST` | `/employer/team/invitations/{invitation_id}/accept` | Принять приглашение с совпадающего подтверждённого email | Работодатель | — | Обновлённый `EmployerTeamResponse` |
| `DELETE` | `/employer/team/invitations/{invitation_id}` | Отменить ожидающее приглашение; тимлид может отменить только приглашение HR | Владелец или тимлид | — | Обновлённый `EmployerTeamResponse` |
| `GET` | `/employer/mentors` | Наставники среди кандидатов, связанных с компанией откликом или принятым приглашением | Работодатель | — | Публичные профили с включённой доступностью наставничества |
| `GET` | `/matching/candidates/{candidate_id}/review` | Загрузить приватную HR-карточку и командные сообщения | Участник организации | — | `CandidateReviewResponse` |
| `PUT` | `/matching/candidates/{candidate_id}/review` | Обновить заметки и HR-статусы | Участник организации | `notes`, `pipeline_status`, `contact_status`, `background_check_status` | Обновлённый `CandidateReviewResponse`; этапы включают оффер, онбординг, работу с ментором и найм |
| `POST` | `/matching/candidates/{candidate_id}/review/messages` | Отправить внутреннее сообщение команде | Участник организации | `{ "body": "Обсудим вопросы для интервью" }` (1–4000 символов) | Обновлённый `CandidateReviewResponse` |

Карточки доступны только для публичных профилей с подтверждённым грейдом. Статусы поиска контакта и проверки СБ — ручная фиксация HR; они не отправляют сообщение кандидату и не запускают внешнюю проверку. Matching API возвращает публичные поля резюме `bio`, `github_url`, `resume_text` и `resume_url`, но не контакты аккаунта. Наставнический список также требует публичности профиля и явного согласия кандидата быть наставником. Миграции командных пространств, этапов и ролей — [007](../backend/alembic/versions/007_employer_candidate_workspaces.py), [012](../backend/alembic/versions/012_candidate_review_onboarding_stages.py) и [013](../backend/alembic/versions/013_employer_team_roles.py).

### 7. Прямые приглашения / Офферы (`/api/v1/invitations`)

#### Чат принятого приглашения

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/invitations/messages/unread-count` | Счётчик непрочитанных сообщений и значения по ID приглашения | Участник | — | `{ "unread_count": 1, "by_invitation": { "<id>": 1 } }` |
| `GET` | `/invitations/{id}/messages` | История чата; помечает входящие сообщения прочитанными | Участник принятого приглашения | — | Список сообщений и `unread_count` |
| `POST` | `/invitations/{id}/messages` | Отправить текстовое сообщение длиной 1–4000 символов | Участник принятого приглашения | `{ "body": "Здравствуйте!" }` | Сообщение с временем и признаком `is_mine` |

До принятия приглашения чат недоступен. Для production запустить [миграцию 005](../backend/alembic/versions/005_invitation_conversations.py); участники и статус проверяются backend для каждого запроса. Frontend обновляет открытую историю с интервалом 5 секунд, без WebSocket.

#### Наставничество и профессиональная сеть

Наставники — кандидаты, которые сами включили `mentor_available` в настройках и имеют подтверждённый грейд выше пользователя, выполняющего поиск. Карточка поиска не раскрывает контакты. Для принятия новых запросов и переписки используйте [миграцию 006](../backend/alembic/versions/006_mentorship_network.py).

| Метод | URL | Описание | Авторизация | Параметры / тело | Ответ |
|---|---|---|---|---|---|
| `GET` | `/network/mentors` | Поиск наставников по навыку и специализации | Кандидат | `skill`, `specialization` | Профили с подтверждённым более высоким грейдом, без контактных данных |
| `GET` | `/network/stats` | Число отправленных запросов наставникам для сводки кандидата | Кандидат | — | `{ "mentorship_requests_sent": 2 }` |
| `POST` | `/network/mentorship-requests` | Запросить наставничество с сообщением и фокусом навыка | Кандидат | `mentor_user_id`, `skill_focus`, `message` (до 4000 символов) | Созданный диалог со статусом `pending` |
| `GET` | `/network/conversations` | Диалоги наставничества, входящие запросы и статусы | Кандидат | — | Список диалогов; `can_accept` выставлен только наставнику |
| `POST` | `/network/conversations/{id}/accept` | Принять входящий запрос | Приглашённый наставник | — | Диалог со статусом `accepted` |
| `POST` | `/network/conversations/{id}/decline` | Отклонить входящий запрос | Приглашённый наставник | — | `204 No Content` |
| `GET` | `/network/conversations/{id}/messages` | Читать историю запроса или принятого диалога | Участник | — | Сообщения с `is_mine` и временем |
| `POST` | `/network/conversations/{id}/messages` | Отправить текст в принятом диалоге | Участник принятого диалога | `{ "body": "..." }` | `201 Created`; до принятия — `409` |

В поиске не показываются кандидаты без подтверждённого собственного грейда: система не может достоверно определить, кто выше. Повторный активный запрос между той же парой пользователей отклоняется с `409`.

| Метод | URL | Описание | Авторизация | Тело запроса | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/invitations` | Отправить приглашение кандидату; `need_id`, если указан, должен принадлежать компании. Контакты скрыты до принятия. | `Bearer JWT` (Employer) | `{ "candidate_id": "...", "need_id": "...", "offer_description": "...", "contact_method": "...", "salary_min": 250000, "salary_max": 350000, "salary_tax_type": "gross", "currency": "RUB" }` (`gross` — до вычета НДФЛ, `net` — на руки) | `201 Created`: `InvitationResponse` (`status="sent"`, `candidate_contacts=None`) |
| `GET` | `/invitations/sent` | Список отправленных компанией приглашений | `Bearer JWT` (Employer) | — | `200 OK`: Список приглашений (контакты раскрываются только если `status="accepted"`) |
| `GET` | `/invitations/my` | Входящие приглашения кандидата (автоматически переводит статус в `viewed`) | `Bearer JWT` (Candidate) | — | `200 OK`: Список входящих офферов |
| `POST` | `/invitations/{id}/accept` | Принять приглашение (раскрывает контакты работодателю) | `Bearer JWT` (Candidate) | `{ "reply": "Спасибо, согласен!" }` | `200 OK`: `InvitationResponse` (`status="accepted"`) |
| `POST` | `/invitations/{id}/reject` | Отклонить приглашение | `Bearer JWT` (Candidate) | `{ "reply": "Не подходит зарплатная вилка" }` | `200 OK`: `InvitationResponse` (`status="rejected"`) |

---

### 8. Демонстрационные данные ФСП (`/api/v1/fsp`)

| Метод | URL | Описание | Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/fsp/athletes` | Тестовые записи ФСП | — | `200 OK`: вымышленные участники и достижения |
| `GET` | `/fsp/verify/{fsp_id}` | Поиск ID в демонстрационных данных | `fsp_id` (например, `FSP-77-001`) | `200 OK`: найденная тестовая запись или пустой результат; совпадение не подтверждает личность |

Вход по одному ФСП ID отключён: известный ID из демо-набора не доказывает владение учётной записью. Путь `/fsp/keycloak/userinfo` также удалён; настоящую интеграцию OIDC можно добавить после настройки доверенного провайдера и проверки токена. Поле `fsp_verified` в текущем API означает совпадение ID с записью, а не проверку личности. В демо достижения не меняют подтверждённый грейд.

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
| `GET` | `/vacancies/{id}/permissions` | Права участников команды на вакансию (только владелец HR-пространства) | Employer | — | `200 OK`: список `user_id`, `can_view`, `can_edit` |
| `PUT` | `/vacancies/{id}/permissions` | Назначить или отозвать права участника (`can_edit` включает просмотр) | Employer | `user_id`, `can_view`, `can_edit` | `200 OK`: обновлённый список прав |
| `GET` | `/vacancies/{id}` | Детали вакансии | Публичный | — | `200 OK`: `VacancyResponse` |
| `PATCH` | `/vacancies/{id}` | Обновление вакансии | `Bearer JWT` (Employer) | `VacancyUpdate` | `200 OK`: `VacancyResponse` |
| `DELETE` | `/vacancies/{id}` | Удаление вакансии | `Bearer JWT` (Employer) | — | `204 No Content` |
| `POST` | `/vacancies/{id}/apply` | Самостоятельный отклик кандидата | `Bearer JWT` (Candidate) | `ApplicationCreate` (`cover_letter`) | `201 Created`: `ApplicationCandidateResponse` |
| `GET` | `/vacancies/applications/my` | Мои отклики на вакансии | `Bearer JWT` (Candidate) | — | `200 OK`: `list[ApplicationCandidateResponse]` |
| `GET` | `/vacancies/{id}/applications` | Список откликов (раскрывает контакты только автору вакансии, 152-ФЗ) | `Bearer JWT` (Employer) | — | `200 OK`: `list[ApplicationEmployerResponse]` (с контактами) |
| `PATCH` | `/vacancies/applications/{id}/status` | Изменение статуса отклика (`accepted`, `rejected`) | `Bearer JWT` (Employer) | `ApplicationStatusUpdate` (`status`) | `200 OK`: статус обновлен |

---

**Актуальное правило доступа (заменяет устаревшее описание в таблице выше):** права на конкретную вакансию назначает владелец HR-пространства через `GET` и `PUT /vacancies/{id}/permissions`. Право редактирования включает просмотр. Владелец команды может выдать участнику доступ к вакансиям других авторов в своей организации; чтение откликов и контактов разрешено автору, владельцу команды и участникам с правом просмотра. Изменять вакансию и статусы откликов могут автор, владелец команды и участник с правом редактирования.

### 11. Открытые вопросы и проверка кода (B-25, B-27) (`/api/v1/testing`)

| Метод | URL | Описание | Доступ | Тело / Параметры | Ответ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/testing/open-questions` | Список открытых вопросов с критериями, без эталонов и допустимых решений | Публичный | `specialization`, `grade` (опционально) | `200 OK`: `list[OpenQuestionResponse]` |
| `GET` | `/testing/open-questions/{code}` | Просмотр открытого вопроса по коду | Публичный | — | `200 OK`: `OpenQuestionResponse` |
| `POST` | `/testing/open-questions/{code}/submit` | Сдача ответа; код передаётся на оценку модели, но не исполняется в backend. Для обязательного задания передайте ID начатого набора | `Bearer JWT` (Candidate) | `{ "answer_text": "...", "assessment_id": "UUID" }` | `201 Created`: `OpenQuestionSubmissionResponse`; без `assessment_id` ответ остаётся отдельной практикой |
| `POST` | `/testing/code-sandbox/execute` | Запуск кода через отдельный Docker-исполнитель при включённом профиле `sandbox` | `Bearer JWT` (Candidate) | `{ "code": "...", "question_code": "...", "timeout_seconds": 3.0 }` | `200 OK`: результат тестов; `400` для неподдерживаемого задания; `503`, если исполнитель недоступен |
| `POST` | `/testing/open-questions/{code}/test-run` | Пробный запуск задания с кодом через отдельный исполнитель | `Bearer JWT` (Candidate) | `{ "code": "...", "timeout_seconds": 3.0 }` | `200 OK`: результат тестов; `400` для неподдерживаемого задания; `503`, если исполнитель недоступен |
| `GET` | `/testing/open-submissions` | История отправленных решений кандидата | `Bearer JWT` (Candidate) | — | `200 OK`: `list[OpenQuestionSubmissionResponse]` |
| `GET` | `/testing/open-submissions/pending-review` | Список решений, ожидающих проверки | `Bearer JWT` (Admin) | — | `200 OK`: `list[OpenQuestionSubmissionResponse]` |
| `POST` | `/testing/open-submissions/{id}/review` | Ручная оценка решения | `Bearer JWT` (Admin) | `{ "score": 0.9, "passed": true, "notes": "..." }` | `200 OK`: `OpenQuestionSubmissionResponse` |
