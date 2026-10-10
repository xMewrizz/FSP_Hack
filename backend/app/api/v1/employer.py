import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_employer
from app.core.database import get_db
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.vacancy import Vacancy, VacancyApplication
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.employer_workspace import (
    EmployerTeamInvitationCreate,
    EmployerTeamResponse,
)
from app.schemas.employer import (
    EmployerOnboardingRequest,
    EmployerProfileResponse,
    EmployerProfileUpdateRequest,
)
from app.services.employer_service import employer_service
from app.services.employer_workspace_service import employer_workspace_service

router = APIRouter(tags=["Employer"])


class EmployerMentorResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    specialization: str | None
    verified_grade: str | None
    skills: list[str]
    city: str | None
    company_link: str
    photo_url: str | None = None


@router.get(
    "/mentors",
    response_model=list[EmployerMentorResponse],
    summary="Наставники среди кандидатов, связанных с компанией",
)
async def list_company_mentors(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    employer = await db.scalar(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    if employer is None:
        raise HTTPException(status_code=404, detail="Профиль работодателя не найден")

    employer_ids = select(EmployerProfile.id).where(
        EmployerProfile.organization_id == employer.organization_id
    ) if employer.organization_id else select(EmployerProfile.id).where(
        EmployerProfile.id == employer.id
    )
    applied_ids = select(VacancyApplication.candidate_id).join(
        Vacancy, Vacancy.id == VacancyApplication.vacancy_id
    ).where(Vacancy.employer_id.in_(employer_ids))
    invited_ids = select(Invitation.candidate_id).where(
        Invitation.employer_id.in_(employer_ids),
        Invitation.status == "accepted",
    )
    profiles = (await db.scalars(
        select(CandidateProfile)
        .where(
            CandidateProfile.id.in_(applied_ids.union(invited_ids)),
            CandidateProfile.mentor_available.is_(True),
            CandidateProfile.verified_grade.is_not(None),
            CandidateProfile.onboarding_completed.is_(True),
            CandidateProfile.agreed_publication.is_(True),
            CandidateProfile.visibility_public.is_(True),
        )
        .order_by(CandidateProfile.last_name, CandidateProfile.first_name)
    )).all()
    return [
        EmployerMentorResponse(
            user_id=profile.user_id,
            name=" ".join(part for part in (profile.first_name, profile.last_name) if part).strip() or "Кандидат",
            specialization=profile.verified_specialization or profile.specialization,
            verified_grade=profile.verified_grade,
            skills=profile.skills or [],
            city=profile.city,
            company_link="Отклик или принятое приглашение",
            photo_url=f"/candidate/{profile.id}/photo" if profile.photo_filename else None,
        )
        for profile in profiles
    ]


@router.post(
    "/onboarding",
    response_model=EmployerProfileResponse,
    summary="Онбординг работодателя",
)
async def complete_onboarding(
    request: EmployerOnboardingRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.complete_onboarding(db, current_user, request)


@router.get(
    "/profile",
    response_model=EmployerProfileResponse,
    summary="Профиль компании",
)
async def get_my_profile(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.get_profile(db, current_user)


@router.put(
    "/profile",
    response_model=EmployerProfileResponse,
    summary="Обновление профиля компании",
)
async def update_my_profile(
    request: EmployerProfileUpdateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_service.update_profile(db, current_user, request)


@router.get(
    "/team",
    response_model=EmployerTeamResponse,
    summary="Состав HR-команды и приглашения",
)
async def get_team(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.get_team(db, current_user)


@router.post(
    "/team/workspace",
    response_model=EmployerTeamResponse,
    summary="Создать HR-пространство компании",
)
async def create_team_workspace(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.create_team(db, current_user)


@router.post(
    "/team/invitations",
    response_model=EmployerTeamResponse,
    summary="Пригласить работодателя в HR-команду",
)
async def invite_team_member(
    request: EmployerTeamInvitationCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.invite_team_member(db, current_user, request)


@router.post(
    "/team/invitations/{invitation_id}/accept",
    response_model=EmployerTeamResponse,
    summary="Принять приглашение в HR-команду",
)
async def accept_team_invitation(
    invitation_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.accept_team_invitation(db, current_user, invitation_id)


@router.delete(
    "/team/invitations/{invitation_id}",
    response_model=EmployerTeamResponse,
    summary="Отменить приглашение в HR-команду",
)
async def cancel_team_invitation(
    invitation_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await employer_workspace_service.cancel_team_invitation(db, current_user, invitation_id)
