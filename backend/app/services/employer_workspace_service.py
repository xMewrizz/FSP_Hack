from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.employer_workspace import (
    CandidateReview,
    CandidateReviewMessage,
    EmployerOrganization,
    EmployerTeamInvitation,
)
from app.models.user import User
from app.schemas.employer_workspace import (
    CandidateReviewResponse,
    CandidateReviewUpdate,
    EmployerTeamInvitationCreate,
    EmployerTeamResponse,
)


class EmployerWorkspaceService:
    @staticmethod
    async def _profile_and_organization(
        db: AsyncSession, user: User
    ) -> tuple[EmployerProfile, EmployerOrganization]:
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль работодателя не найден")
        organization = (
            await db.get(EmployerOrganization, profile.organization_id)
            if profile.organization_id
            else None
        )
        if organization is None:
            organization = EmployerOrganization(name=profile.company_name, owner_user_id=user.id)
            db.add(organization)
            await db.flush()
            profile.organization_id = organization.id
            await db.commit()
            await db.refresh(organization)
        return profile, organization

    @staticmethod
    async def _can_manage_team(
        db: AsyncSession, user: User, profile: EmployerProfile, organization: EmployerOrganization
    ) -> bool:
        return organization.owner_user_id == user.id or profile.team_role == "team_lead"

    @staticmethod
    async def _published_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> CandidateProfile:
        candidate = await db.scalar(
            select(CandidateProfile).where(
                CandidateProfile.id == candidate_id,
                CandidateProfile.onboarding_completed.is_(True),
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
                CandidateProfile.verified_grade.is_not(None),
            )
        )
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль кандидата не найден")
        return candidate

    @staticmethod
    def _review_response(review: CandidateReview) -> CandidateReviewResponse:
        return CandidateReviewResponse(
            candidate_profile_id=review.candidate_profile_id,
            workspace_active=True,
            notes=review.notes,
            pipeline_status=review.pipeline_status,
            contact_status=review.contact_status,
            background_check_status=review.background_check_status,
            updated_at=review.updated_at,
            messages=[
                {
                    "id": message.id,
                    "sender_user_id": message.sender_user_id,
                    "sender_name": (
                        message.sender.employer_profile.company_name
                        if message.sender.employer_profile
                        else message.sender.email
                    ),
                    "body": message.body,
                    "created_at": message.created_at,
                }
                for message in review.messages
            ],
        )

    @staticmethod
    async def get_candidate_review(
        db: AsyncSession, user: User, candidate_id: uuid.UUID
    ) -> CandidateReviewResponse:
        await EmployerWorkspaceService._published_candidate(db, candidate_id)
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль работодателя не найден")
        organization = (
            await db.get(EmployerOrganization, profile.organization_id)
            if profile.organization_id
            else None
        )
        if organization is None:
            return CandidateReviewResponse(
                candidate_profile_id=candidate_id,
                workspace_active=False,
                notes="",
                pipeline_status="new",
                contact_status="not_started",
                background_check_status="not_started",
                updated_at=None,
                messages=[],
            )
        review = await db.scalar(
            select(CandidateReview)
            .options(
                selectinload(CandidateReview.messages)
                .selectinload(CandidateReviewMessage.sender)
                .selectinload(User.employer_profile)
            )
            .where(
                CandidateReview.organization_id == organization.id,
                CandidateReview.candidate_profile_id == candidate_id,
            )
        )
        if review is None:
            review = CandidateReview(
                organization_id=organization.id,
                candidate_profile_id=candidate_id,
            )
            db.add(review)
            await db.commit()
            return await EmployerWorkspaceService.get_candidate_review(db, user, candidate_id)
        return EmployerWorkspaceService._review_response(review)

    @staticmethod
    async def update_candidate_review(
        db: AsyncSession,
        user: User,
        candidate_id: uuid.UUID,
        data: CandidateReviewUpdate,
    ) -> CandidateReviewResponse:
        _, organization = await EmployerWorkspaceService._profile_and_organization(db, user)
        await EmployerWorkspaceService._published_candidate(db, candidate_id)
        review = await db.scalar(
            select(CandidateReview)
            .options(
                selectinload(CandidateReview.messages)
                .selectinload(CandidateReviewMessage.sender)
                .selectinload(User.employer_profile)
            )
            .where(
                CandidateReview.organization_id == organization.id,
                CandidateReview.candidate_profile_id == candidate_id,
            )
        )
        if review is None:
            review = CandidateReview(organization_id=organization.id, candidate_profile_id=candidate_id)
            db.add(review)
        for key, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(review, key, value.strip() if key == "notes" else value)
        await db.commit()
        await db.refresh(review)
        return await EmployerWorkspaceService.get_candidate_review(db, user, candidate_id)

    @staticmethod
    async def add_candidate_review_message(
        db: AsyncSession, user: User, candidate_id: uuid.UUID, body: str
    ) -> CandidateReviewResponse:
        _, organization = await EmployerWorkspaceService._profile_and_organization(db, user)
        await EmployerWorkspaceService._published_candidate(db, candidate_id)
        review = await db.scalar(
            select(CandidateReview).where(
                CandidateReview.organization_id == organization.id,
                CandidateReview.candidate_profile_id == candidate_id,
            )
        )
        if review is None:
            review = CandidateReview(organization_id=organization.id, candidate_profile_id=candidate_id)
            db.add(review)
            await db.flush()
        message_body = body.strip()
        if not message_body:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Сообщение не может быть пустым")
        db.add(CandidateReviewMessage(
            review_id=review.id,
            sender_user_id=user.id,
            body=message_body,
            created_at=datetime.now(timezone.utc),
        ))
        await db.commit()
        return await EmployerWorkspaceService.get_candidate_review(db, user, candidate_id)

    @staticmethod
    async def get_team(db: AsyncSession, user: User) -> EmployerTeamResponse:
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль работодателя не найден")
        received = (await db.scalars(
            select(EmployerTeamInvitation)
            .where(
                func.lower(EmployerTeamInvitation.invited_email) == user.email.lower(),
                EmployerTeamInvitation.status == "pending",
            )
            .order_by(EmployerTeamInvitation.created_at.desc())
        )).all()
        organization = (
            await db.get(EmployerOrganization, profile.organization_id)
            if profile.organization_id
            else None
        )
        if organization is None:
            return EmployerTeamResponse(
                current_user_id=user.id,
                organization_id=None,
                organization_name=None,
                current_user_is_owner=False,
                current_user_can_manage_team=False,
                members=[],
                invitations=[],
                received_invitations=[
                    {
                        "id": invitation.id,
                        "invited_email": invitation.invited_email,
                        "status": invitation.status,
                        "created_at": invitation.created_at,
                        "team_role": invitation.team_role,
                    }
                    for invitation in received
                ],
            )
        members = (await db.scalars(
            select(EmployerProfile)
            .options(selectinload(EmployerProfile.user))
            .where(EmployerProfile.organization_id == organization.id)
            .order_by(EmployerProfile.created_at)
        )).all()
        invitations = (await db.scalars(
            select(EmployerTeamInvitation)
            .where(EmployerTeamInvitation.organization_id == organization.id)
            .order_by(EmployerTeamInvitation.created_at.desc())
        )).all()
        return EmployerTeamResponse(
            current_user_id=user.id,
            organization_id=organization.id,
            organization_name=organization.name,
            current_user_is_owner=organization.owner_user_id == user.id,
            current_user_can_manage_team=await EmployerWorkspaceService._can_manage_team(
                db, user, profile, organization
            ),
            members=[
                {
                    "user_id": member.user_id,
                    "email": member.user.email,
                    "company_name": member.company_name,
                    "is_owner": member.user_id == organization.owner_user_id,
                    "team_role": (
                        "owner" if member.user_id == organization.owner_user_id else member.team_role
                    ),
                }
                for member in members
            ],
            invitations=[
                {
                    "id": invitation.id,
                    "invited_email": invitation.invited_email,
                    "status": invitation.status,
                    "created_at": invitation.created_at,
                    "team_role": invitation.team_role,
                }
                for invitation in invitations
            ],
            received_invitations=[
                {
                    "id": invitation.id,
                    "invited_email": invitation.invited_email,
                    "status": invitation.status,
                    "created_at": invitation.created_at,
                    "team_role": invitation.team_role,
                }
                for invitation in received
            ],
        )

    @staticmethod
    async def create_team(db: AsyncSession, user: User) -> EmployerTeamResponse:
        await EmployerWorkspaceService._profile_and_organization(db, user)
        return await EmployerWorkspaceService.get_team(db, user)

    @staticmethod
    async def invite_team_member(
        db: AsyncSession, user: User, data: EmployerTeamInvitationCreate
    ) -> EmployerTeamResponse:
        profile, organization = await EmployerWorkspaceService._profile_and_organization(db, user)
        can_manage = await EmployerWorkspaceService._can_manage_team(db, user, profile, organization)
        if not can_manage or (profile.team_role == "team_lead" and data.team_role != "hr"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Тимлид может приглашать только HR, а назначать тимлидов может владелец компании")
        email = data.email.strip().lower()
        if email.count("@") != 1 or "." not in email.split("@", 1)[1]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Укажите корректный email")
        if email == user.email.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя пригласить собственный аккаунт")
        existing_member = await db.scalar(
            select(EmployerProfile)
            .join(User, User.id == EmployerProfile.user_id)
            .where(func.lower(User.email) == email)
        )
        if existing_member and existing_member.organization_id:
            detail = (
                "Этот работодатель уже в команде"
                if existing_member.organization_id == organization.id
                else "Этот аккаунт уже состоит в другой HR-команде"
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        pending = await db.scalar(
            select(EmployerTeamInvitation).where(
                func.lower(EmployerTeamInvitation.invited_email) == email,
                EmployerTeamInvitation.status == "pending",
            )
        )
        if pending:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Приглашение на этот email уже ожидает ответа")
        db.add(EmployerTeamInvitation(
            organization_id=organization.id,
            invited_email=email,
            invited_by_user_id=user.id,
            status="pending",
            team_role=data.team_role,
        ))
        await db.commit()
        return await EmployerWorkspaceService.get_team(db, user)

    @staticmethod
    async def accept_team_invitation(
        db: AsyncSession, user: User, invitation_id: uuid.UUID
    ) -> EmployerTeamResponse:
        invitation = await db.scalar(
            select(EmployerTeamInvitation).where(
                EmployerTeamInvitation.id == invitation_id,
                EmployerTeamInvitation.status == "pending",
                func.lower(EmployerTeamInvitation.invited_email) == user.email.lower(),
            )
        )
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль работодателя не найден")
        if profile.organization_id and profile.organization_id != invitation.organization_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Аккаунт уже состоит в другой HR-команде")
        organization = await db.get(EmployerOrganization, invitation.organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
        profile.organization_id = organization.id
        profile.company_name = organization.name
        profile.team_role = invitation.team_role
        invitation.status = "accepted"
        invitation.accepted_by_user_id = user.id
        invitation.accepted_at = datetime.now(timezone.utc)
        await db.commit()
        return await EmployerWorkspaceService.get_team(db, user)

    @staticmethod
    async def cancel_team_invitation(
        db: AsyncSession, user: User, invitation_id: uuid.UUID
    ) -> EmployerTeamResponse:
        profile, organization = await EmployerWorkspaceService._profile_and_organization(db, user)
        invitation = await db.scalar(
            select(EmployerTeamInvitation).where(
                EmployerTeamInvitation.id == invitation_id,
                EmployerTeamInvitation.organization_id == organization.id,
                EmployerTeamInvitation.status == "pending",
            )
        )
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
        if organization.owner_user_id != user.id and (
            profile.team_role != "team_lead" or invitation.team_role != "hr"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для отмены этого приглашения")
        invitation.status = "cancelled"
        await db.commit()
        return await EmployerWorkspaceService.get_team(db, user)


employer_workspace_service = EmployerWorkspaceService()
