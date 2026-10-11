import re
import uuid
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_candidate
from app.core.database import get_db
from app.models.employer_task import TaskAttachment
from app.models.user import User
from app.schemas.candidate import (
    CandidateOnboardingRequest,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
)
from app.schemas.fsp import FSPLinkRequest
from app.services.candidate_service import candidate_service

router = APIRouter(tags=["Candidate"])

MAX_DIPLOMA_SIZE = 10 * 1024 * 1024
DIPLOMA_ATTACHMENT_PREFIX = "fsp-diploma--"


class CandidateDiplomaResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    download_url: str


def _diploma_response(attachment: TaskAttachment) -> CandidateDiplomaResponse:
    _, _, file_name = attachment.file_name.partition("--")
    _, _, file_name = file_name.partition("--")
    return CandidateDiplomaResponse(
        id=attachment.id,
        file_name=file_name,
        download_url=f"/tasks/attachments/{attachment.id}",
    )


@router.get("/olympiad-diplomas", response_model=list[CandidateDiplomaResponse])
async def list_olympiad_diplomas(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    attachments = await db.scalars(
        select(TaskAttachment)
        .where(
            TaskAttachment.owner_user_id == current_user.id,
            TaskAttachment.task_id.is_(None),
            TaskAttachment.submission_id.is_(None),
            TaskAttachment.file_name.startswith(DIPLOMA_ATTACHMENT_PREFIX),
        )
        .order_by(TaskAttachment.id)
    )
    return [_diploma_response(attachment) for attachment in attachments]


@router.post(
    "/olympiad-diplomas",
    response_model=CandidateDiplomaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_olympiad_diploma(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    raw_name = file.filename or ""
    file_name = PureWindowsPath(PurePosixPath(raw_name).name).name
    file_name = re.sub(r"[^\w.() -]", "_", file_name).strip(" .")[:200]
    if not file_name or not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Прикрепить можно только диплом в формате PDF.")

    content = await file.read(MAX_DIPLOMA_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="PDF-файл пуст.")
    if len(content) > MAX_DIPLOMA_SIZE:
        raise HTTPException(status_code=400, detail="Размер PDF не должен превышать 10 МБ.")
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(status_code=400, detail="Файл не распознан как PDF.")

    attachment = TaskAttachment(
        owner_user_id=current_user.id,
        file_name=f"{DIPLOMA_ATTACHMENT_PREFIX}{uuid.uuid4().hex}--{file_name}",
        content_type="application/pdf",
        content=content,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return _diploma_response(attachment)


@router.delete("/olympiad-diplomas/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_olympiad_diploma(
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db.scalar(
        select(TaskAttachment).where(
            TaskAttachment.id == attachment_id,
            TaskAttachment.owner_user_id == current_user.id,
            TaskAttachment.task_id.is_(None),
            TaskAttachment.submission_id.is_(None),
            TaskAttachment.file_name.startswith(DIPLOMA_ATTACHMENT_PREFIX),
        )
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Диплом не найден.")
    await db.delete(attachment)
    await db.commit()


@router.post(
    "/onboarding",
    response_model=CandidateProfileResponse,
    summary="Онбординг кандидата",
)
async def complete_onboarding(
    request: CandidateOnboardingRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.complete_onboarding(db, current_user, request)


@router.get(
    "/profile",
    response_model=CandidateProfileResponse,
    summary="Профиль кандидата",
)
async def get_my_profile(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.get_profile(db, current_user)


@router.put(
    "/profile",
    response_model=CandidateProfileResponse,
    summary="Обновление профиля кандидата",
)
async def update_my_profile(
    request: CandidateProfileUpdateRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.update_profile(db, current_user, request)


@router.post(
    "/link-fsp",
    response_model=CandidateProfileResponse,
    summary="Привязка ФСП ID",
)
async def link_fsp_id(
    request: FSPLinkRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.link_fsp_id(db, current_user, request.fsp_id)


@router.delete(
    "/link-fsp",
    response_model=CandidateProfileResponse,
    summary="Отвязать ФСП ID от профиля",
)
async def unlink_fsp_id(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await candidate_service.unlink_fsp_id(db, current_user)
