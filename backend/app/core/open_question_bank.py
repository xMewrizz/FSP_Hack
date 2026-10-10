"""Банк открытых вопросов с развернутыми ответами и критериями оценки (B-27).

Расширенная версия: Junior, Middle, Senior по специализациям Backend и Data Science.
Сверено с базовыми компетенциями B-02 и документацией.
"""

from typing import Any

OPEN_QUESTIONS: list[dict[str, Any]] = [
    # =========================================================================
    # BACKEND: JUNIOR
    # =========================================================================
    {
        "code": "OPEN-BE-ARCH-JR-01",
        "title": "Проектирование схемы реляционной БД для заказов и целостность данных",
        "specialization": "Backend",
        "grade": "junior",
        "question_type": "free_text",
        "skill": "SQL и моделирование данных",
        "question_text": (
            "Спроектируйте структуру реляционной базы данных (PostgreSQL) для интернет-магазина. "
            "Опишите таблицы `users`, `orders`, `order_items` и `products`. Укажите первичные и внешние ключи, "
            "типы данных, ограничения целостности (NOT NULL, CHECK, UNIQUE), стратегию удаления связанных записей "
            "(ON DELETE CASCADE vs RESTRICT), индексы для частых запросов выборки заказов пользователя по дате, "
            "а также подход к мягкому удалению (soft delete) и сохранению цен товаров на момент покупки."
        ),
        "acceptable_solutions": [
            "Таблица users (id PK, email VARCHAR UNIQUE NOT NULL, created_at TIMESTAMP)",
            "Таблица products (id PK, title VARCHAR NOT NULL, price NUMERIC CHECK (price > 0), stock INT CHECK (stock >= 0))",
            "Таблица orders (id PK, user_id FK users(id) ON DELETE RESTRICT, status VARCHAR, created_at TIMESTAMP, deleted_at TIMESTAMP)",
            "Таблица order_items (id PK, order_id FK orders(id) ON DELETE CASCADE, product_id FK products(id) ON DELETE RESTRICT, quantity INT CHECK (quantity > 0), price_at_purchase NUMERIC NOT NULL)",
            "Составной B-Tree индекс на orders (user_id, created_at DESC) для эффективной выборки истории",
            "Soft delete через флаг is_deleted или отметку времени deleted_at с фильтрацией в WHERE deleted_at IS NULL",
        ],
        "rubric_criteria": [
            "Описание сущностей, первичных ключей (PK) и типов данных с ограничениями целостности (NOT NULL, CHECK, UNIQUE)",
            "Определение внешних ключей (FK) с обоснованием правил удаления (ON DELETE RESTRICT для сохранения истории и транзакций)",
            "Назначение индексов под частые запросы (составной индекс по user_id и дате создания created_at)",
            "Реализация мягкого удаления (soft delete через deleted_at / is_deleted) и фиксация цены на момент покупки (price_at_purchase)",
        ],
        "reference_solution": (
            "1. Схема сущностей:\n"
            "   - users: id BIGSERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW();\n"
            "   - products: id BIGSERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, price NUMERIC(12, 2) NOT NULL CHECK (price > 0), stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0);\n"
            "   - orders: id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT, status VARCHAR(32) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), deleted_at TIMESTAMPTZ NULL;\n"
            "   - order_items: id BIGSERIAL PRIMARY KEY, order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE, product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT, quantity INT NOT NULL CHECK (quantity > 0), price_at_purchase NUMERIC(12, 2) NOT NULL CHECK (price_at_purchase > 0);\n"
            "2. Целостность и удаление: ON DELETE RESTRICT для users и products защищает от случайного удаления данных, на которые ссылаются финансовые проводки. ON DELETE CASCADE для order_items удаляет строки позиции заказа только при явном удалении самого заказа.\n"
            "3. Индексы: CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC) WHERE deleted_at IS NULL для быстрого отображения истории заказов клиента.\n"
            "4. Soft delete: deleted_at TIMESTAMPTZ NULL; при удалении проставляется NOW(), все выборки фильтруют WHERE deleted_at IS NULL.\n"
            "5. Историчность: price_at_purchase обязательно копируется в order_items в момент оформления, так как цена в products может меняться со временем."
        ),
    },
    {
        "code": "OPEN-BE-CODE-JR-01",
        "title": "Реализация REST API эндпоинта создания заказа с Pydantic-валидацией",
        "specialization": "Backend",
        "grade": "junior",
        "question_type": "code",
        "skill": "Python для Backend & HTTP API",
        "question_text": (
            "Напишите асинхронный эндпоинт на FastAPI `POST /orders` с моделью Pydantic `OrderCreate` "
            "(поля `item_id: int`, `quantity: int`, `price: float`). Поля quantity и price должны быть строго больше нуля. "
            "Эндпоинт должен проверять наличие товара через фиктивную асинхронную функцию `check_inventory(item_id: int, quantity: int) -> bool`. "
            "Если товара нет — выбрасывать `HTTPException(status_code=400, detail='Out of stock')`. "
            "При успехе возвращать словарь `{'order_id': 123, 'status': 'created'}` с явным HTTP-статусом `201 Created`."
        ),
        "acceptable_solutions": [
            "FastAPI APIRouter или FastAPI app с декоратором @router.post('/orders', status_code=status.HTTP_201_CREATED)",
            "Pydantic BaseModel с Field(gt=0) для quantity и price либо валидаторами field_validator/validator",
            "Вызов await check_inventory(order.item_id, order.quantity)",
            "Обработка отсутствия остатка через raise HTTPException(status_code=400, detail='Out of stock')",
        ],
        "rubric_criteria": [
            "Определение схемы Pydantic с валидацией положительных значений quantity и price (gt=0 или валидатор)",
            "Объявление асинхронного FastAPI эндпоинта с явным указанием статус-кода 201 (status.HTTP_201_CREATED)",
            "Асинхронный вызов проверки наличия через await check_inventory",
            "Выброс HTTPException со статусом 400 при отсутствии остатков и возврат словаря с order_id при успехе",
        ],
        "reference_solution": (
            "from fastapi import APIRouter, HTTPException, status\n"
            "from pydantic import BaseModel, Field\n\n"
            "router = APIRouter()\n\n"
            "class OrderCreate(BaseModel):\n"
            "    item_id: int\n"
            "    quantity: int = Field(gt=0, description='Количество должно быть > 0')\n"
            "    price: float = Field(gt=0.0, description='Цена должна быть > 0')\n\n"
            "async def check_inventory(item_id: int, quantity: int) -> bool:\n"
            "    return True\n\n"
            "@router.post('/orders', status_code=status.HTTP_201_CREATED)\n"
            "async def create_order(order: OrderCreate):\n"
            "    is_available = await check_inventory(order.item_id, order.quantity)\n"
            "    if not is_available:\n"
            "        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Out of stock')\n"
            "    return {'order_id': 123, 'status': 'created'}\n"
        ),
    },

    # =========================================================================
    # BACKEND: MIDDLE
    # =========================================================================
    {
        "code": "OPEN-BE-ARCH-01",
        "title": "Проектирование идемпотентного обработчика платежей",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "free_text",
        "skill": "Архитектура и надёжность сервиса",
        "question_text": (
            "Опишите архитектуру и последовательность шагов сервиса обработки платежей "
            "при получении повторных webhook-уведомлений от платежного шлюза. "
            "Как гарантировать отсутствие повторного начисления баланса при сетевых тайм-аутах "
            "и повторной доставке сообщений? Опишите структуру БД (ключи, блокировки), "
            "статусы транзакции и логику обработки."
        ),
        "acceptable_solutions": [
            "Уникальный ключ idempotency_key в таблице платежей с UNIQUE constraint",
            "Использование SELECT FOR UPDATE по ключу или оптимистическая блокировка версии",
            "Проверка статуса: если PROCESSED/SUCCESS — немедленный возврат сохраненного ответа без начисления",
            "Reconciliation worker для разрешения зависших в PENDING платежей при сетевых сбоях",
        ],
        "rubric_criteria": [
            "Использование уникального ключа идемпотентности (idempotency_key / payment_intent_id) с UNIQUE constraint в БД",
            "Транзакционная фиксация статусов (например, PENDING -> SUCCESS) и исключение race conditions (SELECT FOR UPDATE или оптимистическая блокировка по версии)",
            "Возврат кэшированного ответа при повторном запросе без повторного выполнения бизнес-логики начисления",
            "Обработка сетевых сбоев, таймаутов и асинхронная сверка (reconciliation) при зависших операциях",
        ],
        "reference_solution": (
            "1. Таблица payments хранит idempotency_key с UNIQUE constraint, статус платежа (PENDING, PROCESSED, FAILED), user_id и amount.\n"
            "2. При входящем webhook открывается транзакция: выполняется попытка вставки или SELECT ... FOR UPDATE по idempotency_key.\n"
            "3. Если запись уже существует со статусом PROCESSED, транзакция фиксируется без изменений баланса и возвращается ранее сохраненный успешный результат (HTTP 200).\n"
            "4. Если запись в статусе PENDING, баланс пользователя обновляется внутри той же транзакции, статус переводится в PROCESSED.\n"
            "5. При сетевом тайм-ауте запись остается в PENDING или направляется на фоновую сверку (reconciliation worker)."
        ),
    },
    {
        "code": "OPEN-BE-CODE-01",
        "title": "Реализация скользящего ограничителя запросов (Sliding Window Rate Limiter)",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "code",
        "skill": "Python для Backend и алгоритмы",
        "question_text": (
            "Напишите класс `SlidingWindowRateLimiter` на Python, который ограничивает количество запросов "
            "от клиента в скользящем окне времени. Класс должен принимать `max_requests: int` и `window_seconds: float`. "
            "Метод `allow_request(key: str, current_time: float) -> bool` должен возвращать True, если запрос разрешен, "
            "и False при превышении лимита. Реализуйте своевременную очистку устаревших отметок времени для предотвращения "
            "утечки памяти."
        ),
        "acceptable_solutions": [
            "Хранение временных меток в collections.deque внутри dict/defaultdict по ключам",
            "Очистка меток, меньших чем current_time - window_seconds, через popleft() в цикле",
            "Проверка длины очереди: если len < max_requests, добавляем current_time и возвращаем True",
        ],
        "rubric_criteria": [
            "Корректная инициализация класса с сохранением параметров max_requests и window_seconds",
            "Хранение истории меток времени запросов по ключам (deque или list)",
            "Удаление устаревших меток времени, вышедших за пределы скользящего окна (current_time - window_seconds)",
            "Проверка лимита: добавление метки времени при непревышении max_requests и возврат True/False",
        ],
        "reference_solution": (
            "from collections import defaultdict, deque\n\n"
            "class SlidingWindowRateLimiter:\n"
            "    def __init__(self, max_requests: int, window_seconds: float):\n"
            "        self.max_requests = max_requests\n"
            "        self.window_seconds = window_seconds\n"
            "        self.requests = defaultdict(deque)\n\n"
            "    def allow_request(self, key: str, current_time: float) -> bool:\n"
            "        timestamps = self.requests[key]\n"
            "        threshold = current_time - self.window_seconds\n"
            "        while timestamps and timestamps[0] <= threshold:\n"
            "            timestamps.popleft()\n"
            "        if len(timestamps) < self.max_requests:\n"
            "            timestamps.append(current_time)\n"
            "            return True\n"
            "        return False\n"
        ),
    },
    {
        "code": "OPEN-BE-CODE-02",
        "title": "Реализация LRU-кэша с ограничением емкости (LRU Cache)",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "code",
        "skill": "Python для Backend и структуры данных",
        "question_text": (
            "Реализуйте класс `LRUCache` на Python, принимающий параметр `capacity: int`. "
            "Класс должен содержать методы `get(key: str) -> Any` и `put(key: str, value: Any) -> None`. "
            "При превышении емкости кэша должен вытесняться наименее недавно использованный (Least Recently Used) элемент. "
            "Обе операции должны выполняться со сложностью O(1)."
        ),
        "rubric_criteria": [
            "Инициализация с заданной емкостью capacity и структурой для быстрого поиска и поддержания порядка (OrderedDict или HashMap + DoublyLinkedList)",
            "Метод get возвращает значение и обновляет приоритет использования ключа (перемещение в конец)",
            "Метод put сохраняет/обновляет значение и вытесняет самый старый элемент при превышении capacity",
            "Выполнение операций чтения и записи за константное время O(1)",
        ],
        "acceptable_solutions": [
            "OrderedDict с move_to_end и popitem(last=False)",
            "Хеш-таблица и двусвязный список с обновлением порядка за O(1)",
        ],
        "reference_solution": (
            "from collections import OrderedDict\n\n"
            "class LRUCache:\n"
            "    def __init__(self, capacity: int):\n"
            "        self.capacity = capacity\n"
            "        self.cache = OrderedDict()\n\n"
            "    def get(self, key: str):\n"
            "        if key not in self.cache:\n"
            "            return None\n"
            "        self.cache.move_to_end(key)\n"
            "        return self.cache[key]\n\n"
            "    def put(self, key: str, value: int) -> None:\n"
            "        if key in self.cache:\n"
            "            self.cache.move_to_end(key)\n"
            "        self.cache[key] = value\n"
            "        if len(self.cache) > self.capacity:\n"
            "            self.cache.popitem(last=False)\n"
        ),
    },
    {
        "code": "OPEN-BE-ARCH-MID-02",
        "title": "Разрешение Deadlocks и уровни изоляции при конкурентном списании остатков",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "free_text",
        "skill": "SQL и работа с данными (Транзакции и блокировки)",
        "question_text": (
            "В интернет-магазине во время распродажи при параллельном оформлении заказов с несколькими одинаковыми товарами "
            "в БД PostgreSQL происходят ошибки взаимных блокировок (`deadlock detected`) и аномалии перезаписи остатков. "
            "Опишите: 1) механику возникновения дедлока при конкурентных операциях обновления остатков, "
            "2) разницу поведения уровней изоляции `Read Committed` vs `Repeatable Read` / `Serializable` при списании, "
            "3) технические способы предотвращения дедлоков (детерминированный порядок сортировки ID товаров при блокировке "
            "`SELECT ... FOR UPDATE`, пакетные обновления), "
            "4) стратегию повторных попыток транзакций на уровне приложения (exponential backoff with jitter)."
        ),
        "acceptable_solutions": [
            "Объяснение циклической блокировки (Транзакция 1 блокирует товар А и ждет Б; Транзакция 2 блокирует Б и ждет А)",
            "Сравнение Read Committed (блокирует строки по мере нахождения) и Repeatable Read (выбрасывает could not serialize access upon concurrent update)",
            "Сортировка ID продуктов ORDER BY product_id перед SELECT FOR UPDATE исключает циклическое ожидание",
            "Повтор транзакции при DeadlockDetected / SerializationFailure с экспоненциальной задержкой и случайным jitter",
        ],
        "rubric_criteria": [
            "Объяснение механики дедлока через перекрестную блокировку строк при параллельных транзакциях",
            "Сравнение поведения уровней изоляции Read Committed и Repeatable Read при конкурентных обновлениях в PostgreSQL",
            "Предотвращение дедлоков через сортировку идентификаторов ресурсов перед блокировкой (ORDER BY id перед SELECT FOR UPDATE)",
            "Реализация логики повтора упавших транзакций на стороне приложения (retry with exponential backoff and jitter)",
        ],
        "reference_solution": (
            "1. Механика Deadlock: транзакция T1 обновляет товар 1 и запрашивает товар 2; одновременно транзакция T2 обновила товар 2 и запрашивает товар 1. Возникает взаимное ожидание (цикл в графе ожидания блокировок), который PostgreSQL обнаруживает по deadlock_timeout и прерывает одну из транзакций ошибкой 40P01.\n"
            "2. Уровни изоляции: в Read Committed транзакция видит закоммиченные изменения и ждет освобождения блокировки строки. В Repeatable Read при попытке изменить строку, измененную другой параллельной транзакцией после старта снимка, немедленно выбрасывается 40001 (serialization failure), требуя повтора всей транзакции.\n"
            "3. Предотвращение: детерминированный глобальный порядок блокировки ресурсов. Перед списанием корзины ID товаров строго сортируются по возрастанию: SELECT id, stock FROM products WHERE id IN (:ids) ORDER BY id ASC FOR UPDATE. Поскольку все процессы запрашивают блокировки в едином порядке, цикл в графе ожиданий физически невозможен.\n"
            "4. Стратегия Retry: перехват ошибок 40P01 (deadlock) и 40001 (serialization failure). Повторная попытка выполняется с задержкой base_delay * (2 ** attempt) + random.uniform(0, jitter) для предотвращения thundering herd."
        ),
    },
    {
        "code": "OPEN-BE-CODE-MID-02",
        "title": "Реализация асинхронного воркера очередей с graceful shutdown и таймаутами",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "code",
        "skill": "Python для Backend & Concurrency (asyncio)",
        "question_text": (
            "Напишите асинхронную функцию `async def process_queue_worker(queue: asyncio.Queue, handler, timeout: float = 5.0)`, "
            "которая в непрерывном цикле извлекает задачи из очереди `queue`, выполняет их через асинхронный обработчик `handler(item)` "
            "с ограничением по времени `timeout` (`asyncio.wait_for`), гарантированно подтверждает выполнение через `queue.task_done()` "
            "в блоке `finally` даже при ошибках, корректно перехватывает `asyncio.CancelledError` для обеспечения graceful shutdown, "
            "и изолирует обычные исключения обработки, не допуская падения воркера."
        ),
        "acceptable_solutions": [
            "Бесконечный цикл while True с await queue.get()",
            "Вызов asyncio.wait_for(handler(item), timeout=timeout)",
            "Блок try / finally с обязательным вызовом queue.task_done()",
            "Обработка asyncio.CancelledError с выходом из цикла и перехват Exception с логированием",
        ],
        "rubric_criteria": [
            "Непрерывное извлечение задач из asyncio.Queue через await queue.get()",
            "Ограничение времени выполнения обработчика через asyncio.wait_for с заданным таймаутом",
            "Гарантированный вызов queue.task_done() в блоке finally даже при возникновении ошибок",
            "Корректная обработка asyncio.CancelledError для обеспечения graceful shutdown без падения цикла на обычных ошибках",
        ],
        "reference_solution": (
            "import asyncio\n"
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n"
            "async def process_queue_worker(queue: asyncio.Queue, handler, timeout: float = 5.0):\n"
            "    while True:\n"
            "        try:\n"
            "            item = await queue.get()\n"
            "        except asyncio.CancelledError:\n"
            "            break\n\n"
            "        try:\n"
            "            try:\n"
            "                await asyncio.wait_for(handler(item), timeout=timeout)\n"
            "            except asyncio.TimeoutError:\n"
            "                logger.error(f'Обработка задачи {item} превысила таймаут {timeout}с')\n"
            "            except asyncio.CancelledError:\n"
            "                raise\n"
            "            except Exception as e:\n"
            "                logger.exception(f'Ошибка обработки задачи {item}: {e}')\n"
            "        finally:\n"
            "            queue.task_done()\n"
        ),
    },

    # =========================================================================
    # BACKEND: SENIOR
    # =========================================================================
    {
        "code": "OPEN-BE-ARCH-SR-01",
        "title": "Распределённые транзакции: Saga, Transactional Outbox и устойчивость к сбоям",
        "specialization": "Backend",
        "grade": "senior",
        "question_type": "free_text",
        "skill": "Архитектура распределенных систем и надёжность",
        "question_text": (
            "Спроектируйте архитектуру распределённого оформления заказа в микросервисной среде "
            "(сервисы: Orders, Payment, Inventory, Delivery). Опишите: 1) выбор между хореографией и оркестрацией саги (Saga Pattern) "
            "для координации шагов, 2) надежную публикацию событий об изменении состояния через Transactional Outbox Pattern и CDC "
            "(Debezium/Kafka) во избежание двухфазного коммита (2PC), 3) проектирование компенсирующих транзакций и обработку сценария, "
            "когда компенсирующая транзакция сама завершается сбоем, 4) защиту от аномалий изоляции (dirty reads / lost updates) "
            "и обеспечение сквозной идемпотентности во всех сервисах-участниках."
        ),
        "acceptable_solutions": [
            "Выбор оркестрации Saga с выделенным сервисом-координатором и конечным автоматом состояний",
            "Transactional Outbox: атомарная запись заказа и Outbox-события в единой локальной транзакции БД с отправкой через CDC",
            "Компенсирующие транзакции: отмена резерва, возврат платежа; при сбое компенсации — retry, Dead Letter Queue и ручной алерт",
            "Семантическая блокировка (статусы PENDING_PAYMENT, CANCELLED) и дедупликация событий по event_id / message_id",
        ],
        "rubric_criteria": [
            "Проектирование паттерна Saga (оркестрация с конечным автоматом состояний) с определением прямых и компенсирующих шагов",
            "Применение Transactional Outbox Pattern в единой транзакции БД с асинхронной отправкой через CDC / брокер сообщений",
            "Обработка сбоев компенсирующих действий через очереди недоставленных сообщений (Dead Letter Queue) и ручную сверку",
            "Обеспечение идемпотентности консьюмеров по уникальному идентификатору события для защиты от дубликатов",
        ],
        "reference_solution": (
            "1. Координация: Выбираем Orchestrated Saga. Сервис OrderOrchestrator управляет конечным автоматом (FSM: CREATED -> INVENTORY_RESERVED -> PAYMENT_CHARGED -> DELIVERY_SCHEDULED -> COMPLETED). Оркестрация централизует бизнес-логику, исключает циклические зависимости хореографии и упрощает аудит.\n"
            "2. Transactional Outbox & CDC: Каждый сервис при изменении состояния сохраняет бизнес-сущность и запись в таблице `outbox_events` (id, aggregate_type, aggregate_id, payload, created_at) в рамках единой локальной ACID-транзакции БД. Debezium читает WAL PostgreSQL и с семантикой at-least-once отправляет события в Apache Kafka. Это исключает распределенный 2PC и рассинхронизацию между БД и брокером.\n"
            "3. Компенсации и сбои: При отказе на этапе Payment оркестратор вызывает компенсирующий шаг ReleaseInventory. Если компенсация падает (таймаут, сбой сети), срабатывает retry с экспоненциальным backoff. При исчерпании лимита попыток событие направляется в Dead Letter Queue (DLQ), поднимается критический P1-алерт дежурному инженеру для reconciliation.\n"
            "4. Идемпотентность и изоляция: Сервисы хранят таблицу `processed_events (event_id PK, processed_at)`. Перед обработкой события проверяется его наличие; повторные сообщения игнорируются (HTTP 200). Для исключения dirty reads заказ создается в промежуточном статусе PENDING_PAYMENT (семантическая блокировка)."
        ),
    },
    {
        "code": "OPEN-BE-CODE-SR-01",
        "title": "Высоконагруженный пул асинхронных воркеров с управлением Backpressure и Circuit Breaker",
        "specialization": "Backend",
        "grade": "senior",
        "question_type": "code",
        "skill": "Python для Backend (Concurrency & High-Load Architecture)",
        "question_text": (
            "Напишите класс `ResilientWorkerPool` на Python (`asyncio`), управляющий параллельной обработкой потока задач во внешнюю систему. "
            "Пул должен: 1) ограничивать максимальное число одновременно выполняемых задач через `asyncio.Semaphore(max_concurrency)`, "
            "2) управлять обратным давлением (Backpressure) через ограниченную очередь `asyncio.Queue(maxsize=queue_size)`, "
            "3) содержать встроенный Circuit Breaker: если подряд происходит `failure_threshold` ошибок, пул переходит в состояние OPEN "
            "и отклоняет новые вызовы в течение `recovery_timeout` секунд (выбрасывая исключение `RuntimeError('Circuit breaker is OPEN')`), "
            "4) реализовывать метод `shutdown()` для ожидания очереди и отмены воркеров."
        ),
        "acceptable_solutions": [
            "Использование asyncio.Semaphore(max_concurrency) и asyncio.Queue(maxsize=queue_size)",
            "Реализация Circuit Breaker с отслеживанием sequential failures, времени перехода в OPEN и восстановлением в HALF_OPEN/CLOSED",
            "Безопасная обработка задач с освобождением слотов семафора в try/finally",
            "Метод shutdown с queue.join(), cancel воркеров и asyncio.gather",
        ],
        "rubric_criteria": [
            "Использование asyncio.Semaphore для ограничения конкурентности и asyncio.Queue с maxsize для реализации backpressure",
            "Реализация состояний Circuit Breaker (CLOSED/OPEN) с блокировкой при превышении порога сбоев и таймаутом восстановления",
            "Гарантированное освобождение ресурсов семафора и очереди при ошибках обработки (try/finally или менеджер контекста)",
            "Реализация процедуры graceful shutdown с ожиданием завершения задач и отменой фоновых воркеров",
        ],
        "reference_solution": (
            "import asyncio\n"
            "import time\n\n"
            "class ResilientWorkerPool:\n"
            "    def __init__(self, max_concurrency: int = 5, queue_size: int = 100, failure_threshold: int = 3, recovery_timeout: float = 10.0):\n"
            "        self.semaphore = asyncio.Semaphore(max_concurrency)\n"
            "        self.queue = asyncio.Queue(maxsize=queue_size)\n"
            "        self.failure_threshold = failure_threshold\n"
            "        self.recovery_timeout = recovery_timeout\n"
            "        self.failure_count = 0\n"
            "        self.is_open = False\n"
            "        self.opened_at = 0.0\n"
            "        self.workers = [asyncio.create_task(self._worker()) for _ in range(max_concurrency)]\n\n"
            "    async def submit(self, task_func, *args):\n"
            "        now = time.monotonic()\n"
            "        if self.is_open:\n"
            "            if now - self.opened_at < self.recovery_timeout:\n"
            "                raise RuntimeError('Circuit breaker is OPEN')\n"
            "            self.is_open = False\n"
            "            self.failure_count = 0\n"
            "        await self.queue.put((task_func, args))\n\n"
            "    async def _worker(self):\n"
            "        while True:\n"
            "            try:\n"
            "                task_func, args = await self.queue.get()\n"
            "            except asyncio.CancelledError:\n"
            "                break\n"
            "            try:\n"
            "                async with self.semaphore:\n"
            "                    await task_func(*args)\n"
            "                self.failure_count = 0\n"
            "            except asyncio.CancelledError:\n"
            "                self.queue.task_done()\n"
            "                raise\n"
            "            except Exception:\n"
            "                self.failure_count += 1\n"
            "                if self.failure_count >= self.failure_threshold:\n"
            "                    self.is_open = True\n"
            "                    self.opened_at = time.monotonic()\n"
            "            finally:\n"
            "                self.queue.task_done()\n\n"
            "    async def shutdown(self):\n"
            "        await self.queue.join()\n"
            "        for w in self.workers:\n"
            "            w.cancel()\n"
            "        await asyncio.gather(*self.workers, return_exceptions=True)\n"
        ),
    },

    # =========================================================================
    # DATA SCIENCE: JUNIOR
    # =========================================================================
    {
        "code": "OPEN-DS-ARCH-JR-01",
        "title": "Проектирование схемы валидации для временных и группированных данных",
        "specialization": "Data Science",
        "grade": "junior",
        "question_type": "free_text",
        "skill": "Машинное обучение и валидация данных",
        "question_text": (
            "Вам поручено построить ML-модель прогнозирования оттока клиентов телеком-оператора. "
            "Датасет содержит историю звонков, оплат и обращений клиентов за последние 2 года. "
            "Опишите корректную схему разбиения данных на Train, Validation и Test. "
            "Как предотвратить утечку данных во времени (Lookahead bias / Data Leakage across time) "
            "и групповую утечку по клиентам (Group Leakage)? На каком этапе и каким образом должны обучаться "
            "методы заполнения пропусков (Imputer) и масштабирования признаков (Scaler)?"
        ),
        "acceptable_solutions": [
            "Отказ от случайного разбиения train_test_split из-за автокорреляции и заглядывания в будущее",
            "Использование временного сплита (Time-based split / TimeSeriesSplit / Out-of-time test)",
            "Группировка по client_id (GroupKFold), чтобы данные одного пользователя не пересекались между фолдами",
            "Обучение Imputer, Scaler, Target Encoder строго на Train выборке с transform на Val и Test",
        ],
        "rubric_criteria": [
            "Обоснование недопустимости случайного (random) разбиения для временных рядов и использование временного (Time-based) сплита",
            "Предотвращение групповой утечки по пользователям (все наблюдения одного клиента должны попадать строго в один сплит)",
            "Строгая изоляция обучающей, валидационной и тестовой частей выборки до применения любых трансформаций",
            "Обучение трансформеров (Imputer, Scaler, Encoder) строго на Train выборке с последующим применением transform на Val/Test",
        ],
        "reference_solution": (
            "1. Недопустимость случайного сплита: При случайном разбиении (random shuffle) данные из будущего попадают в обучающую выборку, приводя к Lookahead bias и завышенным метрикам на валидации, которые обрушатся в продакшене.\n"
            "2. Временное разбиение (Time-based / Out-Of-Time): Данные сортируются по времени. Например, первые 18 месяцев — Train, следующие 3 месяца — Validation для подбора гиперпараметров, последние 3 месяца — финальный Test (OOT).\n"
            "3. Групповая утечка (Group Leakage): Если один клиент имеет несколько записей, все записи конкретного client_id должны принадлежать строго одному сплиту (GroupKFold / GroupShuffleSplit), иначе модель запомнит индивидуальные поведенческие паттерны пользователя вместо общих закономерностей.\n"
            "4. Изоляция препроцессинга: Разделение данных выполняется ДО любого расчета статистик. Все методы препроцессинга (SimpleImputer, StandardScaler, OneHotEncoder) обучаются строго через .fit() на обучающей части Train, а к Validation и Test применяется исключительно .transform(). Использование sklearn Pipeline гарантирует соблюдение этого правила внутри кросс-валидации."
        ),
    },
    {
        "code": "OPEN-DS-CODE-JR-01",
        "title": "Оптимизация потребления памяти и векторизованная агрегация транзакций в Pandas",
        "specialization": "Data Science",
        "grade": "junior",
        "question_type": "code",
        "skill": "Python & Data Processing (NumPy, Pandas)",
        "question_text": (
            "Напишите функцию `process_transactions_pipeline(df: pd.DataFrame) -> pd.DataFrame`, которая принимает "
            "сырой DataFrame транзакций (колонки: `transaction_id: int64`, `user_id: int64`, `category: object`, "
            "`status: object`, `amount: float64`, `created_at: object`). "
            "Функция должна: 1) оптимизировать память: преобразовать строковые категории с низкой кардинальностью "
            "(`category`, `status`) в тип `category`, привести `created_at` к `datetime64[ns]`, привести целочисленные id "
            "к минимально достаточным типам через `pd.to_numeric(..., downcast='integer')`, 2) векторизованно профильтровать "
            "только успешные транзакции (`status == 'success'`), 3) без использования медленных циклов (`iterrows`, `itertuples`) "
            "рассчитать для каждого `user_id` общую сумму покупок (`total_amount`) и количество заказов (`order_count`), "
            "отсортировав результат по убыванию `total_amount`."
        ),
        "acceptable_solutions": [
            "Преобразование df['category'].astype('category') и df['status'].astype('category')",
            "Приведение pd.to_datetime(df['created_at']) и pd.to_numeric(df['...'], downcast='integer')",
            "Векторизованная фильтрация df[df['status'] == 'success']",
            "Агрегация df.groupby('user_id').agg(total_amount=('amount', 'sum'), order_count=('amount', 'count'))",
            "Сортировка sort_values('total_amount', ascending=False)",
        ],
        "rubric_criteria": [
            "Приведение типов данных для снижения расхода RAM (преобразование в category, datetime, downcast чисел)",
            "Векторизованная фильтрация данных по условию без построчной итерации",
            "Агрегация метрик по пользователям через groupby с одновременным расчетом суммы и количества",
            "Корректная сортировка итогового DataFrame по убыванию общей суммы транзакций",
        ],
        "reference_solution": (
            "import pandas as pd\n\n"
            "def process_transactions_pipeline(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    res = df.copy()\n"
            "    res['category'] = res['category'].astype('category')\n"
            "    res['status'] = res['status'].astype('category')\n"
            "    res['created_at'] = pd.to_datetime(res['created_at'])\n"
            "    res['transaction_id'] = pd.to_numeric(res['transaction_id'], downcast='integer')\n"
            "    res['user_id'] = pd.to_numeric(res['user_id'], downcast='integer')\n\n"
            "    successful = res[res['status'] == 'success']\n\n"
            "    aggregated = (\n"
            "        successful.groupby('user_id', as_index=False)\n"
            "        .agg(total_amount=('amount', 'sum'), order_count=('amount', 'count'))\n"
            "        .sort_values(by='total_amount', ascending=False)\n"
            "        .reset_index(drop=True)\n"
            "    )\n"
            "    return aggregated\n"
        ),
    },

    # =========================================================================
    # DATA SCIENCE: MIDDLE
    # =========================================================================
    {
        "code": "OPEN-DS-ARCH-01",
        "title": "Архитектура Real-Time ML Serving и мониторинга дрейфа данных",
        "specialization": "Data Science",
        "grade": "middle",
        "question_type": "free_text",
        "skill": "MLOps и архитектура инференса",
        "question_text": (
            "Опишите архитектуру сервиса онлайн-инференса для ML-модели ранжирования "
            "с жестким SLA по задержке P99 < 50 мс. Опишите: 1) извлечение признаков (Feature Store / кэш), "
            "2) валидацию входных данных, 3) отслеживание дрейфа признаков (Data Drift) и предсказаний "
            "(Concept Drift) в продакшене без замедления времени ответа клиенту."
        ),
        "acceptable_solutions": [
            "In-Memory Feature Store (Redis / Feast) для соблюдения P99 SLA",
            "Асинхронная выгрузка логов инференса в Kafka/RabbitMQ во избежание деградации latency",
            "Мониторинг дрейфа через расчет PSI, Wasserstein distance или KS-тест в фоновом воркере",
            "Валидация схемы данных (типы, допустимые диапазоны, пропуски) на входе",
        ],
        "rubric_criteria": [
            "Быстрое извлечение признаков (In-Memory Feature Store, например Redis / Feast) для соблюдения P99 SLA",
            "Асинхронная выгрузка логов инференса (Kafka / брокер очередей) во избежание замедления основного HTTP потока",
            "Мониторинг дрейфа распределений (PSI, Wasserstein distance, KS-тест) в фоновом пайплайне",
            "Валидация входных признаков (типы, диапазоны допустимых значений, пропуски)",
        ],
        "reference_solution": (
            "1. Онлайн-сервис инференса с моделью в памяти. Признаки читаются из Redis (low latency < 2ms).\n"
            "2. Входной запрос валидируется по схеме (типы, диапазоны и отсутствие критических пропусков).\n"
            "3. Инференс выполняется батчами с ограничением таймаута.\n"
            "4. Кортеж (features, prediction, timestamp) асинхронно отправляется в брокер (Kafka/RabbitMQ), не замедляя ответ клиенту.\n"
            "5. Фоновый воркер агрегирует метрики распределений (PSI, KS-тест) и строит алерты при выявлении дрейфа."
        ),
    },
    {
        "code": "OPEN-DS-CODE-01",
        "title": "Реализация честной кросс-валидации с препроцессингом без Data Leakage",
        "specialization": "Data Science",
        "grade": "middle",
        "question_type": "code",
        "skill": "Машинное обучение и валидация",
        "question_text": (
            "Напишите функцию `evaluate_cv_pipeline(X, y, n_splits=5)`, которая реализует честную "
            "K-Fold кросс-валидацию для задачи классификации: на каждом фолде масштабирует числовые признаки "
            "через StandardScaler (строго внутри обучающей части фолда без утечки данных) и обучает LogisticRegression, "
            "возвращая средний ROC-AUC по тестовым фолдам."
        ),
        "acceptable_solutions": [
            "Разбиение через KFold или StratifiedKFold(n_splits=n_splits)",
            "scaler.fit(X_train) или fit_transform строго на тренировочном фолде",
            "scaler.transform(X_val) на валидационном фолде без повторного fit",
            "model.fit(X_train_scaled, y_train) и расчет roc_auc_score(y_val, preds)",
            "Возврат среднего значения float(np.mean(scores))",
        ],
        "rubric_criteria": [
            "Разделение выборки на фолды (KFold или StratifiedKFold)",
            "Обучение StandardScaler (fit) строго на обучающей части текущего фолда (X_train)",
            "Применение transform к тестовой/валидационной части фолда (X_val) без повторного fit",
            "Обучение модели на обучающей части и расчет roc_auc_score на отложенной тестовой части",
            "Корректный расчет и возврат среднего значения метрики по фолдам",
        ],
        "reference_solution": (
            "import numpy as np\n"
            "from sklearn.model_selection import StratifiedKFold\n"
            "from sklearn.preprocessing import StandardScaler\n"
            "from sklearn.linear_model import LogisticRegression\n"
            "from sklearn.metrics import roc_auc_score\n\n"
            "def evaluate_cv_pipeline(X, y, n_splits=5):\n"
            "    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)\n"
            "    scores = []\n"
            "    for train_idx, val_idx in skf.split(X, y):\n"
            "        X_train, X_val = X[train_idx], X[val_idx]\n"
            "        y_train, y_val = y[train_idx], y[val_idx]\n"
            "        scaler = StandardScaler()\n"
            "        X_train_scaled = scaler.fit_transform(X_train)\n"
            "        X_val_scaled = scaler.transform(X_val)\n"
            "        model = LogisticRegression(max_iter=1000)\n"
            "        model.fit(X_train_scaled, y_train)\n"
            "        preds = model.predict_proba(X_val_scaled)[:, 1]\n"
            "        scores.append(roc_auc_score(y_val, preds))\n"
            "    return float(np.mean(scores))\n"
        ),
    },
    {
        "code": "OPEN-DS-ARCH-MID-02",
        "title": "Дизайн A/B эксперимента, диагностика Sample Ratio Mismatch (SRM) и множественное тестирование",
        "specialization": "Data Science",
        "grade": "middle",
        "question_type": "free_text",
        "skill": "Статистика и A/B тестирование (SRM & Дизайн)",
        "question_text": (
            "Продуктовая команда маркетплейса планирует запустить новый алгоритм рекомендаций в корзине. "
            "Опишите: 1) процедуру предварительного расчета размера выборки (Sample Size Determination) на основе MDE, "
            "уровня значимости $\\alpha = 0.05$ и мощности $1 - \\beta = 0.80$, "
            "2) обязательную проверку Sample Ratio Mismatch (SRM): почему она критична, какой статистический тест использовать "
            "(критерий согласия Пирсона $\\chi^2$) и какие действия предпринять при обнаружении SRM ($p < 0.01$), "
            "3) классификацию метрик: первичная (OEC — Overall Evaluation Criterion), guardrail-метрики (задержка загрузки, отток) "
            "и прокси-метрики, 4) коррекцию уровня значимости при проверке нескольких гипотез (поправка Бонферрони или процедура Бенджамини-Хохберга / FDR)."
        ),
        "acceptable_solutions": [
            "Формула расчета выборки через дисперсию метрики, MDE, квантили стандартного нормального распределения Z_alpha/2 и Z_beta",
            "SRM как индикатор сбоев сплитования трафика, проверка через Chi-square goodness-of-fit test",
            "Запрет интерпретации эффектов эксперимента при наличии SRM",
            "Иерархия метрик: OEC (целевая), Guardrail (безопасность бизнеса/техническая), Proxy (быстрый отклик)",
            "Поправка Бонферрони (alpha / m) или FDR Бенджамини-Хохберга для контроля ложноположительных открытий",
        ],
        "rubric_criteria": [
            "Описание процедуры расчета размера выборки с учетом MDE, дисперсии метрики, уровня значимости alpha и мощности 1 - beta",
            "Методология проверки Sample Ratio Mismatch (SRM) критерием согласия Хи-квадрат и запрет интерпретации при наличии SRM",
            "Классификация метрик эксперимента (первичная целевая OEC, guardrail-метрики безопасности системы, прокси-метрики)",
            "Коррекция уровня значимости при множественных сравнениях (поправка Бонферрони или процедура контроля FDR Бенджамини-Хохберга)",
        ],
        "reference_solution": (
            "1. Расчет размера выборки: определяется по формуле n = 2 * (Z_{1 - alpha/2} + Z_{1 - beta})^2 * sigma^2 / MDE^2. При alpha=0.05 (Z=1.96) и мощности 80% (Z=0.84) требуется заранее оценить дисперсию sigma^2 на исторических предэкспериментальных данных.\n"
            "2. Sample Ratio Mismatch (SRM): Проверка соответствия фактического соотношения пользователей в группах Control и Treatment плановому (например, 50/50). Применяется критерий согласия Хи-квадрат: chi2 = sum((O_i - E_i)^2 / E_i) с 1 степенью свободы. При p-value < 0.01 фиксируется SRM. SRM свидетельствует о системном смещении (поломка рандомизатора, селективный отвал пользователей из-за крашей/задержек в Treatment). Интерпретировать результаты такого теста категорически запрещено; эксперимент признается невалидным.\n"
            "3. Классификация метрик: Primary OEC (Overall Evaluation Criterion — конверсия в покупку или средний чек), Guardrail метрики (время загрузки страницы P99, количество ошибок 5xx, отток пользователей — метрики, падение которых блокирует выкатку даже при росте выручки), Proxy метрики (CTR блока рекомендаций — метрика с быстрым откликом, коррелирующая с OEC).\n"
            "4. Множественное тестирование: При оценке m метрик одновременно растет вероятность ложноположительного срабатывания FWER = 1 - (1 - alpha)^m. Для контроля FWER применяется поправка Бонферрони (alpha_adj = alpha / m). Для менее консервативного контроля при большом числе срезов применяется процедура Бенджамини-Хохберга, контролирующая False Discovery Rate (FDR)."
        ),
    },
    {
        "code": "OPEN-DS-CODE-MID-02",
        "title": "Реализация метода снижения дисперсии метрик CUPED для A/B тестирования",
        "specialization": "Data Science",
        "grade": "middle",
        "question_type": "code",
        "skill": "Статистика и A/B тестирование (CUPED)",
        "question_text": (
            "Напишите функцию `apply_cuped(df: pd.DataFrame, target_col: str, covariate_col: str) -> tuple[pd.Series, float, float]`, "
            "реализующую метод CUPED (Controlled-experiment Using Pre-Experiment Data). "
            "Функция должна: 1) вычислить ковариацию $\\mathrm{Cov}(Y, X)$ и дисперсию предэкспериментальной ковариаты $\\mathrm{Var}(X)$ "
            "по объединенной выборке, 2) рассчитать оптимальный коэффициент $\\theta = \\frac{\\mathrm{Cov}(Y, X)}{\\mathrm{Var}(X)}$, "
            "3) вычислить преобразованную метрику $Y_{cuped} = Y - \\theta(X - \\bar{X})$, "
            "4) рассчитать относительное снижение дисперсии $1 - \\frac{\\mathrm{Var}(Y_{cuped})}{\\mathrm{Var}(Y)}$ "
            "и вернуть кортеж `(cuped_series, variance_reduction_ratio, theta)`."
        ),
        "acceptable_solutions": [
            "Расчет cov = df[target_col].cov(df[covariate_col]) и var_x = df[covariate_col].var()",
            "Вычисление theta = cov / var_x",
            "Расчет y_cuped = df[target_col] - theta * (df[covariate_col] - df[covariate_col].mean())",
            "Расчет variance_reduction = 1.0 - (y_cuped.var() / df[target_col].var())",
            "Возврат кортежа (y_cuped, variance_reduction, theta)",
        ],
        "rubric_criteria": [
            "Корректный расчет ковариации между целевой метрикой и ковариатой Cov(Y, X) и дисперсии ковариаты Var(X)",
            "Вычисление оптимального коэффициента масштабирования theta = Cov(Y, X) / Var(X)",
            "Центрирование ковариаты относительно среднего значения и расчет преобразованной метрики Y_cuped",
            "Расчет коэффициента относительного снижения дисперсии и возврат итогового кортежа значений",
        ],
        "reference_solution": (
            "import pandas as pd\n\n"
            "def apply_cuped(df: pd.DataFrame, target_col: str, covariate_col: str) -> tuple[pd.Series, float, float]:\n"
            "    y = df[target_col]\n"
            "    x = df[covariate_col]\n\n"
            "    cov_yx = y.cov(x)\n"
            "    var_x = x.var()\n\n"
            "    if var_x == 0:\n"
            "        return y.copy(), 0.0, 0.0\n\n"
            "    theta = float(cov_yx / var_x)\n"
            "    x_mean = x.mean()\n"
            "    y_cuped = y - theta * (x - x_mean)\n\n"
            "    var_y = y.var()\n"
            "    var_cuped = y_cuped.var()\n"
            "    variance_reduction = float(1.0 - (var_cuped / var_y)) if var_y > 0 else 0.0\n\n"
            "    return y_cuped, variance_reduction, theta\n"
        ),
    },

    # =========================================================================
    # DATA SCIENCE: SENIOR
    # =========================================================================
    {
        "code": "OPEN-DS-ARCH-SR-01",
        "title": "Архитектура Enterprise Feature Store, Vector DB (HNSW) и Shadow Deployment",
        "specialization": "Data Science",
        "grade": "senior",
        "question_type": "free_text",
        "skill": "MLOps, High-Scale Feature Store & Vector Search",
        "question_text": (
            "Спроектируйте архитектуру крупномасштабной системы рекомендаций (10M+ пользователей, 100K+ RPS, SLA < 20 мс). "
            "Опишите: 1) дуальную архитектуру Feature Store (Offline Store на Spark/Parquet для тренировочных выборок с point-in-time join "
            "и Online Store на Redis/Aerospike с потоковой синхронизацией через Kafka/Flink), "
            "2) двухстадийный пайплайн поиска: Retrieval через Approximate Nearest Neighbors (ANN) с векторным индексом HNSW "
            "в Milvus/Qdrant/FAISS и последующее тяжелое ранжирование (Ranking Model на CatBoost/Transformer), "
            "3) теневое развертывание (Shadow Deployment / Dark Launch) и канареечный релиз с контролем P99 SLA и стабильности скоров, "
            "4) стратегию обнаружения дрейфа концепции (Concept Drift) при отложенной разметке целевой переменной (delayed feedback)."
        ),
        "acceptable_solutions": [
            "Дуальный Feature Store: Offline с point-in-time time-travel join для устранения data leakage и Online Redis для чтения признаков < 2мс",
            "2-стадийный пайплайн: ANN Retrieval (HNSW индекс, cosine similarity, топ-500 кандидатов) + Ranking Model (тяжелый ML)",
            "Shadow deployment: дублирование реального трафика на новую модель без отдачи клиенту для замера P99 SLA и калибровки",
            "Мониторинг Concept Drift: отслеживание распределения скоров модели (PSI, Wasserstein) и прокси-сигналов кликов до прихода факта конверсий",
        ],
        "rubric_criteria": [
            "Проектирование дуального Feature Store (Offline с point-in-time join и Online low-latency кэш с потоковым обновлением)",
            "Двухстадийная архитектура рекомендаций (быстрый ANN Retrieval на HNSW индексе плюс глубокий ML Ranking)",
            "Безопасное тестирование в продакшене (теневой трафик Shadow Deployment и постепенный Canary релиз с контролем P99 SLA)",
            "Мониторинг Concept Drift в условиях отложенной целевой переменной (мониторинг распределения скоров, PSI, прокси-метрик)",
        ],
        "reference_solution": (
            "1. Дуальный Feature Store (Feast/Hopsworks): Offline Store на S3/Delta Lake вычисляет исторические признаки батчами (Apache Spark) и формирует тренировочные выборки с использованием Point-in-time Join (ASOF join) для исключения утечек признаков из будущего. Online Store на Redis кластере обеспечивает P99 чтение признаков сущностей < 2 мс. Потоковый процессинг на Apache Flink читает события из Kafka, обновляет скользящие окна (счетчики кликов за 15 мин) и синхронно пишет в Redis и буфер Offline Store.\n"
            "2. Двухстадийный рекомендательный пайплайн: На этапе Candidate Retrieval векторный движок (Qdrant/Milvus с графовым индексом HNSW) за 5-7 мс отбирает топ-500 кандидатов по косинусной близости пользовательского эмбеддинга и эмбеддингов товаров. На этапе Ranking тяжелая модель (CatBoost/DLRM) обогащает кандидатов свежими признаками из Redis и ранжирует их за 8-10 мс, укладываясь в общий SLA 20 мс.\n"
            "3. Shadow Deployment & Canary: Новая версия модели деплоится в теневом режиме (Shadow/Dark launch): сервис-маршрутизатор асинхронно дублирует входящий продакшен-трафик на модель v2, предсказания логируются, но клиенту отдается ответ v1. Измеряется реальное потребление памяти, CPU и P99 latency под нагрузкой 100K RPS. При успехе включается Canary релиз (5% -> 25% -> 100%) с автоматическим rollback при превышении лимита ошибок или деградации guardrail-метрик.\n"
            "4. Дрейф при delayed feedback: В e-commerce факт покупки наступает через дни/недели после показа. Вместо ожидания запаздывающих таргетов внедряется мониторинг ранних сигналов: 1) Population Stability Index (PSI) распределения выходных скоров модели (дрейф скоров выявляется мгновенно); 2) отслеживание прокси-метрик (CTR, добавление в корзину); 3) оценка дрейфа признаков (PSI и KS-тест) в Kafka логах."
        ),
    },
    {
        "code": "OPEN-DS-CODE-SR-01",
        "title": "Реализация кастомного sklearn-классификатора с калибровкой вероятностей и Brier Score",
        "specialization": "Data Science",
        "grade": "senior",
        "question_type": "code",
        "skill": "Scikit-Learn Architecture & Probability Calibration",
        "question_text": (
            "Напишите класс `CalibratedCostSensitiveClassifier`, совместимый с API scikit-learn (`BaseEstimator`, `ClassifierMixin`). "
            "Класс должен: 1) принимать базовый классификатор `base_estimator` и метод калибровки `method: str = 'isotonic'`, "
            "2) в методе `fit(X, y)` разбивать обучающие данные на две части (через внутренний честный сплит): на первой обучать `base_estimator`, "
            "на второй обучать калибратор вероятностей (`IsotonicRegression`), исключая переобучение и утечку данных, "
            "3) в методе `predict_proba(X)` возвращать откалиброванные вероятности обоих классов в виде массива формы (N, 2), "
            "4) реализовывать метод `brier_score(X, y) -> float` для оценки среднеквадратичной ошибки калиброванных вероятностей."
        ),
        "acceptable_solutions": [
            "Наследование от BaseEstimator и ClassifierMixin из sklearn.base",
            "Внутреннее честное разбиение выборки через train_test_split на подвыборку обучения и калибровки",
            "Обучение base_estimator на первой части и калибровка через IsotonicRegression на второй части",
            "Корректное формирование вероятностей predict_proba (N, 2) с суммой строк 1.0",
            "Метод brier_score, вычисляющий np.mean((probs[:, 1] - y) ** 2)",
        ],
        "rubric_criteria": [
            "Корректное наследование от базовых классов scikit-learn (BaseEstimator, ClassifierMixin) и реализация методов fit и predict_proba",
            "Внутреннее разделение выборки на обучающую и калибровочную части для исключения переобучения калибратора",
            "Обучение базовой модели и применение калибровки вероятностей (Isotonic Regression или Platt scaling)",
            "Возврат корректной матрицы вероятностей размером (N, 2) и реализация метода расчета Brier Score",
        ],
        "reference_solution": (
            "import numpy as np\n"
            "from sklearn.base import BaseEstimator, ClassifierMixin\n"
            "from sklearn.isotonic import IsotonicRegression\n"
            "from sklearn.model_selection import train_test_split\n\n"
            "class CalibratedCostSensitiveClassifier(BaseEstimator, ClassifierMixin):\n"
            "    def __init__(self, base_estimator=None, method: str = 'isotonic', calib_size: float = 0.25, random_state: int = 42):\n"
            "        self.base_estimator = base_estimator\n"
            "        self.method = method\n"
            "        self.calib_size = calib_size\n"
            "        self.random_state = random_state\n\n"
            "    def fit(self, X, y):\n"
            "        X_arr = np.asarray(X)\n"
            "        y_arr = np.asarray(y)\n"
            "        X_train, X_cal, y_train, y_cal = train_test_split(\n"
            "            X_arr, y_arr, test_size=self.calib_size, random_state=self.random_state, stratify=y_arr\n"
            "        )\n"
            "        self.estimator_ = self.base_estimator\n"
            "        self.estimator_.fit(X_train, y_train)\n\n"
            "        if hasattr(self.estimator_, 'predict_proba'):\n"
            "            raw_cal_probs = self.estimator_.predict_proba(X_cal)[:, 1]\n"
            "        else:\n"
            "            raw_cal_probs = self.estimator_.decision_function(X_cal)\n\n"
            "        self.calibrator_ = IsotonicRegression(out_of_bounds='clip')\n"
            "        self.calibrator_.fit(raw_cal_probs, y_cal)\n"
            "        self.classes_ = np.unique(y_arr)\n"
            "        return self\n\n"
            "    def predict_proba(self, X):\n"
            "        X_arr = np.asarray(X)\n"
            "        if hasattr(self.estimator_, 'predict_proba'):\n"
            "            raw_probs = self.estimator_.predict_proba(X_arr)[:, 1]\n"
            "        else:\n"
            "            raw_probs = self.estimator_.decision_function(X_arr)\n\n"
            "        cal_p1 = np.clip(self.calibrator_.predict(raw_probs), 0.0, 1.0)\n"
            "        cal_p0 = 1.0 - cal_p1\n"
            "        return np.column_stack([cal_p0, cal_p1])\n\n"
            "    def predict(self, X):\n"
            "        probs = self.predict_proba(X)\n"
            "        return (probs[:, 1] >= 0.5).astype(int)\n\n"
            "    def brier_score(self, X, y) -> float:\n"
            "        probs = self.predict_proba(X)[:, 1]\n"
            "        y_arr = np.asarray(y)\n"
            "        return float(np.mean((probs - y_arr) ** 2))\n"
        ),
    },
]


def get_open_questions(specialization: str | None = None, grade: str | None = None) -> list[dict[str, Any]]:
    questions = OPEN_QUESTIONS
    if specialization:
        questions = [q for q in questions if q["specialization"] == specialization]
    if grade:
        questions = [q for q in questions if q["grade"] == grade.lower()]
    return questions


def get_open_question_by_code(code: str) -> dict[str, Any] | None:
    for q in OPEN_QUESTIONS:
        if q["code"] == code:
            return q
    return None
