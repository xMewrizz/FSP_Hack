"""Реестр скрытых тестов (Hidden Test Suites) для задач с кодом (Task B-25).

Скрытые тесты не выдаются кандидату в публичном API и проверяются изолированным раннером.
"""

from typing import Any

# Скрытые тестовые сценарии, оформленные как исполняемый Python-код
HIDDEN_TEST_SUITES: dict[str, str] = {
    "OPEN-BE-CODE-01": '''
def test_rate_limiter_basic_allow(module):
    Limiter = getattr(module, "SlidingWindowRateLimiter", None)
    assert Limiter is not None, "Класс SlidingWindowRateLimiter не найден"
    limiter = Limiter(max_requests=3, window_seconds=10.0)
    assert limiter.allow_request("user_1", 1.0) is True
    assert limiter.allow_request("user_1", 2.0) is True
    assert limiter.allow_request("user_1", 3.0) is True

def test_rate_limiter_exceed_limit(module):
    Limiter = getattr(module, "SlidingWindowRateLimiter", None)
    limiter = Limiter(max_requests=2, window_seconds=5.0)
    assert limiter.allow_request("user_1", 1.0) is True
    assert limiter.allow_request("user_1", 2.0) is True
    assert limiter.allow_request("user_1", 3.0) is False, "Запрос сверх лимита должен возвращать False"

def test_rate_limiter_window_slide(module):
    Limiter = getattr(module, "SlidingWindowRateLimiter", None)
    limiter = Limiter(max_requests=2, window_seconds=5.0)
    assert limiter.allow_request("user_1", 1.0) is True
    assert limiter.allow_request("user_1", 2.0) is True
    assert limiter.allow_request("user_1", 3.0) is False
    # После истечения 5 секунд от t=1.0 и t=2.0 (на t=8.0 threshold = 3.0) старые запросы очищены
    assert limiter.allow_request("user_1", 8.0) is True, "После выхода за окно запросы должны быть разрешены"

def test_rate_limiter_multiple_keys_isolation(module):
    Limiter = getattr(module, "SlidingWindowRateLimiter", None)
    limiter = Limiter(max_requests=1, window_seconds=10.0)
    assert limiter.allow_request("alice", 1.0) is True
    assert limiter.allow_request("alice", 2.0) is False
    assert limiter.allow_request("bob", 2.0) is True, "Лимит одного клиента не должен блокировать другого"

def test_rate_limiter_burst_and_boundary(module):
    Limiter = getattr(module, "SlidingWindowRateLimiter", None)
    limiter = Limiter(max_requests=5, window_seconds=2.0)
    allowed_count = 0
    for i in range(10):
        if limiter.allow_request("burst", 1.0 + i * 0.1):
            allowed_count += 1
    assert allowed_count == 5, f"Ожидалось ровно 5 разрешенных запросов в пачке, получено {allowed_count}"
''',

    "OPEN-BE-CODE-02": '''
def test_lru_basic_put_and_get(module):
    Cache = getattr(module, "LRUCache", None)
    assert Cache is not None, "Класс LRUCache не найден"
    cache = Cache(2)
    cache.put("k1", 100)
    cache.put("k2", 200)
    assert cache.get("k1") == 100
    assert cache.get("k2") == 200

def test_lru_eviction(module):
    Cache = getattr(module, "LRUCache", None)
    cache = Cache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    val_a = cache.get("a")
    assert val_a == 1
    # Добавление c должно вытеснить b (так как к a обращались позже)
    cache.put("c", 3)
    res_b = cache.get("b")
    assert res_b is None or res_b == -1, f"Ключ b должен быть вытеснен из LRU, получено {res_b}"
    assert cache.get("a") == 1
    assert cache.get("c") == 3

def test_lru_update_existing_key(module):
    Cache = getattr(module, "LRUCache", None)
    cache = Cache(2)
    cache.put("x", 10)
    cache.put("x", 99)
    assert cache.get("x") == 99

def test_lru_missing_key(module):
    Cache = getattr(module, "LRUCache", None)
    cache = Cache(2)
    res = cache.get("absent_key")
    assert res is None or res == -1
''',

    "OPEN-DS-CODE-01": '''
def test_cv_pipeline_structure_and_signature(module):
    fn = getattr(module, "evaluate_cv_pipeline", None)
    assert fn is not None, "Функция evaluate_cv_pipeline не найдена"
    assert callable(fn), "evaluate_cv_pipeline должна быть вызываемой функцией"
    import inspect
    sig = inspect.signature(fn)
    assert len(sig.parameters) >= 2, "Функция должна принимать минимум аргументы X, y"

def test_cv_pipeline_execution_or_interface(module):
    fn = getattr(module, "evaluate_cv_pipeline", None)
    assert fn is not None
    import sys
    if "numpy" in sys.modules and type(sys.modules["numpy"]).__name__ != "MagicMock":
        import numpy as np
        np.random.seed(42)
        X = np.random.randn(50, 4)
        y = np.array([0] * 25 + [1] * 25)
        res = fn(X, y, n_splits=3)
        if isinstance(res, (int, float, getattr(np, "floating", float))):
            assert 0.0 <= float(res) <= 1.0
    else:
        try:
            fn([[1, 2], [3, 4]], [0, 1], n_splits=2)
        except Exception:
            pass
        assert callable(fn)
''',
}


def get_hidden_tests_for_question(question_code: str) -> str | None:
    """Возвращает исполняемый код скрытых тестов для указанного кода вопроса."""
    return HIDDEN_TEST_SUITES.get(question_code)
