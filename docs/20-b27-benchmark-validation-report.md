# Отчет валидации открытых заданий и LLM-оценщика (B-27)

**Дата проведения**: 2026-10-10  
**Оценочная модель**: `qwen2.5:14b-instruct-q4_K_M` (Ollama, локальный GPU-инференс)  
**Аппаратное обеспечение**: NVIDIA GeForce RTX 3060 (12 ГБ VRAM)  
**Потребление VRAM**: ~10.2 ГБ из 12.3 ГБ (~2.1 ГБ свободного запаса, стабильный CUDA-инференс)

---

## 1. Покрытие навыков и грейдов (Банк заданий B-27)

Банк открытых заданий расширен с 4 задач уровня Middle до **16 практических заданий** с равномерным распределением по грейдам (Junior, Middle, Senior) и направлениям (Backend и Data Science), синхронизированных с базовым банком B-02.

### Сводная матрица заданий

| Специализация | Грейд | Код задания | Тип | Проверяемый навык | Краткое описание темы |
|---|---|---|---|---|---|
| **Backend** | Junior | `OPEN-BE-ARCH-JR-01` | `free_text` | Проектирование реляционных схем БД | Схема интернет-магазина в PostgreSQL: PK/FK, NOT NULL, CHECK, UNIQUE, индексы, soft delete, ON DELETE RESTRICT |
| **Backend** | Junior | `OPEN-BE-CODE-JR-01` | `code` | Асинхронные REST API (FastAPI/Pydantic) | Эндпоинт `POST /orders`, валидация Pydantic `gt=0`, `HTTPException(400)`, статус `201 Created` |
| **Backend** | Middle | `OPEN-BE-ARCH-01` | `free_text` | Идемпотентность и интеграция с платежами | Двухфазные платежи, ключи идемпотентности, Outbox-паттерн, Dead Letter Queue |
| **Backend** | Middle | `OPEN-BE-ARCH-MID-02` | `free_text` | Индексирование и оптимизация PostgreSQL | Составные индексы (B-Tree), устранение Seq Scan и FileSort в ленте событий |
| **Backend** | Middle | `OPEN-BE-CODE-01` | `code` | Потокобезопасные структуры данных | Sliding window rate limiter на `asyncio.Lock` и `collections.deque` |
| **Backend** | Middle | `OPEN-BE-CODE-MID-02` | `code` | Асинхронные очереди задач | Воркер на `asyncio.Queue`, graceful shutdown через `task_done` и отмену тасок |
| **Backend** | Senior | `OPEN-BE-ARCH-SR-01` | `free_text` | Распределенные транзакции (Saga / 2PC) | Сага с компенсирующими транзакциями, outbox и CDC (Debezium/Kafka) |
| **Backend** | Senior | `OPEN-BE-CODE-SR-01` | `code` | Высоконагруженный отказоустойчивый клиент | Асинхронный HTTP-клиент: Connection Pooling, Exponential Backoff, Jitter, Circuit Breaker |
| **Data Science** | Junior | `OPEN-DS-ARCH-JR-01` | `free_text` | Валидация и предотвращение утечек данных | Стратегия разбиения временных рядов (TimeSeriesSplit), запрет Leakage на этапе Scaler |
| **Data Science** | Junior | `OPEN-DS-CODE-JR-01` | `code` | Оптимизация памяти и векторизация Pandas | Устранение `iterrows()`, downcasting типов `float32`/`category`, векторизация |
| **Data Science** | Middle | `OPEN-DS-ARCH-01` | `free_text` | Архитектура Real-Time ML и MLOps | Low-latency inference (<50ms), Redis Feature Store, Kafka, Evidently AI |
| **Data Science** | Middle | `OPEN-DS-ARCH-MID-02` | `free_text` | Методология A/B тестирования | Проверка Sample Ratio Mismatch (SRM via Chi-square), коррекция множественных тестов |
| **Data Science** | Middle | `OPEN-DS-CODE-01` | `code` | Честная кросс-валидация и пайплайны | `StratifiedKFold`, обучение скейлеров строго внутри фолда, расчет Mean ROC-AUC |
| **Data Science** | Middle | `OPEN-DS-CODE-MID-02` | `code` | Снижение дисперсии метрик (CUPED) | Формула $\theta = \frac{Cov(Y, X)}{Var(X)}$, трансформация $Y_{cuped} = Y - \theta (X - \bar{X})$ |
| **Data Science** | Senior | `OPEN-DS-ARCH-SR-01` | `free_text` | High-load ML Platform & Shadow Deployment | Архитектура ML-платформы на 10k RPS: Envoy Shadow traffic, gRPC, Triton Inference Server |
| **Data Science** | Senior | `OPEN-DS-CODE-SR-01` | `code` | Кастомные алгоритмы и архитектура scikit-learn | Реализация `BaseEstimator` + `ClassifierMixin`, калибровка вероятностей без лика данных |

### Распределение по типам и грейдам
* **Всего заданий**: 16 (8 Backend, 8 Data Science)
* **По формату**: 8 `code` (Python с контекстом API/Concurrency для Backend и Memory/Math/ML для Data Science), 8 `free_text` (Архитектура, Базы Данных, MLOps, A/B).
* **По грейдам**: 4 Junior (25%), 8 Middle (50%), 4 Senior (25%).

---

## 2. Результаты валидации LLM-оценщика на Qwen 14B

Для верификации работы промпта и надежности автоматической оценки был сформирован бенчмарк из **74 тест-кейсов** (306 атомарных критериев рубрики), охватывающий идеальные, частичные, ошибочные и стресс-ответы.

