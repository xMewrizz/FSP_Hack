"""Private storage for candidate-uploaded PDF resumes."""

from pathlib import Path
import uuid

from fastapi import HTTPException

MAX_RESUME_SIZE = 10 * 1024 * 1024
RESUME_DIR = Path("media/candidate_resumes")
RESUME_DIR.mkdir(parents=True, exist_ok=True)


def save_resume_pdf(content: bytes) -> str:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(400, "Поддерживается только формат PDF")
    if len(content) > MAX_RESUME_SIZE:
        raise HTTPException(400, "Размер файла не должен превышать 10 МБ")
    filename = f"{uuid.uuid4().hex}.pdf"
    (RESUME_DIR / filename).write_bytes(content)
    return filename


def read_resume_pdf(filename: str | None) -> bytes:
    if not filename or Path(filename).name != filename or not filename.endswith(".pdf"):
        raise HTTPException(404, "Файл резюме не найден")
    path = RESUME_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Файл резюме не найден")
    return path.read_bytes()


def delete_resume_pdf(filename: str | None) -> None:
    if filename and Path(filename).name == filename:
        (RESUME_DIR / filename).unlink(missing_ok=True)
