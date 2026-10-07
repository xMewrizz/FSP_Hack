import asyncio
import time
import tracemalloc
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_performance_and_memory_without_gpu_b31(client: AsyncClient):
    """
    Ручной замер B-31: время ответа и память при параллельных запросах.
    Используются ASGI-клиент и SQLite из conftest.py, а не сеть и PostgreSQL.
    """
    tracemalloc.start()

    # 1. Сгенерируем тестовые данные (Seed)
    seed_resp = await client.post("/api/v1/system/seed")
    assert seed_resp.status_code == 201

    # Авторизуемся под сидовым работодателем для доступа к банку кандидатов
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "hr@yandex-team.ru", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {token}"}

    # 2. Симуляция 50 параллельных запросов к эндпоинтам поиска и подбора
    concurrent_requests = 50

    async def fetch_matching_search():
        t0 = time.perf_counter()
        resp = await client.get(
            "/api/v1/matching/search",
            headers=emp_headers,
            params={"specialization": "Backend", "grade": "middle", "limit": 20},
        )
        t1 = time.perf_counter()
        assert resp.status_code == 200
        return (t1 - t0) * 1000  # ms

    async def fetch_vacancies_list():
        t0 = time.perf_counter()
        resp = await client.get("/api/v1/vacancies", params={"limit": 20})
        t1 = time.perf_counter()
        assert resp.status_code == 200
        return (t1 - t0) * 1000  # ms

    # Запускаем пачку одновременных запросов
    tasks = []
    for _ in range(concurrent_requests // 2):
        tasks.append(fetch_matching_search())
        tasks.append(fetch_vacancies_list())

    latencies = await asyncio.gather(*tasks)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mem_mb = peak_mem / (1024 * 1024)

    # Метрики задержки
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[-1]
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n--- B-31 BENCHMARK RESULTS ({concurrent_requests} concurrent requests) ---")
    print(f"Total Requests: {len(latencies)}")
    print(f"Avg Latency:    {avg_latency:.2f} ms")
    print(f"P50 Latency:    {p50:.2f} ms")
    print(f"P95 Latency:    {p95:.2f} ms")
    print(f"P99 Latency:    {p99:.2f} ms")
    print(f"Peak Memory:    {peak_mem_mb:.2f} MB")
    print("GPU Dependency: None (in-process ASGI + SQLite)")
    print("--------------------------------------------------------------------------")

    # Без GPU при 50 параллельных запросах API должен отдавать результаты быстрее 500мс
    assert p95 < 500.0, f"P95 latency {p95}ms exceeds 500ms target"
    assert peak_mem_mb < 200.0, f"Peak memory {peak_mem_mb}MB exceeds 200MB target"
