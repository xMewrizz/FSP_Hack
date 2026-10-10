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
                if payload["question_code"] == "OPEN-BE-CODE-01":
                    instance = solution.SlidingWindowRateLimiter(
                        max_requests=case["max_requests"],
                        window_seconds=case["window_seconds"],
                    )
                    result = [
                        instance.allow_request(key, timestamp)
                        for key, timestamp in case["requests"]
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
