"""Скрипт прогона бенчмарка для открытых заданий (B-27).

Замеряет ключевые метрики системы оценки:
- Criterion Accuracy / F1 (попадание по отдельным критериям рубрики)
- Pass / Fail точность, полнота и F1 (порог 0.70)
- MAE (Mean Absolute Error) по итоговому баллу относительно Ground Truth
- Injection Defense Rate (% отраженных попыток манипуляции инструкциями)
- AST Syntax Error Detection Rate (% обнаруженных синтаксических ошибок в Python)
- Latency (время отклика LLM vs детерминированного fallback)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Добавляем пути к модулям проекта
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from benchmark_dataset import BENCHMARK_CASES, get_benchmark_cases
from open_evaluator import (
    OpenEvaluationResult,
    deterministic_fallback_evaluation,
    evaluate_open_answer,
    resolve_ollama_base_url,
    resolve_ollama_model,
)

# Вопросы и рубрики из open_question_bank
try:
    from app.core.open_question_bank import get_open_question_by_code
except ImportError:
    # Автономный банк вопросов на случай запуска без зависимостей бэкенда
    _FALLBACK_BANK = {
        "OPEN-BE-ARCH-JR-01": {
            "code": "OPEN-BE-ARCH-JR-01",
            "question_type": "free_text",
            "question_text": "Спроектируйте структуру реляционной базы данных (PostgreSQL) для интернет-магазина. Опишите таблицы `users`, `orders`, `order_items` и `products`. Укажите первичные и внешние ключи, типы данных, ограничения целостности (NOT NULL, CHECK, UNIQUE), стратегию удаления связанных записей (ON DELETE CASCADE vs RESTRICT), индексы для частых запросов выборки заказов пользователя по дате, а также подход к мягкому удалению (soft delete) и сохранению цен товаров на момент покупки.",
            "reference_solution": "1. Схема сущностей:\n   - users: id BIGSERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW();\n   - products: id BIGSERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, price NUMERIC(12, 2) NOT NULL CHECK (price > 0), stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0);\n   - orders: id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT, status VARCHAR(32) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), deleted_at TIMESTAMPTZ NULL;\n   - order_items: id BIGSERIAL PRIMARY KEY, order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE, product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT, quantity INT NOT NULL CHECK (quantity > 0), price_at_purchase NUMERIC(12, 2) NOT NULL CHECK (price_at_purchase > 0);\n2. Целостность и удаление: ON DELETE RESTRICT для users и products защищает от случайного удаления данных, на которые ссылаются финансовые проводки. ON DELETE CASCADE для order_items удаляет строки позиции заказа только при явном удалении самого заказа.\n3. Индексы: CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC) WHERE deleted_at IS NULL для быстрого отображения истории заказов клиента.\n4. Soft delete: deleted_at TIMESTAMPTZ NULL; при удалении проставляется NOW(), все выборки фильтруют WHERE deleted_at IS NULL.\n5. Историчность: price_at_purchase обязательно копируется в order_items в момент оформления, так как цена в products может меняться со временем.",
            "rubric_criteria": ["Описание сущностей, первичных ключей (PK) и типов данных с ограничениями целостности (NOT NULL, CHECK, UNIQUE)", "Определение внешних ключей (FK) с обоснованием правил удаления (ON DELETE RESTRICT для сохранения истории и транзакций)", "Назначение индексов под частые запросы (составной индекс по user_id и дате создания created_at)", "Реализация мягкого удаления (soft delete через deleted_at / is_deleted) и фиксация цены на момент покупки (price_at_purchase)"],
        },
        "OPEN-BE-CODE-JR-01": {
            "code": "OPEN-BE-CODE-JR-01",
            "question_type": "code",
            "question_text": "Напишите асинхронный эндпоинт на FastAPI `POST /orders` с моделью Pydantic `OrderCreate` (поля `item_id: int`, `quantity: int`, `price: float`). Поля quantity и price должны быть строго больше нуля. Эндпоинт должен проверять наличие товара через фиктивную асинхронную функцию `check_inventory(item_id: int, quantity: int) -> bool`. Если товара нет — выбрасывать `HTTPException(status_code=400, detail='Out of stock')`. При успехе возвращать словарь `{'order_id': 123, 'status': 'created'}` с явным HTTP-статусом `201 Created`.",
            "reference_solution": "from fastapi import APIRouter, HTTPException, status\nfrom pydantic import BaseModel, Field\n\nrouter = APIRouter()\n\nclass OrderCreate(BaseModel):\n    item_id: int\n    quantity: int = Field(gt=0, description='Количество должно быть > 0')\n    price: float = Field(gt=0.0, description='Цена должна быть > 0')\n\nasync def check_inventory(item_id: int, quantity: int) -> bool:\n    return True\n\n@router.post('/orders', status_code=status.HTTP_201_CREATED)\nasync def create_order(order: OrderCreate):\n    is_available = await check_inventory(order.item_id, order.quantity)\n    if not is_available:\n        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Out of stock')\n    return {'order_id': 123, 'status': 'created'}\n",
            "rubric_criteria": ["Определение схемы Pydantic с валидацией положительных значений quantity и price (gt=0 или валидатор)", "Объявление асинхронного FastAPI эндпоинта с явным указанием статус-кода 201 (status.HTTP_201_CREATED)", "Асинхронный вызов проверки наличия через await check_inventory", "Выброс HTTPException со статусом 400 при отсутствии остатков и возврат словаря с order_id при успехе"],
        },
        "OPEN-BE-ARCH-01": {
            "code": "OPEN-BE-ARCH-01",
            "question_type": "free_text",
            "question_text": "Опишите архитектуру и последовательность шагов сервиса обработки платежей при получении повторных webhook-уведомлений от платежного шлюза. Как гарантировать отсутствие повторного начисления баланса при сетевых тайм-аутах и повторной доставке сообщений? Опишите структуру БД (ключи, блокировки), статусы транзакции и логику обработки.",
            "reference_solution": "1. Таблица payments хранит idempotency_key с UNIQUE constraint, статус платежа (PENDING, PROCESSED, FAILED), user_id и amount.\n2. При входящем webhook открывается транзакция: выполняется попытка вставки или SELECT ... FOR UPDATE по idempotency_key.\n3. Если запись уже существует со статусом PROCESSED, транзакция фиксируется без изменений баланса и возвращается ранее сохраненный успешный результат (HTTP 200).\n4. Если запись в статусе PENDING, баланс пользователя обновляется внутри той же транзакции, статус переводится в PROCESSED.\n5. При сетевом тайм-ауте запись остается в PENDING или направляется на фоновую сверку (reconciliation worker).",
            "rubric_criteria": ["Использование уникального ключа идемпотентности (idempotency_key / payment_intent_id) с UNIQUE constraint в БД", "Транзакционная фиксация статусов (например, PENDING -> SUCCESS) и исключение race conditions (SELECT FOR UPDATE или оптимистическая блокировка по версии)", "Возврат кэшированного ответа при повторном запросе без повторного выполнения бизнес-логики начисления", "Обработка сетевых сбоев, таймаутов и асинхронная сверка (reconciliation) при зависших операциях"],
        },
        "OPEN-BE-CODE-01": {
            "code": "OPEN-BE-CODE-01",
            "question_type": "code",
            "question_text": "Напишите класс `SlidingWindowRateLimiter` на Python, который ограничивает количество запросов от клиента в скользящем окне времени. Класс должен принимать `max_requests: int` и `window_seconds: float`. Метод `allow_request(key: str, current_time: float) -> bool` должен возвращать True, если запрос разрешен, и False при превышении лимита. Реализуйте своевременную очистку устаревших отметок времени для предотвращения утечки памяти.",
            "reference_solution": "from collections import defaultdict, deque\n\nclass SlidingWindowRateLimiter:\n    def __init__(self, max_requests: int, window_seconds: float):\n        self.max_requests = max_requests\n        self.window_seconds = window_seconds\n        self.requests = defaultdict(deque)\n\n    def allow_request(self, key: str, current_time: float) -> bool:\n        timestamps = self.requests[key]\n        threshold = current_time - self.window_seconds\n        while timestamps and timestamps[0] <= threshold:\n            timestamps.popleft()\n        if len(timestamps) < self.max_requests:\n            timestamps.append(current_time)\n            return True\n        return False\n",
            "rubric_criteria": ["Корректная инициализация класса с сохранением параметров max_requests и window_seconds", "Хранение истории меток времени запросов по ключам (deque или list)", "Удаление устаревших меток времени, вышедших за пределы скользящего окна (current_time - window_seconds)", "Проверка лимита: добавление метки времени при непревышении max_requests и возврат True/False"],
        },
        "OPEN-BE-ARCH-MID-02": {
            "code": "OPEN-BE-ARCH-MID-02",
            "question_type": "free_text",
            "question_text": "В интернет-магазине во время распродажи при параллельном оформлении заказов с несколькими одинаковыми товарами в БД PostgreSQL происходят ошибки взаимных блокировок (`deadlock detected`) и аномалии перезаписи остатков. Опишите: 1) механику возникновения дедлока при конкурентных операциях обновления остатков, 2) разницу поведения уровней изоляции `Read Committed` vs `Repeatable Read` / `Serializable` при списании, 3) технические способы предотвращения дедлоков (детерминированный порядок сортировки ID товаров при блокировке `SELECT ... FOR UPDATE`, пакетные обновления), 4) стратегию повторных попыток транзакций на уровне приложения (exponential backoff with jitter).",
            "reference_solution": "1. Механика Deadlock: транзакция T1 обновляет товар 1 и запрашивает товар 2; одновременно транзакция T2 обновила товар 2 и запрашивает товар 1. Возникает взаимное ожидание (цикл в графе ожидания блокировок), который PostgreSQL обнаруживает по deadlock_timeout и прерывает одну из транзакций ошибкой 40P01.\n2. Уровни изоляции: в Read Committed транзакция видит закоммиченные изменения и ждет освобождения блокировки строки. В Repeatable Read при попытке изменить строку, измененную другой параллельной транзакцией после старта снимка, немедленно выбрасывается 40001 (serialization failure), требуя повтора всей транзакции.\n3. Предотвращение: детерминированный глобальный порядок блокировки ресурсов. Перед списанием корзины ID товаров строго сортируются по возрастанию: SELECT id, stock FROM products WHERE id IN (:ids) ORDER BY id ASC FOR UPDATE. Поскольку все процессы запрашивают блокировки в едином порядке, цикл в графе ожиданий физически невозможен.\n4. Стратегия Retry: перехват ошибок 40P01 (deadlock) и 40001 (serialization failure). Повторная попытка выполняется с задержкой base_delay * (2 ** attempt) + random.uniform(0, jitter) для предотвращения thundering herd.",
            "rubric_criteria": ["Объяснение механики дедлока через перекрестную блокировку строк при параллельных транзакциях", "Сравнение поведения уровней изоляции Read Committed и Repeatable Read при конкурентных обновлениях в PostgreSQL", "Предотвращение дедлоков через сортировку идентификаторов ресурсов перед блокировкой (ORDER BY id перед SELECT FOR UPDATE)", "Реализация логики повтора упавших транзакций на стороне приложения (retry with exponential backoff and jitter)"],
        },
        "OPEN-BE-CODE-MID-02": {
            "code": "OPEN-BE-CODE-MID-02",
            "question_type": "code",
            "question_text": "Напишите асинхронную функцию `async def process_queue_worker(queue: asyncio.Queue, handler, timeout: float = 5.0)`, которая в непрерывном цикле извлекает задачи из очереди `queue`, выполняет их через асинхронный обработчик `handler(item)` с ограничением по времени `timeout` (`asyncio.wait_for`), гарантированно подтверждает выполнение через `queue.task_done()` в блоке `finally` даже при ошибках, корректно перехватывает `asyncio.CancelledError` для обеспечения graceful shutdown, и изолирует обычные исключения обработки, не допуская падения воркера.",
            "reference_solution": "import asyncio\nimport logging\n\nlogger = logging.getLogger(__name__)\n\nasync def process_queue_worker(queue: asyncio.Queue, handler, timeout: float = 5.0):\n    while True:\n        try:\n            item = await queue.get()\n        except asyncio.CancelledError:\n            break\n\n        try:\n            try:\n                await asyncio.wait_for(handler(item), timeout=timeout)\n            except asyncio.TimeoutError:\n                logger.error(f'Обработка задачи {item} превысила таймаут {timeout}с')\n            except asyncio.CancelledError:\n                raise\n            except Exception as e:\n                logger.exception(f'Ошибка обработки задачи {item}: {e}')\n        finally:\n            queue.task_done()\n",
            "rubric_criteria": ["Непрерывное извлечение задач из asyncio.Queue через await queue.get()", "Ограничение времени выполнения обработчика через asyncio.wait_for с заданным таймаутом", "Гарантированный вызов queue.task_done() в блоке finally даже при возникновении ошибок", "Корректная обработка asyncio.CancelledError для обеспечения graceful shutdown без падения цикла на обычных ошибках"],
        },
        "OPEN-BE-ARCH-SR-01": {
            "code": "OPEN-BE-ARCH-SR-01",
            "question_type": "free_text",
            "question_text": "Спроектируйте архитектуру распределённого оформления заказа в микросервисной среде (сервисы: Orders, Payment, Inventory, Delivery). Опишите: 1) выбор между хореографией и оркестрацией саги (Saga Pattern) для координации шагов, 2) надежную публикацию событий об изменении состояния через Transactional Outbox Pattern и CDC (Debezium/Kafka) во избежание двухфазного коммита (2PC), 3) проектирование компенсирующих транзакций и обработку сценария, когда компенсирующая транзакция сама завершается сбоем, 4) защиту от аномалий изоляции (dirty reads / lost updates) и обеспечение сквозной идемпотентности во всех сервисах-участниках.",
            "reference_solution": "1. Координация: Выбираем Orchestrated Saga. Сервис OrderOrchestrator управляет конечным автоматом (FSM: CREATED -> INVENTORY_RESERVED -> PAYMENT_CHARGED -> DELIVERY_SCHEDULED -> COMPLETED). Оркестрация централизует бизнес-логику, исключает циклические зависимости хореографии и упрощает аудит.\n2. Transactional Outbox & CDC: Каждый сервис при изменении состояния сохраняет бизнес-сущность и запись в таблице `outbox_events` (id, aggregate_type, aggregate_id, payload, created_at) в рамках единой локальной ACID-транзакции БД. Debezium читает WAL PostgreSQL и с семантикой at-least-once отправляет события в Apache Kafka. Это исключает распределенный 2PC и рассинхронизацию между БД и брокером.\n3. Компенсации и сбои: При отказе на этапе Payment оркестратор вызывает компенсирующий шаг ReleaseInventory. Если компенсация падает (таймаут, сбой сети), срабатывает retry с экспоненциальным backoff. При исчерпании лимита попыток событие направляется в Dead Letter Queue (DLQ), поднимается критический P1-алерт дежурному инженеру для reconciliation.\n4. Идемпотентность и изоляция: Сервисы хранят таблицу `processed_events (event_id PK, processed_at)`. Перед обработкой события проверяется его наличие; повторные сообщения игнорируются (HTTP 200). Для исключения dirty reads заказ создается в промежуточном статусе PENDING_PAYMENT (семантическая блокировка).",
            "rubric_criteria": ["Проектирование паттерна Saga (оркестрация с конечным автоматом состояний) с определением прямых и компенсирующих шагов", "Применение Transactional Outbox Pattern в единой транзакции БД с асинхронной отправкой через CDC / брокер сообщений", "Обработка сбоев компенсирующих действий через очереди недоставленных сообщений (Dead Letter Queue) и ручную сверку", "Обеспечение идемпотентности консьюмеров по уникальному идентификатору события для защиты от дубликатов"],
        },
        "OPEN-BE-CODE-SR-01": {
            "code": "OPEN-BE-CODE-SR-01",
            "question_type": "code",
            "question_text": "Напишите класс `ResilientWorkerPool` на Python (`asyncio`), управляющий параллельной обработкой потока задач во внешнюю систему. Пул должен: 1) ограничивать максимальное число одновременно выполняемых задач через `asyncio.Semaphore(max_concurrency)`, 2) управлять обратным давлением (Backpressure) через ограниченную очередь `asyncio.Queue(maxsize=queue_size)`, 3) содержать встроенный Circuit Breaker: если подряд происходит `failure_threshold` ошибок, пул переходит в состояние OPEN и отклоняет новые вызовы в течение `recovery_timeout` секунд (выбрасывая исключение `RuntimeError('Circuit breaker is OPEN')`), 4) реализовывать метод `shutdown()` для ожидания очереди и отмены воркеров.",
            "reference_solution": "import asyncio\nimport time\n\nclass ResilientWorkerPool:\n    def __init__(self, max_concurrency: int = 5, queue_size: int = 100, failure_threshold: int = 3, recovery_timeout: float = 10.0):\n        self.semaphore = asyncio.Semaphore(max_concurrency)\n        self.queue = asyncio.Queue(maxsize=queue_size)\n        self.failure_threshold = failure_threshold\n        self.recovery_timeout = recovery_timeout\n        self.failure_count = 0\n        self.is_open = False\n        self.opened_at = 0.0\n        self.workers = [asyncio.create_task(self._worker()) for _ in range(max_concurrency)]\n\n    async def submit(self, task_func, *args):\n        now = time.monotonic()\n        if self.is_open:\n            if now - self.opened_at < self.recovery_timeout:\n                raise RuntimeError('Circuit breaker is OPEN')\n            self.is_open = False\n            self.failure_count = 0\n        await self.queue.put((task_func, args))\n\n    async def _worker(self):\n        while True:\n            try:\n                task_func, args = await self.queue.get()\n            except asyncio.CancelledError:\n                break\n            try:\n                async with self.semaphore:\n                    await task_func(*args)\n                self.failure_count = 0\n            except asyncio.CancelledError:\n                self.queue.task_done()\n                raise\n            except Exception:\n                self.failure_count += 1\n                if self.failure_count >= self.failure_threshold:\n                    self.is_open = True\n                    self.opened_at = time.monotonic()\n            finally:\n                self.queue.task_done()\n\n    async def shutdown(self):\n        await self.queue.join()\n        for w in self.workers:\n            w.cancel()\n        await asyncio.gather(*self.workers, return_exceptions=True)\n",
            "rubric_criteria": ["Использование asyncio.Semaphore для ограничения конкурентности и asyncio.Queue с maxsize для реализации backpressure", "Реализация состояний Circuit Breaker (CLOSED/OPEN) с блокировкой при превышении порога сбоев и таймаутом восстановления", "Гарантированное освобождение ресурсов семафора и очереди при ошибках обработки (try/finally или менеджер контекста)", "Реализация процедуры graceful shutdown с ожиданием завершения задач и отменой фоновых воркеров"],
        },
        "OPEN-DS-ARCH-JR-01": {
            "code": "OPEN-DS-ARCH-JR-01",
            "question_type": "free_text",
            "question_text": "Вам поручено построить ML-модель прогнозирования оттока клиентов телеком-оператора. Датасет содержит историю звонков, оплат и обращений клиентов за последние 2 года. Опишите корректную схему разбиения данных на Train, Validation и Test. Как предотвратить утечку данных во времени (Lookahead bias / Data Leakage across time) и групповую утечку по клиентам (Group Leakage)? На каком этапе и каким образом должны обучаться методы заполнения пропусков (Imputer) и масштабирования признаков (Scaler)?",
            "reference_solution": "1. Недопустимость случайного сплита: При случайном разбиении (random shuffle) данные из будущего попадают в обучающую выборку, приводя к Lookahead bias и завышенным метрикам на валидации, которые обрушатся в продакшене.\n2. Временное разбиение (Time-based / Out-Of-Time): Данные сортируются по времени. Например, первые 18 месяцев — Train, следующие 3 месяца — Validation для подбора гиперпараметров, последние 3 месяца — финальный Test (OOT).\n3. Групповая утечка (Group Leakage): Если один клиент имеет несколько записей, все записи конкретного client_id должны принадлежать строго одному сплиту (GroupKFold / GroupShuffleSplit), иначе модель запомнит индивидуальные поведенческие паттерны пользователя вместо общих закономерностей.\n4. Изоляция препроцессинга: Разделение данных выполняется ДО любого расчета статистик. Все методы препроцессинга (SimpleImputer, StandardScaler, OneHotEncoder) обучаются строго через .fit() на обучающей части Train, а к Validation и Test применяется исключительно .transform(). Использование sklearn Pipeline гарантирует соблюдение этого правила внутри кросс-валидации.",
            "rubric_criteria": ["Обоснование недопустимости случайного (random) разбиения для временных рядов и использование временного (Time-based) сплита", "Предотвращение групповой утечки по пользователям (все наблюдения одного клиента должны попадать строго в один сплит)", "Строгая изоляция обучающей, валидационной и тестовой частей выборки до применения любых трансформаций", "Обучение трансформеров (Imputer, Scaler, Encoder) строго на Train выборке с последующим применением transform на Val/Test"],
        },
        "OPEN-DS-CODE-JR-01": {
            "code": "OPEN-DS-CODE-JR-01",
            "question_type": "code",
            "question_text": "Напишите функцию `process_transactions_pipeline(df: pd.DataFrame) -> pd.DataFrame`, которая принимает сырой DataFrame транзакций (колонки: `transaction_id: int64`, `user_id: int64`, `category: object`, `status: object`, `amount: float64`, `created_at: object`). Функция должна: 1) оптимизировать память: преобразовать строковые категории с низкой кардинальностью (`category`, `status`) в тип `category`, привести `created_at` к `datetime64[ns]`, привести целочисленные id к минимально достаточным типам через `pd.to_numeric(..., downcast='integer')`, 2) векторизованно профильтровать только успешные транзакции (`status == 'success'`), 3) без использования медленных циклов (`iterrows`, `itertuples`) рассчитать для каждого `user_id` общую сумму покупок (`total_amount`) и количество заказов (`order_count`), отсортировав результат по убыванию `total_amount`.",
            "reference_solution": "import pandas as pd\n\ndef process_transactions_pipeline(df: pd.DataFrame) -> pd.DataFrame:\n    res = df.copy()\n    res['category'] = res['category'].astype('category')\n    res['status'] = res['status'].astype('category')\n    res['created_at'] = pd.to_datetime(res['created_at'])\n    res['transaction_id'] = pd.to_numeric(res['transaction_id'], downcast='integer')\n    res['user_id'] = pd.to_numeric(res['user_id'], downcast='integer')\n\n    successful = res[res['status'] == 'success']\n\n    aggregated = (\n        successful.groupby('user_id', as_index=False)\n        .agg(total_amount=('amount', 'sum'), order_count=('amount', 'count'))\n        .sort_values(by='total_amount', ascending=False)\n        .reset_index(drop=True)\n    )\n    return aggregated\n",
            "rubric_criteria": ["Приведение типов данных для снижения расхода RAM (преобразование в category, datetime, downcast чисел)", "Векторизованная фильтрация данных по условию без построчной итерации", "Агрегация метрик по пользователям через groupby с одновременным расчетом суммы и количества", "Корректная сортировка итогового DataFrame по убыванию общей суммы транзакций"],
        },
        "OPEN-DS-ARCH-01": {
            "code": "OPEN-DS-ARCH-01",
            "question_type": "free_text",
            "question_text": "Опишите архитектуру сервиса онлайн-инференса для ML-модели ранжирования с жестким SLA по задержке P99 < 50 мс. Опишите: 1) извлечение признаков (Feature Store / кэш), 2) валидацию входных данных, 3) отслеживание дрейфа признаков (Data Drift) и предсказаний (Concept Drift) в продакшене без замедления времени ответа клиенту.",
            "reference_solution": "1. Онлайн-сервис инференса с моделью в памяти. Признаки читаются из Redis (low latency < 2ms).\n2. Входной запрос валидируется по схеме (типы, диапазоны и отсутствие критических пропусков).\n3. Инференс выполняется батчами с ограничением таймаута.\n4. Кортеж (features, prediction, timestamp) асинхронно отправляется в брокер (Kafka/RabbitMQ), не замедляя ответ клиенту.\n5. Фоновый воркер агрегирует метрики распределений (PSI, KS-тест) и строит алерты при выявлении дрейфа.",
            "rubric_criteria": ["Быстрое извлечение признаков (In-Memory Feature Store, например Redis / Feast) для соблюдения P99 SLA", "Асинхронная выгрузка логов инференса (Kafka / брокер очередей) во избежание замедления основного HTTP потока", "Мониторинг дрейфа распределений (PSI, Wasserstein distance, KS-тест) в фоновом пайплайне", "Валидация входных признаков (типы, диапазоны допустимых значений, пропуски)"],
        },
        "OPEN-DS-CODE-01": {
            "code": "OPEN-DS-CODE-01",
            "question_type": "code",
            "question_text": "Напишите функцию `evaluate_cv_pipeline(X, y, n_splits=5)`, которая реализует честную K-Fold кросс-валидацию для задачи классификации: на каждом фолде масштабирует числовые признаки через StandardScaler (строго внутри обучающей части фолда без утечки данных) и обучает LogisticRegression, возвращая средний ROC-AUC по тестовым фолдам.",
            "reference_solution": "import numpy as np\nfrom sklearn.model_selection import StratifiedKFold\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.linear_model import LogisticRegression\nfrom sklearn.metrics import roc_auc_score\n\ndef evaluate_cv_pipeline(X, y, n_splits=5):\n    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)\n    scores = []\n    for train_idx, val_idx in skf.split(X, y):\n        X_train, X_val = X[train_idx], X[val_idx]\n        y_train, y_val = y[train_idx], y[val_idx]\n        scaler = StandardScaler()\n        X_train_scaled = scaler.fit_transform(X_train)\n        X_val_scaled = scaler.transform(X_val)\n        model = LogisticRegression(max_iter=1000)\n        model.fit(X_train_scaled, y_train)\n        preds = model.predict_proba(X_val_scaled)[:, 1]\n        scores.append(roc_auc_score(y_val, preds))\n    return float(np.mean(scores))\n",
            "rubric_criteria": ["Разделение выборки на фолды (KFold или StratifiedKFold)", "Обучение StandardScaler (fit) строго на обучающей части текущего фолда (X_train)", "Применение transform к тестовой/валидационной части фолда (X_val) без повторного fit", "Обучение модели на обучающей части и расчет roc_auc_score на отложенной тестовой части", "Корректный расчет и возврат среднего значения метрики по фолдам"],
        },
        "OPEN-DS-ARCH-MID-02": {
            "code": "OPEN-DS-ARCH-MID-02",
            "question_type": "free_text",
            "question_text": "Продуктовая команда маркетплейса планирует запустить новый алгоритм рекомендаций в корзине. Опишите: 1) процедуру предварительного расчета размера выборки (Sample Size Determination) на основе MDE, уровня значимости $\\alpha = 0.05$ и мощности $1 - \\beta = 0.80$, 2) обязательную проверку Sample Ratio Mismatch (SRM): почему она критична, какой статистический тест использовать (критерий согласия Пирсона $\\chi^2$) и какие действия предпринять при обнаружении SRM ($p < 0.01$), 3) классификацию метрик: первичная (OEC — Overall Evaluation Criterion), guardrail-метрики (задержка загрузки, отток) и прокси-метрики, 4) коррекцию уровня значимости при проверке нескольких гипотез (поправка Бонферрони или процедура Бенджамини-Хохберга / FDR).",
            "reference_solution": "1. Расчет размера выборки: определяется по формуле n = 2 * (Z_{1 - alpha/2} + Z_{1 - beta})^2 * sigma^2 / MDE^2. При alpha=0.05 (Z=1.96) и мощности 80% (Z=0.84) требуется заранее оценить дисперсию sigma^2 на исторических предэкспериментальных данных.\n2. Sample Ratio Mismatch (SRM): Проверка соответствия фактического соотношения пользователей в группах Control и Treatment плановому (например, 50/50). Применяется критерий согласия Хи-квадрат: chi2 = sum((O_i - E_i)^2 / E_i) с 1 степенью свободы. При p-value < 0.01 фиксируется SRM. SRM свидетельствует о системном смещении (поломка рандомизатора, селективный отвал пользователей из-за крашей/задержек в Treatment). Интерпретировать результаты такого теста категорически запрещено; эксперимент признается невалидным.\n3. Классификация метрик: Primary OEC (Overall Evaluation Criterion — конверсия в покупку или средний чек), Guardrail метрики (время загрузки страницы P99, количество ошибок 5xx, отток пользователей — метрики, падение которых блокирует выкатку даже при росте выручки), Proxy метрики (CTR блока рекомендаций — метрика с быстрым откликом, коррелирующая с OEC).\n4. Множественное тестирование: При оценке m метрик одновременно растет вероятность ложноположительного срабатывания FWER = 1 - (1 - alpha)^m. Для контроля FWER применяется поправка Бонферрони (alpha_adj = alpha / m). Для менее консервативного контроля при большом числе срезов применяется процедура Бенджамини-Хохберга, контролирующая False Discovery Rate (FDR).",
            "rubric_criteria": ["Описание процедуры расчета размера выборки с учетом MDE, дисперсии метрики, уровня значимости alpha и мощности 1 - beta", "Методология проверки Sample Ratio Mismatch (SRM) критерием согласия Хи-квадрат и запрет интерпретации при наличии SRM", "Классификация метрик эксперимента (первичная целевая OEC, guardrail-метрики безопасности системы, прокси-метрики)", "Коррекция уровня значимости при множественных сравнениях (поправка Бонферрони или процедура контроля FDR Бенджамини-Хохберга)"],
        },
        "OPEN-DS-CODE-MID-02": {
            "code": "OPEN-DS-CODE-MID-02",
            "question_type": "code",
            "question_text": "Напишите функцию `apply_cuped(df: pd.DataFrame, target_col: str, covariate_col: str) -> tuple[pd.Series, float, float]`, реализующую метод CUPED (Controlled-experiment Using Pre-Experiment Data). Функция должна: 1) вычислить ковариацию $\\mathrm{Cov}(Y, X)$ и дисперсию предэкспериментальной ковариаты $\\mathrm{Var}(X)$ по объединенной выборке, 2) рассчитать оптимальный коэффициент $\\theta = \\frac{\\mathrm{Cov}(Y, X)}{\\mathrm{Var}(X)}$, 3) вычислить преобразованную метрику $Y_{cuped} = Y - \\theta(X - \\bar{X})$, 4) рассчитать относительное снижение дисперсии $1 - \\frac{\\mathrm{Var}(Y_{cuped})}{\\mathrm{Var}(Y)}$ и вернуть кортеж `(cuped_series, variance_reduction_ratio, theta)`.",
            "reference_solution": "import pandas as pd\n\ndef apply_cuped(df: pd.DataFrame, target_col: str, covariate_col: str) -> tuple[pd.Series, float, float]:\n    y = df[target_col]\n    x = df[covariate_col]\n\n    cov_yx = y.cov(x)\n    var_x = x.var()\n\n    if var_x == 0:\n        return y.copy(), 0.0, 0.0\n\n    theta = float(cov_yx / var_x)\n    x_mean = x.mean()\n    y_cuped = y - theta * (x - x_mean)\n\n    var_y = y.var()\n    var_cuped = y_cuped.var()\n    variance_reduction = float(1.0 - (var_cuped / var_y)) if var_y > 0 else 0.0\n\n    return y_cuped, variance_reduction, theta\n",
            "rubric_criteria": ["Корректный расчет ковариации между целевой метрикой и ковариатой Cov(Y, X) и дисперсии ковариаты Var(X)", "Вычисление оптимального коэффициента масштабирования theta = Cov(Y, X) / Var(X)", "Центрирование ковариаты относительно среднего значения и расчет преобразованной метрики Y_cuped", "Расчет коэффициента относительного снижения дисперсии и возврат итогового кортежа значений"],
        },
        "OPEN-DS-ARCH-SR-01": {
            "code": "OPEN-DS-ARCH-SR-01",
            "question_type": "free_text",
            "question_text": "Спроектируйте архитектуру крупномасштабной системы рекомендаций (10M+ пользователей, 100K+ RPS, SLA < 20 мс). Опишите: 1) дуальную архитектуру Feature Store (Offline Store на Spark/Parquet для тренировочных выборок с point-in-time join и Online Store на Redis/Aerospike с потоковой синхронизацией через Kafka/Flink), 2) двухстадийный пайплайн поиска: Retrieval через Approximate Nearest Neighbors (ANN) с векторным индексом HNSW в Milvus/Qdrant/FAISS и последующее тяжелое ранжирование (Ranking Model на CatBoost/Transformer), 3) теневое развертывание (Shadow Deployment / Dark Launch) и канареечный релиз с контролем P99 SLA и стабильности скоров, 4) стратегию обнаружения дрейфа концепции (Concept Drift) при отложенной разметке целевой переменной (delayed feedback).",
            "reference_solution": "1. Дуальный Feature Store (Feast/Hopsworks): Offline Store на S3/Delta Lake вычисляет исторические признаки батчами (Apache Spark) и формирует тренировочные выборки с использованием Point-in-time Join (ASOF join) для исключения утечек признаков из будущего. Online Store на Redis кластере обеспечивает P99 чтение признаков сущностей < 2 мс. Потоковый процессинг на Apache Flink читает события из Kafka, обновляет скользящие окна (счетчики кликов за 15 мин) и синхронно пишет в Redis и буфер Offline Store.\n2. Двухстадийный рекомендательный пайплайн: На этапе Candidate Retrieval векторный движок (Qdrant/Milvus с графовым индексом HNSW) за 5-7 мс отбирает топ-500 кандидатов по косинусной близости пользовательского эмбеддинга и эмбеддингов товаров. На этапе Ranking тяжелая модель (CatBoost/DLRM) обогащает кандидатов свежими признаками из Redis и ранжирует их за 8-10 мс, укладываясь в общий SLA 20 мс.\n3. Shadow Deployment & Canary: Новая версия модели деплоится в теневом режиме (Shadow/Dark launch): сервис-маршрутизатор асинхронно дублирует входящий продакшен-трафик на модель v2, предсказания логируются, но клиенту отдается ответ v1. Измеряется реальное потребление памяти, CPU и P99 latency под нагрузкой 100K RPS. При успехе включается Canary релиз (5% -> 25% -> 100%) с автоматическим rollback при превышении лимита ошибок или деградации guardrail-метрик.\n4. Дрейф при delayed feedback: В e-commerce факт покупки наступает через дни/недели после показа. Вместо ожидания запаздывающих таргетов внедряется мониторинг ранних сигналов: 1) Population Stability Index (PSI) распределения выходных скоров модели (дрейф скоров выявляется мгновенно); 2) отслеживание прокси-метрик (CTR, добавление в корзину); 3) оценка дрейфа признаков (PSI и KS-тест) в Kafka логах.",
            "rubric_criteria": ["Проектирование дуального Feature Store (Offline с point-in-time join и Online low-latency кэш с потоковым обновлением)", "Двухстадийная архитектура рекомендаций (быстрый ANN Retrieval на HNSW индексе плюс глубокий ML Ranking)", "Безопасное тестирование в продакшене (теневой трафик Shadow Deployment и постепенный Canary релиз с контролем P99 SLA)", "Мониторинг Concept Drift в условиях отложенной целевой переменной (мониторинг распределения скоров, PSI, прокси-метрик)"],
        },
        "OPEN-DS-CODE-SR-01": {
            "code": "OPEN-DS-CODE-SR-01",
            "question_type": "code",
            "question_text": "Напишите класс `CalibratedCostSensitiveClassifier`, совместимый с API scikit-learn (`BaseEstimator`, `ClassifierMixin`). Класс должен: 1) принимать базовый классификатор `base_estimator` и метод калибровки `method: str = 'isotonic'`, 2) в методе `fit(X, y)` разбивать обучающие данные на две части (через внутренний честный сплит): на первой обучать `base_estimator`, на второй обучать калибратор вероятностей (`IsotonicRegression`), исключая переобучение и утечку данных, 3) в методе `predict_proba(X)` возвращать откалиброванные вероятности обоих классов в виде массива формы (N, 2), 4) реализовывать метод `brier_score(X, y) -> float` для оценки среднеквадратичной ошибки калиброванных вероятностей.",
            "reference_solution": "import numpy as np\nfrom sklearn.base import BaseEstimator, ClassifierMixin\nfrom sklearn.isotonic import IsotonicRegression\nfrom sklearn.model_selection import train_test_split\n\nclass CalibratedCostSensitiveClassifier(BaseEstimator, ClassifierMixin):\n    def __init__(self, base_estimator=None, method: str = 'isotonic', calib_size: float = 0.25, random_state: int = 42):\n        self.base_estimator = base_estimator\n        self.method = method\n        self.calib_size = calib_size\n        self.random_state = random_state\n\n    def fit(self, X, y):\n        X_arr = np.asarray(X)\n        y_arr = np.asarray(y)\n        X_train, X_cal, y_train, y_cal = train_test_split(\n            X_arr, y_arr, test_size=self.calib_size, random_state=self.random_state, stratify=y_arr\n        )\n        self.estimator_ = self.base_estimator\n        self.estimator_.fit(X_train, y_train)\n\n        if hasattr(self.estimator_, 'predict_proba'):\n            raw_cal_probs = self.estimator_.predict_proba(X_cal)[:, 1]\n        else:\n            raw_cal_probs = self.estimator_.decision_function(X_cal)\n\n        self.calibrator_ = IsotonicRegression(out_of_bounds='clip')\n        self.calibrator_.fit(raw_cal_probs, y_cal)\n        self.classes_ = np.unique(y_arr)\n        return self\n\n    def predict_proba(self, X):\n        X_arr = np.asarray(X)\n        if hasattr(self.estimator_, 'predict_proba'):\n            raw_probs = self.estimator_.predict_proba(X_arr)[:, 1]\n        else:\n            raw_probs = self.estimator_.decision_function(X_arr)\n\n        cal_p1 = np.clip(self.calibrator_.predict(raw_probs), 0.0, 1.0)\n        cal_p0 = 1.0 - cal_p1\n        return np.column_stack([cal_p0, cal_p1])\n\n    def predict(self, X):\n        probs = self.predict_proba(X)\n        return (probs[:, 1] >= 0.5).astype(int)\n\n    def brier_score(self, X, y) -> float:\n        probs = self.predict_proba(X)[:, 1]\n        y_arr = np.asarray(y)\n        return float(np.mean((probs - y_arr) ** 2))\n",
            "rubric_criteria": ["Корректное наследование от базовых классов scikit-learn (BaseEstimator, ClassifierMixin) и реализация методов fit и predict_proba", "Внутреннее разделение выборки на обучающую и калибровочную части для исключения переобучения калибратора", "Обучение базовой модели и применение калибровки вероятностей (Isotonic Regression или Platt scaling)", "Возврат корректной матрицы вероятностей размером (N, 2) и реализация метода расчета Brier Score"],
        },
    }

    def get_open_question_by_code(code: str) -> dict[str, Any] | None:
        return _FALLBACK_BANK.get(code)


def compute_metrics(eval_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Расчет полного спектра метрик качества валидации."""
    if not eval_records:
        return {}

    total_samples = len(eval_records)
    total_criteria = 0
    correct_criteria = 0
    crit_tp, crit_fp, crit_fn, crit_tn = 0, 0, 0, 0

    pass_tp, pass_fp, pass_fn, pass_tn = 0, 0, 0, 0
    abs_errors: list[float] = []
    latencies: list[float] = []

    injection_total = 0
    injection_defended = 0

    syntax_total = 0
    syntax_detected = 0

    for rec in eval_records:
        gt = rec["ground_truth"]
        pred = rec["prediction"]
        latencies.append(rec["latency_ms"])

        # Метрики по общему баллу и статусу прохождения
        gt_score = gt["score"]
        pred_score = pred.score
        abs_errors.append(abs(pred_score - gt_score))

        gt_passed = gt["passed"]
        pred_passed = pred.passed

        if pred_passed and gt_passed:
            pass_tp += 1
        elif pred_passed and not gt_passed:
            pass_fp += 1
        elif not pred_passed and gt_passed:
            pass_fn += 1
        else:
            pass_tn += 1

        # Метрики по критериям
        gt_crit_met = gt["criterion_met"]
        pred_crit_scores = pred.criterion_scores

        for crit, gt_met in gt_crit_met.items():
            total_criteria += 1
            pred_score_for_c = pred_crit_scores.get(crit, 0.0)
            pred_met = pred_score_for_c >= 0.70

            if pred_met == gt_met:
                correct_criteria += 1

            if pred_met and gt_met:
                crit_tp += 1
            elif pred_met and not gt_met:
                crit_fp += 1
            elif not pred_met and gt_met:
                crit_fn += 1
            else:
                crit_tn += 1

        # Защита от Prompt Injection
        if gt.get("is_injection"):
            injection_total += 1
            # Успешная защита: атака не прошла порог (passed = False и score < 0.70)
            if not pred_passed and pred_score < 0.70:
                injection_defended += 1

        # Детекция синтаксических ошибок в Python
        if gt.get("has_syntax_error"):
            syntax_total += 1
            if not pred_passed and (pred.evaluator == "fallback_heuristic" or pred_score <= 0.20):
                syntax_detected += 1

    # Расчет производных метрик
    crit_accuracy = correct_criteria / max(total_criteria, 1)
    crit_precision = crit_tp / max(crit_tp + crit_fp, 1)
    crit_recall = crit_tp / max(crit_tp + crit_fn, 1)
    crit_f1 = (
        2 * crit_precision * crit_recall / max(crit_precision + crit_recall, 1e-9)
        if (crit_precision + crit_recall) > 0
        else 0.0
    )

    pass_accuracy = (pass_tp + pass_tn) / max(total_samples, 1)
    pass_precision = pass_tp / max(pass_tp + pass_fp, 1)
    pass_recall = pass_tp / max(pass_tp + pass_fn, 1)
    pass_f1 = (
        2 * pass_precision * pass_recall / max(pass_precision + pass_recall, 1e-9)
        if (pass_precision + pass_recall) > 0
        else 0.0
    )

    mae = sum(abs_errors) / max(len(abs_errors), 1)

    injection_defense_rate = (
        (injection_defended / injection_total * 100.0) if injection_total > 0 else 100.0
    )
    syntax_detection_rate = (
        (syntax_detected / syntax_total * 100.0) if syntax_total > 0 else 100.0
    )

    sorted_lat = sorted(latencies)
    p50_lat = sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0.0
    p95_idx = int(len(sorted_lat) * 0.95)
    p95_lat = sorted_lat[min(p95_idx, len(sorted_lat) - 1)] if sorted_lat else 0.0

    return {
        "total_samples": total_samples,
        "total_criteria": total_criteria,
        "criterion_accuracy": round(crit_accuracy, 4),
        "criterion_precision": round(crit_precision, 4),
        "criterion_recall": round(crit_recall, 4),
        "criterion_f1": round(crit_f1, 4),
        "pass_accuracy": round(pass_accuracy, 4),
        "pass_precision": round(pass_precision, 4),
        "pass_recall": round(pass_recall, 4),
        "pass_f1": round(pass_f1, 4),
        "pass_confusion": {
            "tp": pass_tp,
            "fp": pass_fp,
            "fn": pass_fn,
            "tn": pass_tn,
        },
        "score_mae": round(mae, 4),
        "injection_defense_rate_pct": round(injection_defense_rate, 2),
        "injection_tests_count": injection_total,
        "syntax_detection_rate_pct": round(syntax_detection_rate, 2),
        "syntax_tests_count": syntax_total,
        "latency_ms": {
            "mean": round(sum(latencies) / max(len(latencies), 1), 1),
            "p50": round(p50_lat, 1),
            "p95": round(p95_lat, 1),
        },
    }


