import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import (
    get_current_candidate,
    get_current_employer,
    get_current_verified_user,
    get_db,
)
from app.models.user import User
from app.schemas.invitation import (
    InvitationCandidateAction,
    InvitationCreate,
    InvitationResponse,
)
from app.services.invitation_service import invitation_service

router = APIRouter(prefix="/invitations", tags=["Invitations & Reverse Hiring"])


@router.post(
    "",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить прямое оффер-приглашение кандидату (только работодатель)",
)
async def send_invitation(
    data: InvitationCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.create_invitation(db, current_user, data)


@router.get(
    "/sent",
    response_model=list[InvitationResponse],
    summary="Список отправленных приглашений компании (контакты скрыты до принятия)",
)
async def get_sent_invitations(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.get_sent_invitations(db, current_user)


@router.get(
    "/my",
    response_model=list[InvitationResponse],
    summary="Входящие приглашения от компаний (только кандидат)",
)
async def get_my_invitations(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.get_my_invitations(db, current_user)


@router.post(
    "/{invitation_id}/accept",
    response_model=InvitationResponse,
    summary="Принять приглашение компании (открывает контакты работодателю)",
)
async def accept_invitation(
    invitation_id: uuid.UUID,
    data: InvitationCandidateAction = InvitationCandidateAction(),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.candidate_action(
        db, current_user, invitation_id, action="accept", reply=data.reply
    )


@router.post(
    "/{invitation_id}/reject",
    response_model=InvitationResponse,
    summary="Отклонить приглашение компании",
)
async def reject_invitation(
    invitation_id: uuid.UUID,
    data: InvitationCandidateAction = InvitationCandidateAction(),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.candidate_action(
        db, current_user, invitation_id, action="reject", reply=data.reply
    )
