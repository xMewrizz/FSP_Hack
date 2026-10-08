from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.employer import EmployerProfile
from app.models.need import EmployerNeed
from app.models.user import User
from app.schemas.need import (
    EmployerNeedCreate,
    EmployerNeedResponse,
    EmployerNeedUpdate,
    SkillRequirement,
)


class NeedService:
    @staticmethod
    async def create_need(
        db: AsyncSession, user: User, data: EmployerNeedCreate
    ) -> EmployerNeedResponse:
        stmt = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res = await db.execute(stmt)
        employer = res.scalar_one_or_none()

        if not employer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден. Сначала завершите онбординг компании.",
            )

        skills_json = [s.model_dump() for s in data.required_skills]

        need = EmployerNeed(
            employer_id=employer.id,
            title=data.title,
            specialization=data.specialization,
            required_grade=data.required_grade.value,
            required_skills=skills_json,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_tax_type=data.salary_tax_type,
            currency=data.currency,
            work_format=data.work_format.value,
            city=data.city,
            description=data.description,
            is_active=True,
        )
        db.add(need)
        await db.commit()
        await db.refresh(need)

        return NeedService._build_response(need, employer.company_name)

    @staticmethod
    async def get_my_needs(db: AsyncSession, user: User) -> list[EmployerNeedResponse]:
        stmt_emp = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res_emp = await db.execute(stmt_emp)
        employer = res_emp.scalar_one_or_none()

        if not employer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден",
            )

        stmt = (
            select(EmployerNeed)
            .where(EmployerNeed.employer_id == employer.id)
            .order_by(EmployerNeed.created_at.desc())
        )
        res = await db.execute(stmt)
        needs = res.scalars().all()

        return [NeedService._build_response(n, employer.company_name) for n in needs]

    @staticmethod
    async def get_need(db: AsyncSession, need_id: uuid.UUID) -> EmployerNeedResponse:
        stmt = (
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.employer))
            .where(EmployerNeed.id == need_id)
        )
        res = await db.execute(stmt)
        need = res.scalar_one_or_none()

        if not need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Потребность не найдена",
            )

        return NeedService._build_response(need, need.employer.company_name)

    @staticmethod
    async def update_need(
        db: AsyncSession, user: User, need_id: uuid.UUID, data: EmployerNeedUpdate
    ) -> EmployerNeedResponse:
        stmt_emp = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res_emp = await db.execute(stmt_emp)
        employer = res_emp.scalar_one_or_none()

        if not employer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль работодателя не найден",
            )

        stmt = select(EmployerNeed).where(
            EmployerNeed.id == need_id,
            EmployerNeed.employer_id == employer.id,
        )
        res = await db.execute(stmt)
        need = res.scalar_one_or_none()

        if not need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Потребность не найдена или принадлежит другой компании",
            )
        new_min = data.salary_min if data.salary_min is not None else need.salary_min
        new_max = data.salary_max if data.salary_max is not None else need.salary_max
        if new_min > new_max:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail="salary_min не может быть больше salary_max",
            )

        update_dict = data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            if key == "required_grade" and val:
                need.required_grade = val.value if hasattr(val, "value") else val
            elif key == "work_format" and val:
                need.work_format = val.value if hasattr(val, "value") else val
            elif key == "required_skills" and val is not None:
                need.required_skills = [
                    s.model_dump() if hasattr(s, "model_dump") else s for s in val
                ]
            elif hasattr(need, key):
                setattr(need, key, val)

        await db.commit()
        await db.refresh(need)

        return NeedService._build_response(need, employer.company_name)

    @staticmethod
    async def delete_need(
        db: AsyncSession, user: User, need_id: uuid.UUID
    ) -> dict[str, str]:
        stmt_emp = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
        res_emp = await db.execute(stmt_emp)
        employer = res_emp.scalar_one_or_none()

        if not employer:
            raise HTTPException(status_code=404, detail="Работодатель не найден")

        stmt = select(EmployerNeed).where(
            EmployerNeed.id == need_id,
            EmployerNeed.employer_id == employer.id,
        )
        res = await db.execute(stmt)
        need = res.scalar_one_or_none()

        if not need:
            raise HTTPException(status_code=404, detail="Потребность не найдена")

        await db.delete(need)
        await db.commit()

        return {"message": "Потребность успешно удалена"}

    @staticmethod
    def _build_response(need: EmployerNeed, company_name: str) -> EmployerNeedResponse:
        skills = [
            SkillRequirement(**s) if isinstance(s, dict) else s
            for s in (need.required_skills or [])
        ]
        return EmployerNeedResponse(
            id=need.id,
            employer_id=need.employer_id,
            company_name=company_name,
            title=need.title,
            specialization=need.specialization,
            required_grade=need.required_grade,
            required_skills=skills,
            salary_min=need.salary_min,
            salary_max=need.salary_max,
            salary_tax_type=getattr(need, "salary_tax_type", "gross") or "gross",
            currency=need.currency,
            work_format=need.work_format,
            city=need.city,
            description=need.description,
            is_active=need.is_active,
            created_at=need.created_at,
        )


need_service = NeedService()
