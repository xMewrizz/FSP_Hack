"""Private dialogue between a task author and the candidate who submitted it."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.employer_task import EmployerTask, EmployerTaskMessage, EmployerTaskSubmission
from app.models.user import User


router = APIRouter(prefix="/tasks", tags=["Employer task conversations"])


class TaskMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TaskMessageResponse(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    is_mine: bool


class TaskConversationResponse(BaseModel):
    submission_id: uuid.UUID
    task_title: str
    other_name: str
    last_message: str | None
    updated_at: datetime


async def _participant_submission(
    db: AsyncSession, submission_id: uuid.UUID, user_id: uuid.UUID
) -> EmployerTaskSubmission:
    submission = await db.scalar(
        select(EmployerTaskSubmission)
        .options(
            selectinload(EmployerTaskSubmission.candidate),
            selectinload(EmployerTaskSubmission.task).selectinload(EmployerTask.employer),
        )
        .where(EmployerTaskSubmission.id == submission_id)
    )
    if submission is None or user_id not in (
        submission.candidate.user_id, submission.task.employer.user_id
    ):
        raise HTTPException(status_code=404, detail="Диалог по заданию не найден")
    return submission


@router.get("/conversations", response_model=list[TaskConversationResponse])
async def list_task_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submissions = (await db.scalars(
        select(EmployerTaskSubmission)
        .join(EmployerTask, EmployerTask.id == EmployerTaskSubmission.task_id)
        .join(CandidateProfile, CandidateProfile.id == EmployerTaskSubmission.candidate_id)
        .join(EmployerProfile, EmployerProfile.id == EmployerTask.employer_id)
        .options(
            selectinload(EmployerTaskSubmission.candidate),
            selectinload(EmployerTaskSubmission.task).selectinload(EmployerTask.employer),
        )
        .where(or_(CandidateProfile.user_id == current_user.id, EmployerProfile.user_id == current_user.id))
        .order_by(EmployerTaskSubmission.updated_at.desc())
        .limit(200)
    )).all()
    conversations = []
    for submission in submissions:
        latest = await db.scalar(
            select(EmployerTaskMessage)
            .where(EmployerTaskMessage.submission_id == submission.id)
            .order_by(EmployerTaskMessage.created_at.desc(), EmployerTaskMessage.id.desc())
            .limit(1)
        )
        candidate_is_current = submission.candidate.user_id == current_user.id
        conversations.append(TaskConversationResponse(
            submission_id=submission.id,
            task_title=submission.task.title,
            other_name=(submission.task.employer.company_name if candidate_is_current
                        else f"{submission.candidate.first_name} {submission.candidate.last_name}".strip()),
            last_message=latest.body if latest else None,
            updated_at=latest.created_at if latest else submission.updated_at,
        ))
    return sorted(conversations, key=lambda row: row.updated_at, reverse=True)


@router.get("/submissions/{submission_id}/messages", response_model=list[TaskMessageResponse])
async def get_task_messages(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _participant_submission(db, submission_id, current_user.id)
    messages = (await db.scalars(
        select(EmployerTaskMessage)
        .where(EmployerTaskMessage.submission_id == submission_id)
        .order_by(EmployerTaskMessage.created_at, EmployerTaskMessage.id)
    )).all()
    return [TaskMessageResponse(
        id=item.id, body=item.body, created_at=item.created_at,
        is_mine=item.sender_user_id == current_user.id,
    ) for item in messages]


@router.post(
    "/submissions/{submission_id}/messages",
    response_model=TaskMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_task_message(
    submission_id: uuid.UUID,
    data: TaskMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _participant_submission(db, submission_id, current_user.id)
    body = data.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Сообщение пустое")
    message = EmployerTaskMessage(
        submission_id=submission_id, sender_user_id=current_user.id, body=body,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return TaskMessageResponse(id=message.id, body=message.body, created_at=message.created_at, is_mine=True)
