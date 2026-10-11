import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate, get_db
from app.models.candidate import CandidateProfile
from app.models.network_conversation import NetworkConversation, NetworkMessage
from app.models.user import User
from app.models.base import utc_now
from app.schemas.network import (
    MentorProfileResponse,
    MentorshipRequestCreate,
    NetworkConversationHistoryResponse,
    NetworkConversationResponse,
    NetworkMessageCreate,
    NetworkMessageResponse,
    NetworkStatsResponse,
)

router = APIRouter(prefix="/network", tags=["Networking and mentorship"])


def _name(profile: CandidateProfile) -> str:
    return " ".join(part for part in (profile.first_name, profile.last_name) if part).strip() or "Ментор"


@router.get("/stats", response_model=NetworkStatsResponse)
async def get_network_stats(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    sent_count = await db.scalar(
        select(func.count(NetworkConversation.id)).where(
            NetworkConversation.requester_user_id == current_user.id
        )
    )
    return NetworkStatsResponse(mentorship_requests_sent=sent_count or 0)


async def _conversation_for_user(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> NetworkConversation:
    result = await db.execute(
        select(NetworkConversation).where(
            NetworkConversation.id == conversation_id,
            or_(
                NetworkConversation.requester_user_id == user_id,
                NetworkConversation.mentor_user_id == user_id,
            ),
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return conversation


@router.get("/mentors", response_model=list[MentorProfileResponse])
async def search_mentors(
    skill: str | None = Query(None, max_length=100),
    specialization: str | None = Query(None, max_length=100),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(CandidateProfile)
        .where(
            CandidateProfile.mentor_available.is_(True),
            CandidateProfile.user_id != current_user.id,
            CandidateProfile.verified_grade.is_not(None),
        )
        .order_by(CandidateProfile.verified_grade, CandidateProfile.last_name)
        .limit(100)
    )
    if specialization:
        statement = statement.where(CandidateProfile.specialization == specialization)
    result = await db.execute(statement)
    profiles = result.scalars().all()
    skill_query = (skill or "").strip().casefold()
    return [
        MentorProfileResponse(
            user_id=profile.user_id,
            name=_name(profile),
            specialization=profile.verified_specialization or profile.specialization,
            verified_grade=profile.verified_grade,
            skills=profile.skills or [],
            city=profile.city,
        )
        for profile in profiles
        if not skill_query or any(skill_query in item.casefold() for item in (profile.skills or []))
    ]


@router.get("/conversations", response_model=list[NetworkConversationResponse])
async def list_network_conversations(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NetworkConversation)
        .where(
            or_(
                NetworkConversation.requester_user_id == current_user.id,
                NetworkConversation.mentor_user_id == current_user.id,
            )
        )
        .order_by(NetworkConversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    rows = []
    for conversation in conversations:
        other_id = (
            conversation.mentor_user_id
            if conversation.requester_user_id == current_user.id
            else conversation.requester_user_id
        )
        profile_result = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == other_id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            continue
        last_message_result = await db.execute(
            select(NetworkMessage.body)
            .where(NetworkMessage.conversation_id == conversation.id)
            .order_by(NetworkMessage.created_at.desc())
            .limit(1)
        )
        rows.append(
            NetworkConversationResponse(
                id=conversation.id,
                other_user_id=other_id,
                other_name=_name(profile),
                skill_focus=conversation.skill_focus,
                status=conversation.status,
                can_accept=(
                    conversation.status == "pending"
                    and conversation.mentor_user_id == current_user.id
                ),
                last_message=last_message_result.scalar_one_or_none() or "",
                updated_at=conversation.updated_at,
            )
        )
    return rows


@router.post(
    "/mentorship-requests",
    response_model=NetworkConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_mentorship(
    data: MentorshipRequestCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if data.mentor_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя отправить запрос самому себе")
    mentor_result = await db.execute(
        select(CandidateProfile).where(
            CandidateProfile.user_id == data.mentor_user_id,
            CandidateProfile.mentor_available.is_(True),
            CandidateProfile.verified_grade.is_not(None),
        )
    )
    mentor = mentor_result.scalar_one_or_none()
    if mentor is None:
        raise HTTPException(status_code=404, detail="Наставник больше не принимает запросы")
    existing_result = await db.execute(
        select(NetworkConversation).where(
            NetworkConversation.status.in_(("pending", "accepted")),
            or_(
                (
                    and_(
                        NetworkConversation.requester_user_id == current_user.id,
                        NetworkConversation.mentor_user_id == data.mentor_user_id,
                    )
                ),
                (
                    and_(
                        NetworkConversation.requester_user_id == data.mentor_user_id,
                        NetworkConversation.mentor_user_id == current_user.id,
                    )
                ),
            ),
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Запрос или диалог с этим наставником уже существует")

    conversation = NetworkConversation(
        requester_user_id=current_user.id,
        mentor_user_id=data.mentor_user_id,
        skill_focus=data.skill_focus,
        status="pending",
    )
    db.add(conversation)
    await db.flush()
    db.add(
        NetworkMessage(
            conversation_id=conversation.id,
            sender_user_id=current_user.id,
            body=data.message,
        )
    )
    await db.commit()
    await db.refresh(conversation)
    return NetworkConversationResponse(
        id=conversation.id,
        other_user_id=mentor.user_id,
        other_name=_name(mentor),
        skill_focus=conversation.skill_focus,
        status=conversation.status,
        can_accept=False,
        last_message=data.message,
        updated_at=conversation.updated_at,
    )


@router.post("/conversations/{conversation_id}/accept", response_model=NetworkConversationResponse)
async def accept_mentorship_request(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _conversation_for_user(db, conversation_id, current_user.id)
    if conversation.mentor_user_id != current_user.id or conversation.status != "pending":
        raise HTTPException(status_code=404, detail="Запрос не найден")
    conversation.status = "accepted"
    await db.commit()
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == conversation.requester_user_id)
    )
    profile = profile_result.scalar_one()
    return NetworkConversationResponse(
        id=conversation.id,
        other_user_id=conversation.requester_user_id,
        other_name=_name(profile),
        skill_focus=conversation.skill_focus,
        status=conversation.status,
        can_accept=False,
        last_message="",
        updated_at=conversation.updated_at,
    )


@router.post("/conversations/{conversation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_mentorship_request(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _conversation_for_user(db, conversation_id, current_user.id)
    if conversation.mentor_user_id != current_user.id or conversation.status != "pending":
        raise HTTPException(status_code=404, detail="Запрос не найден")
    conversation.status = "rejected"
    await db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=NetworkConversationHistoryResponse)
async def get_network_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _conversation_for_user(db, conversation_id, current_user.id)
    result = await db.execute(
        select(NetworkMessage)
        .where(NetworkMessage.conversation_id == conversation.id)
        .order_by(NetworkMessage.created_at, NetworkMessage.id)
    )
    return NetworkConversationHistoryResponse(
        messages=[
            NetworkMessageResponse(
                id=message.id,
                body=message.body,
                created_at=message.created_at,
                is_mine=message.sender_user_id == current_user.id,
            )
            for message in result.scalars().all()
        ]
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=NetworkMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_network_message(
    conversation_id: uuid.UUID,
    data: NetworkMessageCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _conversation_for_user(db, conversation_id, current_user.id)
    if conversation.status != "accepted":
        raise HTTPException(status_code=409, detail="Наставник должен принять запрос до начала переписки")
    message = NetworkMessage(
        conversation_id=conversation.id,
        sender_user_id=current_user.id,
        body=data.body,
    )
    conversation.updated_at = utc_now()
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return NetworkMessageResponse(
        id=message.id,
        body=message.body,
        created_at=message.created_at,
        is_mine=True,
    )
