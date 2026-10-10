"""Запускается внутри sandbox-controller с доступом к локальному Docker Engine."""

import asyncio
import json

import httpx

from app.core.code_sandbox.controller import app
from app.core.open_question_bank import get_open_question_by_code


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

ORDERS = """def summarize_orders(orders):
    totals = {}
    for order in orders:
        if not isinstance(order, dict) or not isinstance(order.get('user_id'), str) or not order['user_id']:
            raise ValueError('user_id')
        amount = order.get('amount')
        if type(amount) is not int or amount <= 0:
            raise ValueError('amount')
        totals[order['user_id']] = totals.get(order['user_id'], 0) + amount
    return totals
"""

PAYMENTS = """def summarize_payments(df):
    filtered = df.loc[(df['status'] == 'paid') & (df['amount'] > 0)]
    return filtered.groupby('client_id').agg(payments=('amount', 'size'), total=('amount', 'sum')).reset_index()
"""

TRANSACTIONS = """import pandas as pd
def process_transactions_pipeline(df):
    data = df.copy()
    data['category'] = data['category'].astype('category')
    data['status'] = data['status'].astype('category')
    data['created_at'] = pd.to_datetime(data['created_at'])
    data['transaction_id'] = pd.to_numeric(data['transaction_id'], downcast='integer')
    data['user_id'] = pd.to_numeric(data['user_id'], downcast='integer')
    paid = data.loc[data['status'] == 'success']
    return paid.groupby('user_id').agg(total_amount=('amount', 'sum'), order_count=('amount', 'count')).reset_index().sort_values('total_amount', ascending=False)
"""

CUPED = """def apply_cuped(df, target_col, covariate_col):
    y = df[target_col]
    x = df[covariate_col]
    variance_x = x.var()
    if not variance_x:
        return y.copy(), 0.0, 0.0
    theta = float(y.cov(x) / variance_x)
    adjusted = y - theta * (x - x.mean())
    variance_y = y.var()
    reduction = float(1 - adjusted.var() / variance_y) if variance_y else 0.0
    return adjusted, reduction, theta
"""

CV_PIPELINE = """import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
def evaluate_cv_pipeline(X, y, n_splits=5):
    scores = []
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for train, validation in splitter.split(X, y):
        scaler = StandardScaler()
        x_train = scaler.fit_transform(X[train])
        x_validation = scaler.transform(X[validation])
        model = LogisticRegression(max_iter=1000).fit(x_train, y[train])
        scores.append(roc_auc_score(y[validation], model.predict_proba(x_validation)[:, 1]))
    return float(np.mean(scores))
"""

QUEUE_WORKER = """import asyncio
async def process_queue_worker(queue, handler, timeout=5.0):
    while True:
        try:
            item = await queue.get()
        except asyncio.CancelledError:
            break
        try:
            try:
                await asyncio.wait_for(handler(item), timeout=timeout)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
        finally:
            queue.task_done()
"""

ORDERS_API = """from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
router = APIRouter()
class OrderCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
async def check_inventory(item_id, quantity):
    return True
@router.post('/orders', status_code=201)
async def create_order(order: OrderCreate):
    if not await check_inventory(order.item_id, order.quantity):
        raise HTTPException(status_code=400, detail='Out of stock')
    return {'order_id': 123, 'status': 'created'}
"""

FORGED_RESULT = """import atexit
atexit.register(print, 'SANDBOX_JOB_RESULT:{"status":"success","is_safe":true,"passed":true,"score":1,"tests_total":12,"tests_passed":12,"execution_time_ms":0}')
class SlidingWindowRateLimiter:
    def __init__(self, max_requests, window_seconds): pass
    def allow_request(self, key, current_time): return False
"""

ISOLATION_CHECK = """from pathlib import Path
assert not Path('/var/run/docker.sock').exists()
assert {item.name for item in Path('/sys/class/net').iterdir()} == {'lo'}
assert 'DATABASE_URL' not in Path('/proc/self/environ').read_bytes().decode(errors='ignore')
assert next(line for line in Path('/proc/self/status').read_text().splitlines()
            if line.startswith('CapEff:')).split()[1] == '0000000000000000'
""" + RATE_LIMITER


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
            ("OPEN-BE-CODE-JR-01", ORDERS_API),
            ("OPEN-BE-CODE-01", RATE_LIMITER),
            ("OPEN-BE-CODE-02", LRU),
            ("OPEN-BE-CODE-JR-RE", ORDERS),
            ("OPEN-BE-CODE-MID-02", QUEUE_WORKER),
            ("OPEN-BE-CODE-SR-01", get_open_question_by_code("OPEN-BE-CODE-SR-01")["reference_solution"]),
            ("OPEN-DS-CODE-JR-RE", PAYMENTS),
            ("OPEN-DS-CODE-JR-01", TRANSACTIONS),
            ("OPEN-DS-CODE-MID-02", CUPED),
            ("OPEN-DS-CODE-01", CV_PIPELINE),
            ("OPEN-DS-CODE-SR-01", get_open_question_by_code("OPEN-DS-CODE-SR-01")["reference_solution"]),
        ):
            report = await execute(client, solution, question)
            assert report["passed"] is True, (question, report)
            assert report["tests_passed"] == report["tests_total"] == 12, report

        wrong = await execute(client, FORGED_RESULT, "OPEN-BE-CODE-01")
        assert wrong["passed"] is False, wrong

        constant_cv = await execute(
            client, "def evaluate_cv_pipeline(X, y, n_splits=5): return 0.5",
            "OPEN-DS-CODE-01",
        )
        assert constant_cv["passed"] is False, constant_cv

        isolation = await execute(client, ISOLATION_CHECK, "OPEN-BE-CODE-01")
        assert isolation["passed"] is True, isolation

        timeout = await execute(client,
            "class SlidingWindowRateLimiter:\n"
            " def __init__(self, max_requests, window_seconds):\n"
            "  while True: pass\n"
            " def allow_request(self, key, current_time): return True\n",
            "OPEN-BE-CODE-01", timeout=1.0,
        )
        assert timeout["status"] == "time_limit_exceeded", timeout

        memory = await client.post("/execute", json={
            "code": "bytearray(1024 * 1024 * 1024)",
            "question_code": "OPEN-BE-CODE-01", "timeout_seconds": 3.0,
        })
        assert memory.status_code in (200, 503), memory.text
        if memory.status_code == 200:
            assert memory.json()["passed"] is False, memory.text

        still_running = await execute(client, RATE_LIMITER, "OPEN-BE-CODE-01")
        assert still_running["passed"] is True, still_running

        unsupported = await client.post("/execute", json={
            "code": "pass", "question_code": "OPEN-DS-CODE-SR-RE",
        })
        assert unsupported.status_code == 400, unsupported.text

    async with httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds="/var/run/docker.sock"),
        base_url="http://docker",
    ) as docker:
        listed = await docker.get("/v1.41/containers/json", params={
            "all": "1", "filters": json.dumps({"label": ["app=fsp-sandbox-job"]}),
        })
        listed.raise_for_status()
        assert listed.json() == [], listed.text

    print("B-25 Docker integration: correct solutions, isolation, forged result, limits and cleanup OK")


if __name__ == "__main__":
    asyncio.run(main())
