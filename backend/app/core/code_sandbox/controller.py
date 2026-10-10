"""Создаёт отдельный ограниченный Docker-контейнер для каждого решения."""

import asyncio
import base64
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException

from app.core.code_sandbox.run_job import SUPPORTED_QUESTIONS
from app.core.code_sandbox.schemas import SandboxExecutionRequest, SandboxExecutionResponse
from app.core.open_question_bank import get_open_question_by_code


app = FastAPI(title="FSP code runner")
logger = logging.getLogger(__name__)
DOCKER_SOCKET = "/var/run/docker.sock"
DOCKER_API = "http://docker/v1.41"
RUNNER_IMAGE = "fsp-sandbox-runner:local"
RESULT_PREFIX = "SANDBOX_JOB_RESULT:"
EXECUTABLE_QUESTIONS = SUPPORTED_QUESTIONS
MAX_CONCURRENT_JOBS = 2
job_slots = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


def container_spec(data: SandboxExecutionRequest) -> dict:
    """Ограничения задаются сервером и не зависят от полей запроса."""
    return {
        "Image": RUNNER_IMAGE,
        "Labels": {"app": "fsp-sandbox-job"},
        "Cmd": ["python", "-m", "app.core.code_sandbox.run_job"],
        "User": "0:0",
        "WorkingDir": "/app",
        "Tty": True,
        "AttachStdout": True,
        "AttachStderr": True,
        "NetworkDisabled": True,
        "Env": [
            "SANDBOX_CODE_B64=" + base64.b64encode(data.code.encode("utf-8")).decode("ascii"),
            "SANDBOX_QUESTION_CODE=" + (data.question_code or ""),
            "SANDBOX_TIMEOUT_SECONDS=" + str(data.timeout_seconds),
            "SANDBOX_CONTAINER_MODE=1",
        ],
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Memory": 512 * 1024 * 1024,
            "NanoCpus": 1_000_000_000,
            "PidsLimit": 16,
            "CapDrop": ["ALL"],
            "CapAdd": ["SETUID", "SETGID", "KILL"],
            "SecurityOpt": ["no-new-privileges"],
            "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=64m"},
            "LogConfig": {"Type": "json-file", "Config": {"max-size": "128k", "max-file": "1"}},
        },
    }


def parse_result(logs: str) -> SandboxExecutionResponse:
    for line in reversed(logs.splitlines()):
        if line.startswith(RESULT_PREFIX):
            return SandboxExecutionResponse.model_validate_json(line[len(RESULT_PREFIX):])
    raise ValueError("Исполнитель не вернул результат")


@app.post("/execute", response_model=SandboxExecutionResponse)
async def execute(data: SandboxExecutionRequest) -> SandboxExecutionResponse:
    question = get_open_question_by_code(data.question_code)
    if (not question or question["question_type"] != "code"
            or data.question_code not in EXECUTABLE_QUESTIONS):
        raise HTTPException(status_code=400, detail="Для этого задания нет проверки кода")
    if not os.path.exists(DOCKER_SOCKET):
        raise HTTPException(status_code=503, detail="Изолированный исполнитель недоступен")

    try:
        await asyncio.wait_for(job_slots.acquire(), timeout=0.5)
    except TimeoutError:
        raise HTTPException(status_code=429, detail="Исполнитель занят, повторите позже") from None
    try:
        return await _run_in_container(data)
    finally:
        job_slots.release()


async def _run_in_container(data: SandboxExecutionRequest) -> SandboxExecutionResponse:
    container_id: str | None = None
    transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
    try:
        async with httpx.AsyncClient(transport=transport, timeout=15.0) as client:
            created = await client.post(f"{DOCKER_API}/containers/create", json=container_spec(data))
            created.raise_for_status()
            container_id = created.json()["Id"]
            started = await client.post(f"{DOCKER_API}/containers/{container_id}/start")
            started.raise_for_status()
            try:
                finished = await asyncio.wait_for(
                    client.post(f"{DOCKER_API}/containers/{container_id}/wait", timeout=None),
                    timeout=data.timeout_seconds + 6,
                )
                finished.raise_for_status()
            except TimeoutError:
                await client.post(f"{DOCKER_API}/containers/{container_id}/kill")
                raise HTTPException(status_code=504, detail="Время запуска кода истекло") from None

            logs = await client.get(
                f"{DOCKER_API}/containers/{container_id}/logs",
                params={"stdout": "1", "stderr": "1"},
            )
            logs.raise_for_status()
            return parse_result(logs.text)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.exception("Не удалось получить результат контейнера %s", container_id)
        if container_id and os.getenv("SANDBOX_DEBUG") == "1":
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET), timeout=5.0,
            ) as debug_client:
                try:
                    debug_logs = await debug_client.get(
                        f"{DOCKER_API}/containers/{container_id}/logs",
                        params={"stdout": "1", "stderr": "1"},
                    )
                    logger.error("Диагностика контейнера: %s", debug_logs.text[-3000:])
                except httpx.HTTPError:
                    pass
        raise HTTPException(status_code=503, detail="Изолированный исполнитель не вернул результат") from exc
    finally:
        if container_id:
            async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET), timeout=5.0) as client:
                try:
                    await client.delete(f"{DOCKER_API}/containers/{container_id}", params={"force": "1"})
                except httpx.HTTPError:
                    pass
