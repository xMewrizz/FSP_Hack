"""Банк открытых вопросов с развернутыми ответами и критериями оценки (B-27)."""

from typing import Any

OPEN_QUESTIONS: list[dict[str, Any]] = [
    {
        "code": "OPEN-BE-ARCH-01",
        "title": "Проектирование идемпотентного обработчика платежей",
        "specialization": "Backend",
        "grade": "middle",
        "question_type": "free_text",
        "question_text": (
            "Опишите архитектуру и последовательность шагов сервиса обработки платежей "
            "при получении повторных webhook-уведомлений от платежного шлюза. "
            "Как гарантировать отсутствие повторного начисления баланса при сетевых тайм-аутах "
            "и повторной доставке сообщений? Опишите структуру БД (ключи, блокировки), "
            "статусы транзакции и логику обработки."
        ),
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
        "question_text": (
            "Напишите класс `SlidingWindowRateLimiter` на Python, который ограничивает количество запросов "
            "от клиента в скользящем окне времени. Класс должен принимать `max_requests: int` и `window_seconds: float`. "
            "Метод `allow_request(key: str, current_time: float) -> bool` должен возвращать True, если запрос разрешен, "
            "и False при превышении лимита. Реализуйте своевременную очистку устаревших отметок времени для предотвращения "
            "утечки памяти."
        ),
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
        "code": "OPEN-DS-ARCH-01",
        "title": "Архитектура Real-Time ML Serving и мониторинга дрейфа данных",
        "specialization": "Data Science",
        "grade": "middle",
        "question_type": "free_text",
        "question_text": (
            "Опишите архитектуру сервиса онлайн-инференса для ML-модели ранжирования "
            "с жестким SLA по задержке P99 < 50 мс. Опишите: 1) извлечение признаков (Feature Store / кэш), "
            "2) валидацию входных данных, 3) отслеживание дрейфа признаков (Data Drift) и предсказаний "
            "(Concept Drift) в продакшене без замедления времени ответа клиенту."
        ),
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
        "question_text": (
            "Напишите функцию `evaluate_cv_pipeline(X, y, n_splits=5)`, которая реализует честную "
            "K-Fold кросс-валидацию для задачи классификации: на каждом фолде масштабирует числовые признаки "
            "через StandardScaler (строго внутри обучающей части фолда без утечки данных) и обучает LogisticRegression, "
            "возвращая средний ROC-AUC по тестовым фолдам."
        ),
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
]


def get_open_questions(specialization: str | None = None) -> list[dict[str, Any]]:
    if specialization:
        return [q for q in OPEN_QUESTIONS if q["specialization"] == specialization]
    return OPEN_QUESTIONS


def get_open_question_by_code(code: str) -> dict[str, Any] | None:
    for q in OPEN_QUESTIONS:
        if q["code"] == code:
            return q
    return None
