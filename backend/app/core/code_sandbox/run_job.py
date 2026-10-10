"""Запуск одного решения внутри ограниченного контейнера без сети и секретов."""

import base64
import os

from app.core.code_sandbox.executor import execute_in_sandbox


def main() -> None:
    code = base64.b64decode(os.environ["SANDBOX_CODE_B64"], validate=True).decode("utf-8")
    result = execute_in_sandbox(
        candidate_code=code,
        question_code=os.environ["SANDBOX_QUESTION_CODE"],
        timeout_seconds=float(os.environ["SANDBOX_TIMEOUT_SECONDS"]),
    )
    print("SANDBOX_JOB_RESULT:" + result.model_dump_json(), flush=True)


if __name__ == "__main__":
    main()