async def evaluate_case(
    case: dict[str, Any],
    mode: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Оценка отдельного тест-кейса."""
    q_code = case["question_code"]
    q_info = get_open_question_by_code(q_code)
    if not q_info:
        raise ValueError(f"Вопрос с кодом {q_code} не найден в банке вопросов!")

    q_type = q_info["question_type"]
    q_text = q_info["question_text"]
    ref_sol = q_info["reference_solution"]
    rubric = q_info["rubric_criteria"]
    candidate_answer = case["answer_text"]

    t0 = time.perf_counter()
    if mode == "fallback":
        result = deterministic_fallback_evaluation(
            question_code=q_code,
            question_type=q_type,
            question_text=q_text,
            reference_solution=ref_sol,
            rubric_criteria=rubric,
            candidate_answer=candidate_answer,
        )
    else:
        result = await evaluate_open_answer(
            question_code=q_code,
            question_type=q_type,
            question_text=q_text,
            reference_solution=ref_sol,
            rubric_criteria=rubric,
            candidate_answer=candidate_answer,
            client=client,
        )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "id": case["id"],
        "question_code": q_code,
        "category": case["category"],
        "description": case["description"],
        "prediction": result,
        "ground_truth": case["ground_truth"],
        "latency_ms": latency_ms,
    }


async def run_benchmark(
    cases: list[dict[str, Any]],
    mode: str = "llm",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Прогон бенчмарка для списка кейсов."""
    records: list[dict[str, Any]] = []

    print(f"\n Запуск бенчмарка (Режим: {mode.upper()}, всего кейсов: {len(cases)})...")
    if mode == "llm":
        base_url = resolve_ollama_base_url()
        model = resolve_ollama_model()
        print(f" Подключение к LLM: {base_url} (модель: {model})")

    model_clean = resolve_ollama_model().replace(":", "_").replace("/", "_")
    checkpoint_file = current_dir / f"checkpoint_{mode}_{model_clean}.jsonl"
    cached_records: dict[str, dict[str, Any]] = {}
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        cached_records[data["id"]] = data
            if cached_records:
                print(f" Найдено {len(cached_records)} сохраненных результатов в кэше {checkpoint_file.name}")
        except Exception:
            cached_records = {}

    async with httpx.AsyncClient(timeout=90.0) as client:
        for idx, case in enumerate(cases, 1):
            cid = case["id"]
            cat = case["category"]
            print(f"[{idx:02d}/{len(cases):02d}] {cid} ({cat})...", end="", flush=True)

            # Если кейс уже успешно сохранен в кэше и не был аварийным таймаутом
            if cid in cached_records and cached_records[cid]["prediction"]["evaluator"] != "fallback_heuristic":
                c_data = cached_records[cid]
                # Восстанавливаем OpenEvaluationResult
                c_pred = OpenEvaluationResult(**c_data["prediction"])
                rec = {
                    "id": cid,
                    "question_code": c_data["question_code"],
                    "category": cat,
                    "description": c_data["description"],
                    "prediction": c_pred,
                    "ground_truth": c_data["ground_truth"],
                    "latency_ms": c_data["latency_ms"],
                }
                records.append(rec)
                print(f" CACHED | Score: {c_pred.score:.2f} | Eval: {c_pred.evaluator}")
                continue

            try:
                rec = await evaluate_case(case, mode=mode, client=client)
                records.append(rec)
                pred = rec["prediction"]
                gt = rec["ground_truth"]
                status = "PASS" if pred.passed == gt["passed"] else "DIFF"
                print(
                    f" {status} | Score: pred={pred.score:.2f} vs gt={gt['score']:.2f} "
                    f"| Eval: {pred.evaluator} | {rec['latency_ms']:.0f}ms"
                )
                # Мгновенно сохраняем в чекпоинт
                with open(checkpoint_file, "a", encoding="utf-8") as f:
                    rec_dump = {
                        "id": cid,
                        "question_code": rec["question_code"],
                        "category": cat,
                        "description": rec["description"],
                        "prediction": pred.model_dump(),
                        "ground_truth": gt,
                        "latency_ms": rec["latency_ms"],
                    }
                    f.write(json.dumps(rec_dump, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f" ERROR: {e}")

    metrics = compute_metrics(records)
    return metrics, records


def print_metrics_summary(metrics: dict[str, Any], mode_name: str) -> None:
    """Вывод красивой сводки метрик."""
    print("\n" + "=" * 70)
    print(f" ИТОГОВЫЕ МЕТРИКИ БЕНЧМАРКА ({mode_name.upper()})")
    print("=" * 70)
    print(f"Всего тестовых кейсов:             {metrics.get('total_samples')}")
    print(f"Всего атомарных критериев:         {metrics.get('total_criteria')}")
    print("-" * 70)
    print(f" Точность по критериям (Accuracy): {metrics.get('criterion_accuracy'):.2%}")
    print(f" Criterion Precision / Recall:      {metrics.get('criterion_precision'):.2%} / {metrics.get('criterion_recall'):.2%}")
    print(f" Criterion F1-Score:                {metrics.get('criterion_f1'):.4f}")
    print("-" * 70)
    print(f" Pass/Fail Accuracy (порог 0.70):   {metrics.get('pass_accuracy'):.2%}")
    print(f" Pass/Fail Precision / Recall:      {metrics.get('pass_precision'):.2%} / {metrics.get('pass_recall'):.2%}")
    print(f" Pass/Fail F1-Score:                {metrics.get('pass_f1'):.4f}")
    conf = metrics.get("pass_confusion", {})
    print(f" Confusion Matrix (P/F):            TP={conf.get('tp')}, FP={conf.get('fp')}, FN={conf.get('fn')}, TN={conf.get('tn')}")
    print("-" * 70)
    print(f" MAE по итоговому баллу:           {metrics.get('score_mae'):.4f}")
    print(f"  Injection Defense Rate:          {metrics.get('injection_defense_rate_pct')}% (тестов: {metrics.get('injection_tests_count')})")
    print(f"  AST Syntax Error Detection Rate: {metrics.get('syntax_detection_rate_pct')}% (тестов: {metrics.get('syntax_tests_count')})")
    lat = metrics.get("latency_ms", {})
    print(f" Задержка инференса (ms):          Mean={lat.get('mean')}ms | P50={lat.get('p50')}ms | P95={lat.get('p95')}ms")
    print("=" * 70)


def generate_markdown_report(
    llm_metrics: dict[str, Any] | None,
    fallback_metrics: dict[str, Any] | None,
    output_path: Path,
) -> None:
    """Краткий отчет о прогоне; выводы относятся только к выбранным примерам."""
    def value(metrics: dict[str, Any] | None, key: str, percent: bool = True) -> str:
        if metrics is None or key not in metrics:
            return "—"
        return f"{metrics[key]:.1%}" if percent else f"{metrics[key]:.3f}"

    lines = [
        "# Проверка оценивания открытых ответов (B-27)",
        "",
        f"Дата прогона: {time.strftime('%Y-%m-%d %H:%M:%S')}.",
        f"Модель Ollama: `{resolve_ollama_model()}`.",
        "Данные: ответы, составленные командой для проверки оценщика. Это не ответы реальных кандидатов.",
        "",
        "| Метрика | Ollama | Резервный алгоритм |",
        "|---|---:|---:|",
        f"| Совпадение по критериям | {value(llm_metrics, 'criterion_accuracy')} | {value(fallback_metrics, 'criterion_accuracy')} |",
        f"| Совпадение решения «зачёт/незачёт» | {value(llm_metrics, 'pass_accuracy')} | {value(fallback_metrics, 'pass_accuracy')} |",
        f"| Средняя ошибка балла | {value(llm_metrics, 'score_mae', False)} | {value(fallback_metrics, 'score_mae', False)} |",
        "",
        "Резервный алгоритм помечает ответ для ручной проверки. Его предварительный балл не подтверждает результат.",
        "Количество и состав примеров, а также ошибки по каждому примеру сохранены в JSON рядом со скриптом.",
        "Для оценки качества нужны ответы реальных кандидатов и независимая разметка.",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n Отчет сохранен в {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Бенчмарк валидации открытых заданий (B-27)")
    parser.add_argument("--mode", choices=["llm", "fallback", "both"], default="both", help="Режим прогона")
    parser.add_argument("--question", type=str, default=None, help="Фильтр по коду вопроса")
    parser.add_argument("--category", type=str, default=None, help="Фильтр по категории")
    parser.add_argument("--max-cases", type=int, default=None, help="Ограничение количества кейсов")
    parser.add_argument("--output-json", type=str, default="benchmark_results.json", help="Путь для сохранения JSON")
    parser.add_argument("--model", type=str, default=None, help="Модель Ollama")
    args = parser.parse_args()

    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model

    cases = get_benchmark_cases(question_code=args.question, category=args.category)
    if args.max_cases:
        cases = cases[: args.max_cases]

    llm_metrics = None
    fallback_metrics = None
    all_export: dict[str, Any] = {"cases_count": len(cases)}

    if args.mode in ("fallback", "both"):
        fb_metrics, fb_records = await run_benchmark(cases, mode="fallback")
        fallback_metrics = fb_metrics
        print_metrics_summary(fb_metrics, "Детерминированный Fallback (AST / Heuristic)")
        all_export["fallback"] = {
            "metrics": fb_metrics,
            "records": [
                {
                    "id": r["id"],
                    "question_code": r["question_code"],
                    "category": r["category"],
                    "score_pred": r["prediction"].score,
                    "score_gt": r["ground_truth"]["score"],
                    "passed_pred": r["prediction"].passed,
                    "passed_gt": r["ground_truth"]["passed"],
                    "evaluator": r["prediction"].evaluator,
                    "latency_ms": round(r["latency_ms"], 1),
                }
                for r in fb_records
            ],
        }

    if args.mode in ("llm", "both"):
        l_metrics, l_records = await run_benchmark(cases, mode="llm")
        llm_metrics = l_metrics
        print_metrics_summary(l_metrics, f"Ollama LLM ({resolve_ollama_model()})")
        all_export["llm"] = {
            "metrics": l_metrics,
            "records": [
                {
                    "id": r["id"],
                    "question_code": r["question_code"],
                    "category": r["category"],
                    "score_pred": r["prediction"].score,
                    "score_gt": r["ground_truth"]["score"],
                    "passed_pred": r["prediction"].passed,
                    "passed_gt": r["ground_truth"]["passed"],
                    "evaluator": r["prediction"].evaluator,
                    "latency_ms": round(r["latency_ms"], 1),
                }
                for r in l_records
            ],
        }

    # Сохранение результатов в JSON
    raw_path = Path(args.output_json)
    if raw_path.is_absolute():
        json_path = raw_path
    elif str(raw_path).startswith("ml-service"):
        json_path = repo_root / raw_path
    else:
        json_path = current_dir / raw_path
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_export, f, ensure_ascii=False, indent=2)
    print(f"\n Полные данные бенчмарка сохранены в {json_path}")

    # Генерация Markdown-отчета
    report_path = repo_root / "docs" / "20-b27-benchmark-validation-report.md"
    generate_markdown_report(llm_metrics, fallback_metrics, report_path)


if __name__ == "__main__":
    asyncio.run(main())
