from datetime import datetime, timezone
from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.invitation import Invitation
from app.models.need import EmployerNeed
from app.models.user import User
from app.schemas.invitation import (
    CandidateContactsRevealed,
    InvitationCreate,
    InvitationResponse,
)


class InvitationService:
    @staticmethod
    async def create_invitation(
        db: AsyncSession, user: User, data: InvitationCreate
    ) -> InvitationResponse:
        stmt_emp = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res_emp = await db.execute(stmt_emp)
        employer = res_emp.scalar_one_or_none()

        if not employer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден. Сначала завершите онбординг компании.",
            )

        stmt_cand = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.user))
            .where(
                CandidateProfile.id == data.candidate_id,
                CandidateProfile.agreed_publication.is_(True),
                CandidateProfile.visibility_public.is_(True),
            )
        )
        res_cand = await db.execute(stmt_cand)
        candidate = res_cand.scalar_one_or_none()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кандидат не найден",
            )
        is_demo = not candidate.user.is_active and candidate.user.email.endswith("@example.test")

        need_title = None
        if data.need_id:
            stmt_need = select(EmployerNeed).where(
                EmployerNeed.id == data.need_id,
                EmployerNeed.employer_id == employer.id,
            )
            res_need = await db.execute(stmt_need)
            need = res_need.scalar_one_or_none()
            if not need:
                raise HTTPException(status_code=404, detail="Потребность компании не найдена")
            need_title = need.title

        invitation = Invitation(
            employer_id=employer.id,
            candidate_id=candidate.id,
            need_id=data.need_id,
            company_name=employer.company_name,
            offer_description=data.offer_description,
            contact_method=data.contact_method,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_tax_type=data.salary_tax_type,
            currency=data.currency,
            status="demo" if is_demo else "sent",
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        return InvitationService._build_response(
            invitation=invitation,
            candidate=candidate,
            need_title=need_title,
            reveal_contacts=False,
        )

    @staticmethod
    async def get_sent_invitations(
        db: AsyncSession, user: User
    ) -> list[InvitationResponse]:
        stmt_emp = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res_emp = await db.execute(stmt_emp)
        employer = res_emp.scalar_one_or_none()

        if not employer:
            raise HTTPException(status_code=404, detail="Работодатель не найден")

        stmt = (
            select(Invitation)
            .options(
                selectinload(Invitation.candidate).selectinload(CandidateProfile.user),
                selectinload(Invitation.need),
            )
            .where(Invitation.employer_id == employer.id)
            .order_by(Invitation.created_at.desc())
        )
        res = await db.execute(stmt)
        invitations = res.scalars().all()

        results = []
        for inv in invitations:
            reveal = inv.status == "accepted"
            need_title = inv.need.title if inv.need else None
            results.append(
                InvitationService._build_response(
                    invitation=inv,
                    candidate=inv.candidate,
                    need_title=need_title,
                    reveal_contacts=reveal,
                )
            )
        return results

    @staticmethod
    async def get_my_invitations(
        db: AsyncSession, user: User
    ) -> list[InvitationResponse]:
        stmt_cand = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.user))
            .where(CandidateProfile.user_id == user.id)
        )
        res_cand = await db.execute(stmt_cand)
        candidate = res_cand.scalar_one_or_none()

        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")

        stmt = (
            select(Invitation)
            .options(
                selectinload(Invitation.need),
            )
            .where(Invitation.candidate_id == candidate.id)
            .order_by(Invitation.created_at.desc())
        )
        res = await db.execute(stmt)
        invitations = res.scalars().all()

        results = []
        for inv in invitations:
            # If candidate opens it and status is 'sent', update to 'viewed'
            if inv.status == "sent":
                inv.status = "viewed"
                db.add(inv)

            need_title = inv.need.title if inv.need else None
            results.append(
                InvitationService._build_response(
                    invitation=inv,
                    candidate=candidate,
                    need_title=need_title,
                    reveal_contacts=True,
                )
            )
        await db.commit()
        return results

    @staticmethod
    async def candidate_action(
        db: AsyncSession, user: User, invitation_id: uuid.UUID, action: str, reply: str | None = None
    ) -> InvitationResponse:
        stmt_cand = (
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.user))
            .where(CandidateProfile.user_id == user.id)
        )
        res_cand = await db.execute(stmt_cand)
        candidate = res_cand.scalar_one_or_none()

        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")

        stmt = (
            select(Invitation)
            .options(selectinload(Invitation.need))
            .where(
                Invitation.id == invitation_id,
                Invitation.candidate_id == candidate.id,
            )
        )
        res = await db.execute(stmt)
        invitation = res.scalar_one_or_none()

        if not invitation:
            raise HTTPException(status_code=404, detail="Приглашение не найдено")

        now = datetime.now(timezone.utc)
        if action == "accept":
            invitation.status = "accepted"
            invitation.accepted_at = now
        elif action == "reject":
            invitation.status = "rejected"
        else:
            raise HTTPException(status_code=400, detail="Неверное действие. Доступны: accept, reject")

        if reply:
            invitation.candidate_reply = reply

        await db.commit()
        await db.refresh(invitation)

        need_title = invitation.need.title if invitation.need else None
        return InvitationService._build_response(
            invitation=invitation,
            candidate=candidate,
            need_title=need_title,
            reveal_contacts=True,
        )

    @staticmethod
    def _build_response(
        invitation: Invitation,
        candidate: CandidateProfile,
        need_title: str | None,
        reveal_contacts: bool,
    ) -> InvitationResponse:
        cand_name = f"{candidate.first_name} {candidate.last_name}".strip() or "Кандидат"

        contacts = None
        is_demo = not candidate.user.is_active and candidate.user.email.endswith("@example.test")
        if reveal_contacts and candidate.user and not is_demo:
            contacts = CandidateContactsRevealed(
                email=candidate.user.email,
                phone=candidate.phone,
                telegram=candidate.telegram,
            )

        return InvitationResponse(
            id=invitation.id,
            employer_id=invitation.employer_id,
            company_name=invitation.company_name,
            candidate_id=invitation.candidate_id,
            candidate_name=cand_name,
            need_id=invitation.need_id,
            need_title=need_title,
            offer_description=invitation.offer_description,
            contact_method=invitation.contact_method,
            salary_min=invitation.salary_min,
            salary_max=invitation.salary_max,
            salary_tax_type=getattr(invitation, "salary_tax_type", "gross") or "gross",
            currency=invitation.currency,
            status=invitation.status,
            candidate_reply=invitation.candidate_reply,
            created_at=invitation.created_at,
            accepted_at=invitation.accepted_at,
            candidate_contacts=contacts,
            is_demo=is_demo,
        )


invitation_service = InvitationService()
