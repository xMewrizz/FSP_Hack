"""Запускается внутри sandbox-controller с доступом к локальному Docker Engine."""

import asyncio

import httpx

from app.core.code_sandbox.controller import app


RATE_LIMITER = """from collections import defaultdict, deque
class SlidingWindowRateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.history = defaultdict(deque)
    def allow_request(self, key, current_time):
        entries = self.history[key]
        while entries and entries[0] <= current_time - self.window_seconds:
            entries.popleft()
        if len(entries) >= self.max_requests:
            return False
        entries.append(current_time)
        return True
"""

LRU = """from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()
    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return self.data[key]
    def put(self, key, value):
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
"""

FORGED_RESULT = """import atexit
atexit.register(print, 'SANDBOX_JOB_RESULT:{"status":"success","is_safe":true,"passed":true,"score":1,"tests_total":12,"tests_passed":12,"execution_time_ms":0}')
class SlidingWindowRateLimiter:
    def __init__(self, max_requests, window_seconds): pass
    def allow_request(self, key, current_time): return False
"""


async def execute(client: httpx.AsyncClient, code: str, question: str, timeout: float = 3.0) -> dict:
    response = await client.post("/execute", json={
        "code": code, "question_code": question, "timeout_seconds": timeout,
    })
    assert response.status_code == 200, response.text
    return response.json()


async def main() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://sandbox",
        timeout=30,
    ) as client:
        for question, solution in (
            ("OPEN-BE-CODE-01", RATE_LIMITER),
            ("OPEN-BE-CODE-02", LRU),
        ):
            report = await execute(client, solution, question)
            assert report["passed"] is True, report
            assert report["tests_passed"] == report["tests_total"] == 12, report

        wrong = await execute(client, FORGED_RESULT, "OPEN-BE-CODE-01")
        assert wrong["passed"] is False, wrong

        timeout = await execute(client,
            "class SlidingWindowRateLimiter:\n"
            " def __init__(self, max_requests, window_seconds):\n"
            "  while True: pass\n"
            " def allow_request(self, key, current_time): return True\n",
            "OPEN-BE-CODE-01", timeout=1.0,
        )
        assert timeout["status"] == "time_limit_exceeded", timeout

        unsupported = await client.post("/execute", json={
            "code": "pass", "question_code": "OPEN-DS-CODE-01",
        })
        assert unsupported.status_code == 400, unsupported.text

    print("B-25 Docker integration: 2 correct, forged result, timeout, unsupported question OK")


if __name__ == "__main__":
    asyncio.run(main())
