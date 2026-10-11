"""Private conversations about submitted vacancy applications."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.constants import UserRole
from app.models.candidate import CandidateProfile
from app.models.user import User
from app.models.vacancy import Vacancy, VacancyApplication
from app.models.vacancy_message import VacancyApplicationMessage
from app.services.vacancy_service import VacancyService

router = APIRouter(prefix="/vacancies/applications", tags=["Vacancy application conversations"])


class ApplicationMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ApplicationMessageResponse(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    is_mine: bool


class ApplicationMessagesResponse(BaseModel):
    messages: list[ApplicationMessageResponse]


class ApplicationConversationResponse(BaseModel):
    id: uuid.UUID
    vacancy_id: uuid.UUID
    vacancy_title: str
    company_name: str
    candidate_name: str
    status: str
    last_message: str


async def _accessible_application(
    db: AsyncSession, application_id: uuid.UUID, user: User, *, edit: bool = False
) -> VacancyApplication:
    application = await db.scalar(
        select(VacancyApplication)
        .options(
            selectinload(VacancyApplication.candidate),
            selectinload(VacancyApplication.vacancy).selectinload(Vacancy.employer),
        )
        .where(VacancyApplication.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Отклик не найден")
    if user.role == UserRole.CANDIDATE and application.candidate.user_id == user.id:
        return application
    if user.role == UserRole.EMPLOYER:
        try:
            await VacancyService._permission(db, user.id, application.vacancy, edit=edit)
            return application
        except HTTPException:
            pass
    raise HTTPException(status_code=404, detail="Отклик не найден")


@router.get("/conversations", response_model=list[ApplicationConversationResponse])
async def list_application_conversations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.CANDIDATE:
        candidate = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
        if candidate is None:
            return []
        query = select(VacancyApplication).where(VacancyApplication.candidate_id == candidate.id)
    elif current_user.role == UserRole.EMPLOYER:
        if current_user.employer_profile is None:
            return []
        vacancies = await VacancyService.get_employer_vacancies(
            db, current_user.employer_profile.id, current_user.id
        )
        if not vacancies:
            return []
        query = select(VacancyApplication).where(
            VacancyApplication.vacancy_id.in_([vacancy.id for vacancy in vacancies])
        )
    else:
        return []
    applications = (await db.scalars(
        query.options(
            selectinload(VacancyApplication.candidate),
            selectinload(VacancyApplication.vacancy).selectinload(Vacancy.employer),
        ).order_by(VacancyApplication.created_at.desc()).limit(200)
    )).all()
    conversations = []
    for application in applications:
        latest = await db.scalar(
            select(VacancyApplicationMessage)
            .where(VacancyApplicationMessage.application_id == application.id)
            .order_by(VacancyApplicationMessage.created_at.desc(), VacancyApplicationMessage.id.desc())
            .limit(1)
        )
        conversations.append(ApplicationConversationResponse(
            id=application.id,
            vacancy_id=application.vacancy_id,
            vacancy_title=application.vacancy.title,
            company_name=application.vacancy.employer.company_name,
            candidate_name=f"{application.candidate.first_name} {application.candidate.last_name}".strip() or "Кандидат",
            status=application.status,
            last_message=latest.body if latest else "",
        ))
    return conversations


@router.get("/{application_id}/messages", response_model=ApplicationMessagesResponse)
async def get_application_messages(
    application_id: uuid.UUID, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _accessible_application(db, application_id, current_user)
    messages = (await db.scalars(
        select(VacancyApplicationMessage)
        .where(VacancyApplicationMessage.application_id == application_id)
        .order_by(VacancyApplicationMessage.created_at, VacancyApplicationMessage.id)
    )).all()
    return ApplicationMessagesResponse(messages=[ApplicationMessageResponse(
        id=message.id, body=message.body, created_at=message.created_at,
        is_mine=message.sender_user_id == current_user.id,
    ) for message in messages])


@router.post("/{application_id}/messages", response_model=ApplicationMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_application_message(
    application_id: uuid.UUID, data: ApplicationMessageCreate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _accessible_application(db, application_id, current_user, edit=True)
    body = data.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Сообщение пустое")
    message = VacancyApplicationMessage(
        application_id=application_id, sender_user_id=current_user.id, body=body
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return ApplicationMessageResponse(
        id=message.id, body=message.body, created_at=message.created_at, is_mine=True
    )
