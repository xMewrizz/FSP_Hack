import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.invitation import Invitation
from app.models.invitation_message import InvitationMessage
from app.models.user import User
from app.models.base import utc_now
from app.schemas.invitation_message import (
    InvitationConversationResponse,
    InvitationMessageCreate,
    InvitationMessageResponse,
    InvitationUnreadCountResponse,
)

router = APIRouter(tags=["Invitation conversations"])


async def _get_accepted_participating_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    current_user: User,
) -> Invitation:
    result = await db.execute(
        select(Invitation)
        .options(
            selectinload(Invitation.candidate).selectinload(CandidateProfile.user),
            selectinload(Invitation.employer).selectinload(EmployerProfile.user),
        )
        .where(Invitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()
    if (
        invitation is None
        or invitation.status != "accepted"
        or current_user.id not in (
            invitation.candidate.user_id,
            invitation.employer.user_id,
        )
    ):
        raise HTTPException(status_code=404, detail="Чат не найден")
    return invitation


@router.get(
    "/invitations/messages/unread-count",
    response_model=InvitationUnreadCountResponse,
    summary="Количество непрочитанных сообщений в принятых приглашениях",
)
async def get_unread_message_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationUnreadCountResponse:
    result = await db.execute(
        select(InvitationMessage.invitation_id, func.count(InvitationMessage.id))
        .join(Invitation, Invitation.id == InvitationMessage.invitation_id)
        .outerjoin(CandidateProfile, CandidateProfile.id == Invitation.candidate_id)
        .outerjoin(EmployerProfile, EmployerProfile.id == Invitation.employer_id)
        .where(
            Invitation.status == "accepted",
            InvitationMessage.sender_user_id != current_user.id,
            InvitationMessage.read_at.is_(None),
            or_(
                CandidateProfile.user_id == current_user.id,
                EmployerProfile.user_id == current_user.id,
            ),
        )
        .group_by(InvitationMessage.invitation_id)
    )
    by_invitation = {
        str(invitation_id): int(count)
        for invitation_id, count in result.all()
    }
    return InvitationUnreadCountResponse(
        unread_count=sum(by_invitation.values()),
        by_invitation=by_invitation,
    )


@router.get(
    "/invitations/{invitation_id}/messages",
    response_model=InvitationConversationResponse,
    summary="История чата по принятому приглашению",
)
async def get_invitation_messages(
    invitation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationConversationResponse:
    await _get_accepted_participating_invitation(db, invitation_id, current_user)
    unread_result = await db.execute(
        select(InvitationMessage.id).where(
            InvitationMessage.invitation_id == invitation_id,
            InvitationMessage.sender_user_id != current_user.id,
            InvitationMessage.read_at.is_(None),
        )
    )
    unread_ids = unread_result.scalars().all()
    if unread_ids:
        await db.execute(
            update(InvitationMessage)
            .where(InvitationMessage.id.in_(unread_ids))
            .values(read_at=utc_now())
        )
        await db.commit()

    result = await db.execute(
        select(InvitationMessage)
        .where(InvitationMessage.invitation_id == invitation_id)
        .order_by(InvitationMessage.created_at, InvitationMessage.id)
    )
    messages = result.scalars().all()
    return InvitationConversationResponse(
        messages=[
            InvitationMessageResponse(
                id=message.id,
                body=message.body,
                created_at=message.created_at,
                is_mine=message.sender_user_id == current_user.id,
            )
            for message in messages
        ],
        unread_count=0,
    )


@router.post(
    "/invitations/{invitation_id}/messages",
    response_model=InvitationMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить сообщение участнику принятого приглашения",
)
async def send_invitation_message(
    invitation_id: uuid.UUID,
    data: InvitationMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationMessageResponse:
    await _get_accepted_participating_invitation(db, invitation_id, current_user)
    message = InvitationMessage(
        invitation_id=invitation_id,
        sender_user_id=current_user.id,
        body=data.body,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return InvitationMessageResponse(
        id=message.id,
        body=message.body,
        created_at=message.created_at,
        is_mine=True,
    )
