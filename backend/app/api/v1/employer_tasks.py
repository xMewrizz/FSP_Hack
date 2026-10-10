import uuid
import os
import re
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import File, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_candidate, get_current_employer, get_current_user, get_db
from app.models.employer_task import EmployerTask, EmployerTaskSubmission, TaskAttachment
from app.models.user import User
from app.schemas.employer_task import (
    CandidateActivityResponse,
    CandidateTaskResponse,
    EmployerTaskCreate,
    EmployerTaskResponse,
    EmployerTaskReviewRequest,
    EmployerTaskSubmissionCreate,
    EmployerTaskSubmissionResponse,
    EmployerTaskUpdate,
    TaskFileResponse,
)
from app.services.employer_task_service import EmployerTaskService

router = APIRouter(tags=["Employer Tasks & Candidate Activity (B-29)"])

MAX_TASK_ATTACHMENT_SIZE = 5 * 1024 * 1024
ALLOWED_TASK_ATTACHMENT_EXTENSIONS = {
    ".csv", ".jpeg", ".jpg", ".json", ".md", ".pdf", ".png", ".py", ".txt", ".ts",
    ".tsx", ".zip",
}


@router.post("/tasks/attachments", response_model=TaskFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_task_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.candidate_profile is None and current_user.employer_profile is None:
        raise HTTPException(status_code=403, detail="Вложения доступны кандидатам и работодателям")
    raw_name = file.filename or "attachment"
    file_name = PureWindowsPath(PurePosixPath(raw_name).name).name
    file_name = re.sub(r"[^\w.() -]", "_", file_name).strip(" .")[:255]
    if not file_name or os.path.splitext(file_name)[1].lower() not in ALLOWED_TASK_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Тип файла не поддерживается")
    content = await file.read(MAX_TASK_ATTACHMENT_SIZE + 1)
    if len(content) > MAX_TASK_ATTACHMENT_SIZE:
        raise HTTPException(status_code=400, detail="Размер одного файла не должен превышать 5 МБ")
    if not content:
        raise HTTPException(status_code=400, detail="Нельзя прикрепить пустой файл")
    attachment = TaskAttachment(
        owner_user_id=current_user.id,
        file_name=file_name,
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return TaskFileResponse(
        id=attachment.id,
        file_name=attachment.file_name,
        download_url=f"/tasks/attachments/{attachment.id}",
    )


@router.get("/tasks/attachments/{attachment_id}")
async def download_task_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db.scalar(
        select(TaskAttachment).options(
            selectinload(TaskAttachment.task).selectinload(EmployerTask.employer),
            selectinload(TaskAttachment.submission).selectinload(EmployerTaskSubmission.task).selectinload(EmployerTask.employer),
        ).where(TaskAttachment.id == attachment_id)
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    allowed = attachment.owner_user_id == current_user.id
    if current_user.employer_profile:
        allowed = allowed or bool(
            (attachment.task and attachment.task.employer_id == current_user.employer_profile.id)
            or (
                attachment.submission
                and attachment.submission.task.employer_id == current_user.employer_profile.id
            )
        )
    if current_user.candidate_profile:
        allowed = allowed or bool(
            attachment.submission
            and attachment.submission.candidate_id == current_user.candidate_profile.id
        )
        if attachment.task and not allowed:
            allowed = any(
                item.id == attachment.task.id
                for item in await EmployerTaskService.list_tasks_for_candidate(
                    db, current_user.candidate_profile.id,
                )
            )
    if not allowed:
        raise HTTPException(status_code=403, detail="Нет доступа к вложению")
    return Response(
        content=attachment.content,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.file_name)}"},
    )


# ---------------------------------------------------------
# Employer endpoints
# ---------------------------------------------------------

@router.post(
    "/employer/tasks",
    response_model=EmployerTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать короткое задание (Работодатель)",
)
async def create_employer_task(
    data: EmployerTaskCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль работодателя не заполнен",
        )
    return await EmployerTaskService.create_task(
        db, current_user.employer_profile.id, data
    )


@router.get(
    "/employer/tasks",
    response_model=list[EmployerTaskResponse],
    summary="Список заданий текущего работодателя",
)
async def list_employer_tasks(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        return []
    return await EmployerTaskService.get_employer_tasks(
        db, current_user.employer_profile.id
    )


@router.get(
    "/employer/tasks/{task_id}",
    response_model=EmployerTaskResponse,
    summary="Просмотр задания работодателем",
)
async def get_employer_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль работодателя не заполнен")
    return await EmployerTaskService.get_task_by_id_for_employer(
        db, current_user.employer_profile.id, task_id
    )


@router.patch(
    "/employer/tasks/{task_id}",
    response_model=EmployerTaskResponse,
    summary="Обновить задание (Работодатель)",
)
async def update_employer_task(
    task_id: uuid.UUID,
    data: EmployerTaskUpdate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль работодателя не заполнен")
    return await EmployerTaskService.update_task(
        db, current_user.employer_profile.id, task_id, data
    )


@router.get(
    "/employer/tasks/{task_id}/submissions",
    response_model=list[EmployerTaskSubmissionResponse],
    summary="Список ответов кандидатов по заданию",
)
async def list_task_submissions(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль работодателя не заполнен")
    return await EmployerTaskService.get_task_submissions(
        db, current_user.employer_profile.id, task_id
    )


@router.post(
    "/employer/tasks/submissions/{submission_id}/review",
    response_model=EmployerTaskSubmissionResponse,
    summary="Оценить открытый ответ кандидата (Работодатель)",
)
async def review_task_submission(
    submission_id: uuid.UUID,
    data: EmployerTaskReviewRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль работодателя не заполнен")
    return await EmployerTaskService.review_submission(
        db=db,
        employer_profile_id=current_user.employer_profile.id,
        reviewer_user_id=current_user.id,
        submission_id=submission_id,
        data=data,
    )


# ---------------------------------------------------------
# Candidate endpoints
# ---------------------------------------------------------

@router.get(
    "/candidate/tasks",
    response_model=list[CandidateTaskResponse],
    summary="Список доступных заданий от работодателей (Кандидат)",
)
async def list_candidate_tasks(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        return []
    return await EmployerTaskService.list_tasks_for_candidate(
        db, current_user.candidate_profile.id
    )


@router.get(
    "/candidate/tasks/my-submissions",
    response_model=list[EmployerTaskSubmissionResponse],
    summary="История решений заданий кандидата",
)
async def list_my_task_submissions(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        return []
    return await EmployerTaskService.get_candidate_submissions(
        db, current_user.candidate_profile.id
    )


@router.get(
    "/candidate/tasks/{task_id}",
    response_model=CandidateTaskResponse,
    summary="Просмотр задания кандидатом",
)
async def get_candidate_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        raise HTTPException(status_code=400, detail="Профиль кандидата не заполнен")
    return await EmployerTaskService.get_task_for_candidate(
        db, current_user.candidate_profile.id, task_id
    )


@router.post(
    "/candidate/tasks/{task_id}/submit",
    response_model=EmployerTaskSubmissionResponse,
    summary="Отправить решение задания (Кандидат)",
)
async def submit_task_solution(
    task_id: uuid.UUID,
    data: EmployerTaskSubmissionCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        raise HTTPException(status_code=400, detail="Профиль кандидата не заполнен")
    return await EmployerTaskService.submit_task_solution(
        db=db,
        candidate_profile=current_user.candidate_profile,
        task_id=task_id,
        data=data,
    )


@router.get(
    "/candidate/activity",
    response_model=list[CandidateActivityResponse],
    summary="Лента активности кандидата (B-29)",
)
async def get_candidate_activity(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        return []
    return await EmployerTaskService.get_candidate_activities(
        db, current_user.candidate_profile.id
    )
