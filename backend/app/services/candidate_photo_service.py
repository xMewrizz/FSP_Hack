import os
from pathlib import Path
import uuid
from fastapi import HTTPException

MAX_PHOTO_SIZE = 5 * 1024 * 1024

UPLOAD_DIR = Path("media/candidate_photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class CandidatePhotoService:
    def detect_format(self, content: bytes) -> tuple[str, str]:
        if len(content) < 12:
            raise HTTPException(status_code=400, detail="Файл поврежден или имеет неверный формат.")
        
        # JPEG: \xff\xd8\xff
        if content.startswith(b"\xff\xd8\xff"):
            return ".jpg", "image/jpeg"
        # PNG: \x89PNG\r\n\x1a\n
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png", "image/png"
        # WebP: RIFF....WEBP
        if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return ".webp", "image/webp"

        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только изображения форматов JPEG, PNG и WebP.",
        )

    def save(self, content: bytes, extension: str) -> str:
        filename = f"{uuid.uuid4().hex}{extension}"
        filepath = UPLOAD_DIR / filename
        filepath.write_bytes(content)
        return filename

    def delete(self, filename: str | None) -> None:
        if not filename:
            return
        filepath = UPLOAD_DIR / filename
        if filepath.is_file():
            try:
                filepath.unlink()
            except OSError:
                pass

    def read(self, filename: str | None) -> tuple[bytes, str]:
        if not filename:
            raise HTTPException(status_code=404, detail="Фотография не найдена.")
        filepath = UPLOAD_DIR / filename
        if not filepath.is_file():
            raise HTTPException(status_code=404, detail="Фотография не найдена.")
        content = filepath.read_bytes()
        _, media_type = self.detect_format(content)
        return content, media_type


candidate_photo_service = CandidatePhotoService()
