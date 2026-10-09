# B-25: Безопасная проверка задач с кодом (Изолированная песочница и скрытые тесты)

## 1. Назначение и контекст задачи

В рамках задачи **B-25** (`P1`) реализована отказоустойчивая и защищенная песочница для автоматической проверки решений задач с кодом (Backend и Data Science), содержащихся в банке платформы (`OPEN-BE-CODE-01`, `OPEN-BE-CODE-02`, `OPEN-DS-CODE-01`).

### Ключевые требования ТЗ:
1. **Изолированный запуск**: выполнение пользовательского кода в отдельном независимом подпроцессе во временной изолированной директории.
2. **Лимиты времени и ресурсов**:
   - Жесткий таймаут выполнения (Time Limit Exceeded — TLE, по умолчанию 3.0 секунды) с принудительным завершением (`process.kill()`) при бесконечных циклах (`while True`) или блокировках.
   - Ограничение размера потоков стандартного вывода и ошибок (`stdout`/`stderr` до 16 КБ) для защиты от Memory Exhaustion / исчерпания буфера.
   - Очистка окружения процесса (`env`): полное удаление чувствительных переменных среды (`DATABASE_URL`, `SECRET_KEY`, системных токенов).
3. **Статический анализ безопасности (AST Security Inspector)**:
   - Анализ абстрактного синтаксического дерева кода до запуска процесса.
   - Блокировка потенциально опасных библиотек (`os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `threading`, `multiprocessing`, `requests`, `httpx` и др.).
   - Блокировка опасных вызовов (`eval`, `exec`, `open`, `__import__`, `compile`, `input`, `globals`, `locals`).
   - Блокировка попыток побега из песочницы (sandbox escape) через интроспекцию и рефлексию (`__class__`, `__bases__`, `__subclasses__`, `__code__`, `__globals__`).
4. **Скрытые тесты (Hidden Unit Tests)**:
   - Наборы юнит-тестов, закрытых от кандидата в публичном API.
   - Проверка граничных условий, функциональной корректности и временных окон.

---

## 2. Архитектура компонентов

```
backend/app/core/code_sandbox/
├── __init__.py               # Экспорт ключевых интерфейсов
├── security.py               # AST Security Inspector (статический аудит безопасности)
├── hidden_tests.py           # Реестр скрытых юнит-тестов для задач банка
├── executor.py               # Изолированный подпроцесс, лимиты TLE и парсер отчетов
└── schemas.py                # Pydantic-модели запросов и отчетов выполнения

backend/app/services/
└── code_sandbox_service.py   # Сервисный слой и интеграция с банком открытых вопросов
```

---

## 3. Задачи с кодом и наборы скрытых тестов

### 3.1. `OPEN-BE-CODE-01`: Sliding Window Rate Limiter (Backend)
- **Класс**: `SlidingWindowRateLimiter(max_requests: int, window_seconds: float)`
- **Метод**: `allow_request(key: str, current_time: float) -> bool`
- **Скрытые тесты**:
  1. `test_rate_limiter_basic_allow`: последовательные запросы в рамках лимита.
  2. `test_rate_limiter_exceed_limit`: отсечение запросов при исчерпании лимита (`False`).
  3. `test_rate_limiter_window_slide`: очистка устаревших отметок времени и восстановление квоты после сдвига окна.
  4. `test_rate_limiter_multiple_keys_isolation`: независимость лимитов для разных идентификаторов клиентов.
  5. `test_rate_limiter_burst_and_boundary`: проверка всплесков трафика (burst) и поведения на границах окна.

### 3.2. `OPEN-BE-CODE-02`: LRU Cache (Backend)
- **Класс**: `LRUCache(capacity: int)`
- **Методы**: `get(key: str) -> Any`, `put(key: str, value: Any) -> None`
- **Скрытые тесты**:
  1. `test_lru_basic_put_and_get`: базовое сохранение и получение по ключу.
  2. `test_lru_eviction`: вытеснение наименее недавно использованного элемента при переполнении емкости.
  3. `test_lru_update_existing_key`: обновление значения существующего ключа и его приоритета.
  4. `test_lru_missing_key`: корректный возврат `None` / `-1` для отсутствующего ключа.

### 3.3. `OPEN-DS-CODE-01`: Кросс-валидация без Data Leakage (Data Science)
- **Функция**: `evaluate_cv_pipeline(X, y, n_splits=5) -> float`
- **Скрытые тесты**:
  1. `test_cv_pipeline_structure_and_signature`: валидация сигнатуры, типов и структуры функции.
  2. `test_cv_pipeline_execution_or_interface`: вычисление усредненной метрики ROC-AUC на тестовых фолдах без утечки данных.

---

## 4. API Эндпоинты

### `POST /api/v1/testing/code-sandbox/execute`
Безопасный запуск произвольного кода или решения задачи из банка в изолированной песочнице.
- **Входные данные**:
  ```json
  {
    "code": "class SlidingWindowRateLimiter: ...",
    "question_code": "OPEN-BE-CODE-01",
    "timeout_seconds": 3.0
  }
  ```
- **Ответ**:
  ```json
  {
    "status": "success",
    "is_safe": true,
    "passed": true,
    "score": 1.0,
    "tests_total": 5,
    "tests_passed": 5,
    "execution_time_ms": 42.15,
    "test_results": [
      {
        "name": "test_rate_limiter_basic_allow",
        "passed": true,
        "execution_time_ms": 1.2,
        "error_message": null
      }
    ],
    "feedback": "Скрытые тесты пройдены: 5/5 (100%). Время выполнения: 42.15 мс.",
    "evaluator": "code_sandbox_b25"
  }
  ```

### `POST /api/v1/testing/open-questions/{code}/test-run`
Предварительный прогон решения кандидата на скрытых тестах перед итоговой отправкой.

### `POST /api/v1/testing/open-questions/{code}/submit`
Итоговая сдача решения: автоматически подключает проверку песочницей для вопросов типа `code`, фиксирует балл, критерии рубрики и статус необходимости ручной проверки в БД.

---

## 5. Статусы выполнения и безопасность

| Статус | Описание | Балл | Ручная проверка |
|---|---|---|---|
| `success` | Все скрытые тесты пройдены (100%) | 1.0 | `False` (автозачет) |
| `test_failure` | Часть скрытых тестов не прошла | 0.0 .. <1.0 | `True` |
| `time_limit_exceeded` | Превышен лимит времени выполнения (>3.0 сек, бесконечный цикл) | 0.0 | `True` |
| `security_violation` | Обнаружен импорт запрещенных модулей или опасные вызовы | 0.0 | `True` |
| `syntax_error` | Синтаксическая ошибка в коде | 0.1 | `True` |
| `runtime_error` | Исключение времени выполнения (ZeroDivisionError и т.п.) | 0.0 | `True` |
