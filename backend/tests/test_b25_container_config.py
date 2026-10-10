import json
import pytest
from pydantic import ValidationError
import httpx
from fastapi import HTTPException

from app.core.code_sandbox import controller
from app.core.code_sandbox.controller import container_spec, parse_result
from app.core.code_sandbox.schemas import SandboxExecutionRequest
from app.services import code_sandbox_service as sandbox_module


def test_each_job_has_container_limits_and_no_host_mounts():
    request = SandboxExecutionRequest(
        code="print(1)", question_code="OPEN-BE-CODE-01", timeout_seconds=3,
    )
    spec = container_spec(request)
    limits = spec["HostConfig"]
    assert spec["Labels"]["app"] == "fsp-sandbox-job"
    assert spec["NetworkDisabled"] is True
    assert spec["User"] == "0:0"
    assert limits["NetworkMode"] == "none"
    assert limits["ReadonlyRootfs"] is True
    assert limits["Memory"] <= 512 * 1024 * 1024
    assert limits["PidsLimit"] <= 16
    assert limits["CapDrop"] == ["ALL"]
    assert set(limits["CapAdd"]) == {"SETUID", "SETGID", "KILL"}
    assert "Binds" not in limits and "Mounts" not in spec
    assert all(not name.startswith(("DATABASE_URL=", "JWT_SECRET=", "OPENROUTER_API_KEY=")) for name in spec["Env"])


def test_controller_reads_only_structured_runner_result():
    report = {
        "status": "success", "is_safe": True, "passed": True, "score": 1,
        "tests_total": 1, "tests_passed": 1, "execution_time_ms": 5,
    }
    result = parse_result("candidate output\nSANDBOX_JOB_RESULT:" + json.dumps(report))
    assert result.tests_passed == 1
    assert result.passed is True


def test_request_does_not_accept_custom_tests():
    with pytest.raises(ValidationError):
        SandboxExecutionRequest.model_validate({
            "code": "pass", "question_code": "OPEN-BE-CODE-01", "custom_tests_code": "assert False",
        })


@pytest.mark.asyncio
async def test_question_without_executable_contract_is_rejected():
    with pytest.raises(HTTPException) as error:
        await controller.execute(SandboxExecutionRequest(
            code="pass",
            question_code="OPEN-DS-CODE-SR-RE",
        ))
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_controller_creates_restricted_container_and_cleans_up(monkeypatch):
    calls: list[str] = []

    def reply(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/containers/create"):
            spec = json.loads(request.content)
            assert spec["NetworkDisabled"] is True
            assert spec["HostConfig"]["ReadonlyRootfs"] is True
            return httpx.Response(201, json={"Id": "job-1"})
        if request.url.path.endswith("/start"):
            return httpx.Response(204)
        if request.url.path.endswith("/wait"):
            return httpx.Response(200, json={"StatusCode": 0})
        if request.url.path.endswith("/logs"):
            report = {"status": "success", "is_safe": True, "passed": True,
                      "score": 1, "tests_total": 1, "tests_passed": 1, "execution_time_ms": 4}
            return httpx.Response(200, text="SANDBOX_JOB_RESULT:" + json.dumps(report))
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(request.url)

    transport = httpx.MockTransport(reply)
    monkeypatch.setattr(controller.os.path, "exists", lambda _: True)
    monkeypatch.setattr(controller.httpx, "AsyncHTTPTransport", lambda **_: transport)
    result = await controller.execute(SandboxExecutionRequest(
        code="class SlidingWindowRateLimiter: pass",
        question_code="OPEN-BE-CODE-01",
    ))
    assert result.passed is True
    assert calls == [
        "POST /v1.41/containers/create",
        "POST /v1.41/containers/job-1/start",
        "POST /v1.41/containers/job-1/wait",
        "GET /v1.41/containers/job-1/logs",
        "DELETE /v1.41/containers/job-1",
    ]


@pytest.mark.asyncio
async def test_candidate_response_hides_internal_tests_and_output(monkeypatch):
    report = {
        "status": "test_failure", "is_safe": True, "passed": False, "score": 0.5,
        "tests_total": 2, "tests_passed": 1, "execution_time_ms": 5,
        "feedback": "secret detail", "stdout": "secret output",
        "test_results": [{"name": "test_secret", "passed": False}],
    }
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=report))
    original_client = httpx.AsyncClient
    monkeypatch.setattr(sandbox_module.os, "getenv", lambda key, default="": "http://runner" if key == "SANDBOX_SERVICE_URL" else default)
    monkeypatch.setattr(sandbox_module.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    result = await sandbox_module.code_sandbox_service.execute(SandboxExecutionRequest(
        code="pass", question_code="OPEN-BE-CODE-01",
    ))
    assert result.tests_passed == 1
    assert result.test_results == []
    assert result.stdout == ""
    assert result.feedback == "Пройдено проверок: 1/2"
