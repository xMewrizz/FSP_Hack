"""Недоверенный процесс: исполняет решение, но не знает ожидаемые ответы."""

import contextlib
import json
import os
import sys


def main() -> None:
    payload = json.load(sys.stdin)
    results = []
    with open(os.devnull, "w", encoding="utf-8") as sink, contextlib.redirect_stdout(sink):
        import solution

        for case in payload["cases"]:
            try:
                if payload.get("private_function_name"):
                    function = getattr(solution, payload["private_function_name"])
                    result = function(*case["args"])
                elif payload["question_code"] == "OPEN-BE-CODE-01":
                    instance = solution.SlidingWindowRateLimiter(
                        max_requests=case["max_requests"],
                        window_seconds=case["window_seconds"],
                    )
                    result = [
                        instance.allow_request(key, timestamp)
                        for key, timestamp in case["requests"]
                    ]
                elif payload["question_code"] == "OPEN-BE-CODE-JR-RE":
                    try:
                        result = solution.summarize_orders(case["orders"])
                    except ValueError:
                        result = "ValueError"
                elif payload["question_code"] == "OPEN-BE-CODE-JR-01":
                    import asyncio
                    import httpx
                    from fastapi import FastAPI

                    async def check_inventory(item_id, quantity):
                        return case["available"]

                    solution.check_inventory = check_inventory
                    app = getattr(solution, "app", None)
                    if app is None:
                        app = FastAPI()
                        app.include_router(solution.router)

                    async def exercise_endpoint():
                        async with httpx.AsyncClient(
                            transport=httpx.ASGITransport(app=app), base_url="http://candidate",
                        ) as client:
                            response = await client.post("/orders", json=case["body"])
                            body = response.json()
                            return {
                                "status": response.status_code,
                                "order_id": body.get("order_id"),
                                "result": body.get("status"),
                                "detail": body.get("detail"),
                            }

                    result = asyncio.run(exercise_endpoint())
                elif payload["question_code"] == "OPEN-BE-CODE-MID-02":
                    import asyncio

                    async def exercise_worker():
                        queue = asyncio.Queue()
                        for value in case["values"]:
                            queue.put_nowait(value)
                        seen = []

                        async def handler(value):
                            seen.append(value)
                            if value == case.get("fail_value"):
                                raise ValueError("test failure")
                            if value == case.get("slow_value"):
                                await asyncio.sleep(0.05)

                        task = asyncio.create_task(solution.process_queue_worker(queue, handler, timeout=0.01))
                        try:
                            await asyncio.wait_for(queue.join(), timeout=0.5)
                        finally:
                            task.cancel()
                            try:
                                await asyncio.wait_for(task, timeout=0.5)
                            except asyncio.CancelledError:
                                pass
                        return [seen, queue.empty()]

                    result = asyncio.run(exercise_worker())
                elif payload["question_code"] == "OPEN-BE-CODE-SR-01":
                    import asyncio

                    async def exercise_pool():
                        pool = solution.ResilientWorkerPool(
                            max_concurrency=case["max_concurrency"],
                            queue_size=case["queue_size"],
                            failure_threshold=case["failure_threshold"],
                            recovery_timeout=case["recovery_timeout"],
                        )
                        try:
                            if case["kind"] == "capacity":
                                return (isinstance(pool.queue, asyncio.Queue)
                                        and pool.queue.maxsize == case["queue_size"]
                                        and isinstance(pool.semaphore, asyncio.Semaphore))
                            if case["kind"] == "normal":
                                running = 0
                                peak = 0
                                completed = []

                                async def job(value):
                                    nonlocal running, peak
                                    running += 1
                                    peak = max(peak, running)
                                    await asyncio.sleep(0.01)
                                    completed.append(value)
                                    running -= 1

                                for value in range(5):
                                    await pool.submit(job, value)
                                await asyncio.wait_for(pool.queue.join(), timeout=0.5)
                                return sorted(completed) == list(range(5)) and peak <= case["max_concurrency"]

                            async def failing_job():
                                raise ValueError("test failure")

                            for _ in range(case["failure_threshold"]):
                                await pool.submit(failing_job)
                                await asyncio.wait_for(pool.queue.join(), timeout=0.5)
                            try:
                                await pool.submit(failing_job)
                                return False
                            except RuntimeError:
                                if case["kind"] == "breaker":
                                    return True
                            await asyncio.sleep(case["recovery_timeout"] + 0.01)
                            completed = []

                            async def recovery_job():
                                completed.append(True)

                            await pool.submit(recovery_job)
                            await asyncio.wait_for(pool.queue.join(), timeout=0.5)
                            return completed == [True]
                        finally:
                            await asyncio.wait_for(pool.shutdown(), timeout=0.5)

                    result = asyncio.run(exercise_pool())
                elif payload["question_code"] == "OPEN-DS-CODE-JR-RE":
                    import pandas as pd
                    frame = pd.DataFrame(case["rows"], columns=["client_id", "amount", "status"])
                    summary = solution.summarize_payments(frame)
                    if "client_id" not in summary.columns:
                        summary = summary.reset_index()
                    result = (
                        summary[["client_id", "payments", "total"]]
                        .sort_values("client_id").values.tolist()
                    )
                elif payload["question_code"] == "OPEN-DS-CODE-JR-01":
                    import pandas as pd
                    frame = pd.DataFrame(case["rows"], columns=[
                        "transaction_id", "user_id", "category", "status", "amount", "created_at",
                    ])
                    summary = solution.process_transactions_pipeline(frame)
                    if "user_id" not in summary.columns:
                        summary = summary.reset_index()
                    result = summary[["user_id", "total_amount", "order_count"]].values.tolist()
                elif payload["question_code"] == "OPEN-DS-CODE-MID-02":
                    import pandas as pd
                    frame = pd.DataFrame({"target": case["y"], "covariate": case["x"]})
                    adjusted, reduction, theta = solution.apply_cuped(frame, "target", "covariate")
                    result = [adjusted.tolist(), float(reduction), float(theta)]
                elif payload["question_code"] == "OPEN-DS-CODE-01":
                    import numpy as np
                    result = float(solution.evaluate_cv_pipeline(
                        np.asarray(case["X"], dtype=float), np.asarray(case["y"], dtype=int),
                        n_splits=case["n_splits"],
                    ))
                elif payload["question_code"] == "OPEN-DS-CODE-SR-01":
                    import numpy as np
                    from sklearn.linear_model import LogisticRegression
                    model = solution.CalibratedBinaryClassifier(
                        base_estimator=LogisticRegression(max_iter=200),
                    )
                    model.fit(np.asarray(case["train_x"]), np.asarray(case["train_y"]))
                    X = np.asarray(case["test_x"])
                    y = np.asarray(case["test_y"])
                    probabilities = np.asarray(model.predict_proba(X))
                    brier = float(model.brier_score(X, y))
                    expected_brier = float(np.mean((probabilities[:, 1] - y) ** 2))
                    result = [
                        probabilities.shape == (len(y), 2),
                        bool(np.isfinite(probabilities).all() and (probabilities >= 0).all()
                             and (probabilities <= 1).all()),
                        bool(np.allclose(probabilities.sum(axis=1), 1.0)),
                        bool(abs(brier - expected_brier) < 1e-6 and brier < 0.15),
                    ]
                else:
                    instance = solution.LRUCache(case["capacity"])
                    result = []
                    for operation in case["operations"]:
                        if operation[0] == "put":
                            instance.put(operation[1], operation[2])
                        else:
                            result.append(instance.get(operation[1]))
                results.append(result)
            except Exception:
                results.append({"error": "candidate_error"})
    sys.stdout.write("SANDBOX_WORKER_RESULT:" + json.dumps({"results": results}) + "\n")


if __name__ == "__main__":
    main()
