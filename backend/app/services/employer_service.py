import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.employer import EmployerProfile
from app.models.user import User
from app.schemas.employer import (
    EmployerOnboardingRequest,
    EmployerProfileResponse,
    EmployerProfileUpdateRequest,
)


class EmployerService:
    @staticmethod
    async def complete_onboarding(
        db: AsyncSession, user: User, data: EmployerOnboardingRequest
    ) -> EmployerProfileResponse:
        stmt = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            profile = EmployerProfile(user_id=user.id, company_name=data.company_name)
            db.add(profile)

        profile.company_name = data.company_name
        profile.description = data.description
        profile.industry = data.industry
        profile.website = data.website
        profile.contact_person = data.contact_person
        profile.phone = data.phone
        profile.city = data.city
        profile.onboarding_completed = True

        await db.commit()
        await db.refresh(profile)

        return EmployerProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            email=user.email,
            company_name=profile.company_name,
            description=profile.description,
            industry=profile.industry,
            website=profile.website,
            contact_person=profile.contact_person,
            phone=profile.phone,
            city=profile.city,
            onboarding_completed=profile.onboarding_completed,
        )

    @staticmethod
    async def get_profile(db: AsyncSession, user: User) -> EmployerProfileResponse:
        stmt = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден",
            )

        return EmployerProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            email=user.email,
            company_name=profile.company_name,
            description=profile.description,
            industry=profile.industry,
            website=profile.website,
            contact_person=profile.contact_person,
            phone=profile.phone,
            city=profile.city,
            onboarding_completed=profile.onboarding_completed,
        )

    @staticmethod
    async def update_profile(
        db: AsyncSession, user: User, data: EmployerProfileUpdateRequest
    ) -> EmployerProfileResponse:
        stmt = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден",
            )

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        await db.commit()
        await db.refresh(profile)

        return EmployerProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            email=user.email,
            company_name=profile.company_name,
            description=profile.description,
            industry=profile.industry,
            website=profile.website,
            contact_person=profile.contact_person,
            phone=profile.phone,
            city=profile.city,
            onboarding_completed=profile.onboarding_completed,
        )


employer_service = EmployerService()
