"""Замер B-31 на запущенном API и PostgreSQL, без обращения к ML-сервису."""

import argparse
import asyncio
import math
import os
import time
from collections import defaultdict

import httpx


ROUTES = ("тест", "поиск", "подбор")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


async def run(base_url: str, concurrency: int, rounds: int) -> None:
    password = os.getenv("FSP_BENCH_PASSWORD", "Password123!")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        async def token(email: str) -> str:
            response = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": password},
            )
            response.raise_for_status()
            return response.json()["access_token"]

        employer_token = await token("hr@yandex-team.ru")
        candidate_token = await token("alex@fsp.ru")
        employer_headers = {"Authorization": f"Bearer {employer_token}"}
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

        needs_response = await client.get("/api/v1/needs", headers=employer_headers)
        needs_response.raise_for_status()
        needs = needs_response.json()
        need = next((item for item in needs if item["specialization"] == "Backend"), None)
        if need is None:
            raise RuntimeError("Нет демо-потребности Backend. Сначала вызовите POST /api/v1/system/seed.")

        requests = {
            "тест": ("/api/v1/testing/history", candidate_headers),
            "поиск": ("/api/v1/matching/search?specialization=Backend", employer_headers),
            "подбор": (f"/api/v1/matching/for-need/{need['id']}", employer_headers),
        }

        async def request(route: str) -> float:
            path, headers = requests[route]
            started = time.perf_counter()
            response = await client.get(path, headers=headers)
            elapsed_ms = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            return elapsed_ms

        # Прогрев соединений и кэшей не входит в замер.
        for route in ROUTES:
            await request(route)

        measurements: dict[str, list[float]] = defaultdict(list)
        for _ in range(rounds):
            batch = [ROUTES[index % len(ROUTES)] for index in range(concurrency)]
            latencies = await asyncio.gather(*(request(route) for route in batch))
            for route, elapsed_ms in zip(batch, latencies):
                measurements[route].append(elapsed_ms)

        print(f"Запущенный API: {base_url}; {concurrency} одновременных запросов x {rounds} прогона")
        print("Маршрут  Запросов  P50, мс  P95, мс  Макс., мс")
        for route in ROUTES:
            values = measurements[route]
            print(
                f"{route:<8} {len(values):>8} {percentile(values, .5):>8.1f} "
                f"{percentile(values, .95):>8.1f} {max(values):>10.1f}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if args.concurrency < 3 or args.rounds < 1:
        parser.error("Нужно не менее трёх одновременных запросов и один прогон")
    asyncio.run(run(args.base_url.rstrip("/"), args.concurrency, args.rounds))
