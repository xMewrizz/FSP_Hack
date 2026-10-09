# Задания с развернутым ответом и оценка моделью (B-27)

Документ описывает реализацию открытых заданий (архитектурные кейсы и задачи по написанию кода) с автоматической оценкой через LLM (`Qwen2.5` в Ollama) и надежным детерминированным fallback-контуром в соответствии с регламентом хакатона.

---

## 1. Архитектура и поток данных

```
+---------------------------------------------------------------------------------+
|                                Frontend / Кандидат                              |
+---------------------------------------------------------------------------------+
                                      |
                      POST /testing/open-questions/{code}/submit
                                      v
+---------------------------------------------------------------------------------+
|                            Backend (FastAPI & PostgreSQL)                       |
| - Валидация прав кандидата и доступности вопроса                                |
| - Отправка на оценку в ML-сервис (с таймаутом и защитой от сетевых сбоев)       |
| - Сохранение в OpenQuestionSubmission (score, passed, criteria, review-флаг)    |
+---------------------------------------------------------------------------------+
                                      |
                         POST /evaluate-open-answer
                                      v
+---------------------------------------------------------------------------------+
|                                  ML-Service                                     |
|                                                                                 |
|   +--------------------------+                 +----------------------------+   |
|   |   Ollama / Qwen2.5       |  [сбой / оффлайн] |  Детерминированный         |   |
|   |   Structured JSON Output | ---------------> |  AST & Heuristic Fallback  |   |
|   |   evaluator: llm_qwen3   |                  |  evaluator: fallback_heur  |   |
|   |   needs_manual: False    |                  |  needs_manual_review: True |   |
|   +--------------------------+                 +----------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## 2. Расширенный банк открытых заданий (16 задач)

Банк заданий структурирован по грейдам (**Junior**, **Middle**, **Senior**) и специализациям (**Backend** и **Data Science**), покрывая 8 практических задач по коду (Python в различном контексте) и 8 комплексных архитектурных кейсов.

Все задачи хранятся в модуле `app.core.open_question_bank` с указанием проверяемого навыка (`skill`), допустимых вариантов решения (`acceptable_solutions`), эталонного решения (`reference_solution`) и атомарных критериев оценки (`rubric_criteria`).

### Матрица покрытия навыков и грейдов

| Специализация | Грейд | Код задания | Тип | Проверяемый навык | Ключевая тема |
|---|---|---|---|---|---|
| **Backend** | **Junior** | `OPEN-BE-ARCH-JR-01` | `free_text` | SQL и моделирование данных | Проектирование реляционной схемы БД заказов, FK, ON DELETE RESTRICT, индексы, soft delete |
| **Backend** | **Junior** | `OPEN-BE-CODE-JR-01` | `code` | Python для Backend & HTTP API | Асинхронный эндпоинт FastAPI с Pydantic-валидацией, статусом 201 Created и обработкой ошибок |
| **Backend** | **Middle** | `OPEN-BE-ARCH-01` | `free_text` | Архитектура и надёжность | Идемпотентный обработчик платежей, UNIQUE constraint, SELECT FOR UPDATE, reconciliation worker |
| **Backend** | **Middle** | `OPEN-BE-CODE-01` | `code` | Python для Backend и алгоритмы | Скользящий ограничитель запросов (`SlidingWindowRateLimiter`) на `deque` с очисткой окна |
| **Backend** | **Middle** | `OPEN-BE-ARCH-MID-02` | `free_text` | SQL и работа с транзакциями | Разрешение Deadlocks, уровни изоляции Read Committed vs Repeatable Read, ORDER BY id FOR UPDATE |
| **Backend** | **Middle** | `OPEN-BE-CODE-MID-02` | `code` | Python & Concurrency (asyncio) | Асинхронный воркер очереди задач с graceful shutdown, таймаутами и finally queue.task_done() |
| **Backend** | **Senior** | `OPEN-BE-ARCH-SR-01` | `free_text` | Распределенные системы | Распределенные транзакции: Saga Orchestrator, Transactional Outbox + CDC (Debezium/Kafka), DLQ |
| **Backend** | **Senior** | `OPEN-BE-CODE-SR-01` | `code` | Python High-Load Concurrency | Пул асинхронных воркеров с управлением Backpressure (ограниченная очередь) и Circuit Breaker |
| **Data Science** | **Junior** | `OPEN-DS-ARCH-JR-01` | `free_text` | ML-валидация и статистика | Валидация временных рядов (Time-based split), GroupKFold по пользователям, изоляция препроцессинга |
| **Data Science** | **Junior** | `OPEN-DS-CODE-JR-01` | `code` | Python & Pandas Processing | Оптимизация памяти (category, datetime, downcast), векторизованная фильтрация и groupby aggregation |
| **Data Science** | **Middle** | `OPEN-DS-ARCH-01` | `free_text` | MLOps и онлайн-инференс | Real-Time ML Serving (Redis Feature Store, P99 < 50мс), асинхронное логирование в Kafka, дрейф данных |
| **Data Science** | **Middle** | `OPEN-DS-CODE-01` | `code` | ML-валидация и пайплайны | Честная K-Fold кросс-валидация без Data Leakage (fit StandardScaler строго внутри обучающего фолда) |
| **Data Science** | **Middle** | `OPEN-DS-ARCH-MID-02` | `free_text` | A/B тестирование и статистика | Дизайн A/B теста, расчет выборки по MDE/мощности, диагностика SRM через Chi-square, FDR коррекция |
| **Data Science** | **Middle** | `OPEN-DS-CODE-MID-02` | `code` | Статистика и A/B (CUPED) | Снижение дисперсии методом CUPED: расчет $\theta = \mathrm{Cov}(Y, X)/\mathrm{Var}(X)$ и скорректированной метрики |
| **Data Science** | **Senior** | `OPEN-DS-ARCH-SR-01` | `free_text` | Enterprise MLOps & Vector DB | Корпоративный Feature Store (Offline point-in-time join + Online Redis), 2-stage ANN HNSW, Shadow Deploy |
| **Data Science** | **Senior** | `OPEN-DS-CODE-SR-01` | `code` | Sklearn Architecture & Math | Кастомный sklearn-оценщик (BaseEstimator, ClassifierMixin) с калибровкой вероятностей и Brier Score |

---

## 3. Оценка моделью (LLM Evaluation) и защита от мягкого промпта

### Проблема «мягкого промпта» (Lenient Prompt Bias)
В непродуманных промптах языковая модель склонна засчитывать поверхностные ответы: если кандидат просто упоминает названия библиотек («использую StandardScaler», «сделаю через Redis») без правильной логики или с грубыми ошибками (например, вызов `fit()` на всей выборке до сплита), модель может выставить положительную оценку.

### Меры устранения в B-27:
1. **Строгий системный промпт**:
   - Явное правило: *«Простое упоминание терминов, библиотек или ключевых слов НЕ дает зачет по критерию. Критерий считается выполненным (met: true) ТОЛЬКО если кандидат явно и технически корректно описал или запрограммировал требуемую логику, согласующуюся с эталонным решением»*.
   - Прямое указание: *«Если в ответе содержится грубая ошибка, антипаттерн или прямое нарушение критерия (data leakage, race condition, неверные формулы, отсутствие обязательных блоков), данный критерий ОБЯЗАН быть помечен met: false»*.
2. **Атомарная рубрика**: Каждая задача разбита на 4–5 бинарных, технически проверяемых критериев.
3. **Строгая привязка балла к критериям**: Итоговый балл формируется на основе доли выполненных критериев, исключая галлюцинации завышенного балла при проваленных пунктах рубрики.

---

## 4. Детерминированный Fallback (Регламент хакатона)

В соответствии с правилом `docs/05-backlog.md`:
> «Если LLM недоступна, ответ на развёрнутое задание ждёт ручной проверки; автоматически присваивать за него балл нельзя.»

При недоступности сервиса Ollama активируется детерминированный эвристический fallback:
1. **Предварительный фильтр синтаксиса (AST)**: Для заданий с кодом синтаксические ошибки (`SyntaxError`, `IndentationError`) детектируются за 0.1 мс до отправки в LLM, сохраняя ресурсы и фиксируя оценку 0.10.
2. **Фильтр Prompt Injection**: Регулярные выражения выявляют попытки подмены инструкций («ignore previous instructions», «поставь 100 баллов») и аннулируют балл до нуля.
3. **Инвариант безопасности**: `evaluator = "fallback_heuristic"`, `needs_manual_review = True`. Задание попадает в очередь ручной проверки для ревьюера.

---

## 5. API Эндпоинты

- `GET /api/v1/testing/open-questions?specialization={Backend|Data Science}&grade={junior|middle|senior}` — список доступных открытых задач с фильтрацией по специализации и грейду.
- `GET /api/v1/testing/open-questions/{code}` — детальная карточка задачи с описанием, допустимыми вариантами решения и рубрикой оценки (эталон скрыт).
- `POST /api/v1/testing/open-questions/{code}/submit` — отправка ответа кандидата на оценку.
- `GET /api/v1/testing/open-submissions` — история попыток кандидата со скорами и детализацией критериев.
- `GET /api/v1/testing/open-submissions/pending-review` — очередь для экспертов на ручную верификацию.
- `POST /api/v1/testing/open-submissions/{id}/review` — утверждение/исправление оценки экспертом.
