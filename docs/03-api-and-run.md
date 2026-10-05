# 03 — API и запуск (черновик)

## API
- Источник правды — Swagger: `http://localhost:8000/docs` (генерируется из FastAPI).
- Префикс `/api/v1`: `/auth`, `/candidates`, `/employers`, `/testing`, `/matching`, `/invitations`, `/vacancies`, `/fsp`, `/uploads`.
- Контракты: Pydantic-схемы, коды ошибок в `docs` OpenAPI. Зарплата — объект `{min, max, currency: RUB}` обязателен.
- Видимость контактов: поле `contacts` отдается только если `invitation.status == accepted` и запрашивает участник сделки.

## Запуск
См. README §5. Полная инструкция для жюри будет здесь перед сдачей (шаги: клонировать → `.env` → `docker compose up --build` → сиды `make seed`).

## Библиотеки (фиксируем при scaffolding)
Backend: fastapi, uvicorn, sqlalchemy, alembic, pydantic v2, psycopg, redis, python-jose, passlib[bcrypt], python-multipart, pypdf, reportlab.
ML: ollama/vllm-клиент, transformers, sentence-transformers, scikit-learn, numpy.
Frontend: react, react-router-dom, @tanstack/react-query, axios, tailwindcss, recharts (аналитика), axios-mock? нет — только реальный бэк.

## 152-ФЗ чеклист
- [ ] Согласие при регистрации (текст + timestamp)
- [ ] Настройка приватности профиля
- [ ] Разграничение ролей на каждом эндпоинте
- [ ] Хеши паролей, TTL токенов, подтверждение email