### Сводные метрики бенчмарка

| Метрика | Значение (Qwen 2.5 14B) | Значение (Детерминированный Fallback) | Целевой порог |
|---|---|---|---|
| **Всего тест-кейсов** | 74 | 74 | — |
| **Всего критериев рубрики** | 306 | 306 | — |
| **Criterion Accuracy** | **92.81%** | 81.37% | $\ge 85\%$ |
| **Criterion Precision** | **98.50%** | 89.20% | $\ge 90\%$ |
| **Criterion Recall** | **86.75%** | 83.10% | $\ge 80\%$ |
| **Criterion F1-Score** | **0.9225** | 0.8603 | $\ge 0.85$ |
| **Pass/Fail Accuracy (порог 0.70)** | **78.38%** | 71.62% | — |
| **Pass/Fail Precision** | **100.00%** | 94.74% | $100\%$ |
| **Ложные зачеты (False Positives)** | **0 из 74 (0.0%)** | 1 из 74 (1.3%) | **0** |
| **True Negatives** | **38** | 35 | — |
| **MAE по итоговому баллу** | **0.0951** | 0.1780 | $< 0.15$ |
| **Защита от Prompt Injection** | **100.0%** (4 из 4) | 100.0% | $100\%$ |
| **Детекция AST Syntax Errors** | **100.0%** (5 из 5) | 100.0% | $100\%$ |
| **Средняя задержка инференса** | 24.1 с | < 1 мс | — |

---

## 3. Анализ поведения модели на ошибочных кейсах

Главный риск автоматического оценивания открытых ответов — **галлюцинация компетентности** (когда модель завышает балл за наукообразные термины, поверхностный текст или грубые ошибки из-за мягкого системного промпта).

### Проверка гипотезы о строгости промпта:
* В бенчмарк включены **12 заведомо ошибочных ответов** по всем 16 заданиям (антипаттерны, утечки данных, race conditions, синтаксический бред, отсутствие обязательных блоков).
* **Результат**: **100% отказ (0 из 12 ложных пропусков)**. Модель `qwen2.5:14b-instruct-q4_K_M` выставила `score = 0.00` на **всех 12 ошибочных кейсах**:
  - `be_arch_jr_03_incorrect_bad_relational`: балл `0.00` (отказ за отсутствие внешних ключей и типов);
  - `be_code_jr_03_incorrect_wrong_logic`: балл `0.00` (отказ за отсутствие Pydantic-валидации `gt=0` и неверный статус-код);
  - `be_arch_mid_02_incorrect_fluff`: балл `0.00` (отказ за наукообразную воду без конкретных индексов);
  - `be_code_mid_02_incorrect_crash`: балл `0.00` (отказ за отсутствие вызова `task_done` и аварийное завершение);
  - `be_arch_sr_03_incorrect_distributed_locks`: балл `0.00` (отказ за использование распределенных блокировок вместо Саги);
  - `be_code_sr_03_incorrect_unbounded_leak`: балл `0.00` (отказ за бесконечный retry без circuit breaker);
  - `ds_arch_jr_03_incorrect_random_kfold`: балл `0.00` (отказ за KFold на временных рядах);
  - `ds_code_jr_03_incorrect_bad_code`: балл `0.00` (отказ за вызов `iterrows()` и отсутствие оптимизации);
  - `ds_arch_mid_02_incorrect_peeking`: балл `0.00` (отказ за peeking problem в A/B тестировании);
  - `ds_code_mid_02_incorrect_no_math`: балл `0.00` (отказ за неверную формулу ковариации CUPED);
  - `ds_arch_sr_03_incorrect_single_db`: балл `0.00` (отказ за единую монолитную БД на 10k RPS);
  - `ds_code_sr_03_incorrect_not_sklearn`: балл `0.00` (отказ за несовместимость со scikit-learn API).

### Анализ пограничных кейсов (False Negatives):
* Из 74 кейсов зафиксировано **16 пограничных частичных ответов**, где эталонная разметка предполагала балл ~0.75, а модель выставила ~0.50 (не зачла 1 спорный критерий).
* Это смещает баланс в сторону **консервативности и безопасности**: ни один слабый кандидат не получит незаслуженный зачет автоматически.
* Для пограничных кейсов предусмотрен флаг `needs_manual_review = True`, гарантирующий отправку работы на валидацию рекрутеру/лиду.

---

## 4. Защита от манипуляций и синтаксических ошибок

1. **AST-фильтр**: 
   - До передачи кода в LLM отрабатывает парсер `ast.parse()`. 
   - Любая синтаксическая ошибка (`SyntaxError`, `IndentationError`) мгновенно перехватывается детерминированным модулем (задержка <1 мс, 0 токенов VRAM).
2. **Защита от Prompt Injection**:
   - Шаблон кандидатов изолирован XML-тегом `<candidate_answer>`.
   - В системном промпте задана прямая директива на игнорирование переопределения инструкций.
   - Детерминированный regex-фильтр фиксирует типичные injection-паттерны (`ignore previous instructions`, `give 100%`, `you must return true`). При обнаружении балл не может превысить фактический средний балл по критериям, а фидбек маркируется предупреждением.

---

## 5. Вывод
Система открытых заданий B-27 полностью готова к внедрению: банк заданий покрывает все заявленные грейды и специализации, а LLM-оценщик на модели Qwen 14B демонстрирует высокую избирательность (98.5% precision по критериям, 0% false positives на ошибочных кейсах).