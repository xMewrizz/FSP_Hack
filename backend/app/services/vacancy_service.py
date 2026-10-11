from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.employer_workspace import EmployerOrganization
from app.models.user import User
from app.models.vacancy import Vacancy, VacancyAccess, VacancyApplication
from app.schemas.vacancy import (
    ApplicationCreate,
    CandidateContactInfo,
    CompanyShortInfo,
    VacancyCreate,
    VacancyResponse,
    VacancyAccessResponse,
    VacancyAccessUpdate,
    VacancyUpdate,
)


class VacancyService:
    @staticmethod
    async def can_edit_vacancy(db: AsyncSession, user_id: uuid.UUID, vacancy: Vacancy) -> bool:
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
        if profile is None:
            return False
        if profile.id == vacancy.employer_id:
            return True
        owner_id = await db.scalar(
            select(EmployerOrganization.owner_user_id).where(
                EmployerOrganization.id == profile.organization_id
            )
        ) if profile.organization_id else None
        if owner_id == user_id:
            return True
        permission = await db.scalar(select(VacancyAccess).where(
            VacancyAccess.vacancy_id == vacancy.id,
            VacancyAccess.user_id == user_id,
        ))
        return bool(permission and permission.can_edit)

    @staticmethod
    async def _permission(db: AsyncSession, user_id: uuid.UUID, vacancy: Vacancy, *, edit: bool) -> None:
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
        if profile is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ к вакансии запрещён")
        if profile.id == vacancy.employer_id:
            return
        owner_id = await db.scalar(
            select(EmployerOrganization.owner_user_id).where(
                EmployerOrganization.id == profile.organization_id
            )
        ) if profile.organization_id else None
        if owner_id == user_id:
            return
        permission = await db.scalar(select(VacancyAccess).where(
            VacancyAccess.vacancy_id == vacancy.id,
            VacancyAccess.user_id == user_id,
        ))
        if permission and (permission.can_edit if edit else permission.can_view or permission.can_edit):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на эту вакансию")

    @staticmethod
    async def _access_managed_vacancy(
        db: AsyncSession, user: User, vacancy_id: uuid.UUID
    ) -> tuple[Vacancy, EmployerOrganization]:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if profile is None or profile.organization_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Сначала создайте HR-пространство команды")
        organization = await db.get(EmployerOrganization, profile.organization_id)
        author = await db.get(EmployerProfile, vacancy.employer_id)
        if (
            organization is None
            or (organization.owner_user_id != user.id and profile.team_role != "team_lead")
            or author is None
            or author.organization_id != organization.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только руководитель команды управляет доступами её вакансий")
        return vacancy, organization

    @staticmethod
    async def get_vacancy_permissions(
        db: AsyncSession, user: User, vacancy_id: uuid.UUID
    ) -> list[VacancyAccessResponse]:
        _, organization = await VacancyService._access_managed_vacancy(db, user, vacancy_id)
        members = (await db.execute(
            select(EmployerProfile, User)
            .join(User, User.id == EmployerProfile.user_id)
            .where(EmployerProfile.organization_id == organization.id)
            .order_by(EmployerProfile.created_at)
        )).all()
        grants = (await db.scalars(
            select(VacancyAccess).where(VacancyAccess.vacancy_id == vacancy_id)
        )).all()
        by_user = {grant.user_id: grant for grant in grants}
        return [
            VacancyAccessResponse(
                user_id=member.user_id,
                email=account.email,
                company_name=member.company_name,
                can_view=bool(by_user.get(member.user_id) and (by_user[member.user_id].can_view or by_user[member.user_id].can_edit)),
                can_edit=bool(by_user.get(member.user_id) and by_user[member.user_id].can_edit),
            )
            for member, account in members
            if member.user_id != user.id
        ]

    @staticmethod
    async def set_vacancy_permission(
        db: AsyncSession, user: User, vacancy_id: uuid.UUID, data: VacancyAccessUpdate
    ) -> list[VacancyAccessResponse]:
        vacancy, organization = await VacancyService._access_managed_vacancy(db, user, vacancy_id)
        member = await db.scalar(select(EmployerProfile).where(
            EmployerProfile.user_id == data.user_id,
            EmployerProfile.organization_id == organization.id,
        ))
        if member is None or data.user_id == user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник HR-команды не найден")
        grant = await db.scalar(select(VacancyAccess).where(
            VacancyAccess.vacancy_id == vacancy.id,
            VacancyAccess.user_id == data.user_id,
        ))
        if not data.can_view and not data.can_edit:
            if grant is not None:
                await db.delete(grant)
        elif grant is None:
            db.add(VacancyAccess(
                vacancy_id=vacancy.id,
                user_id=data.user_id,
                can_view=data.can_view or data.can_edit,
                can_edit=data.can_edit,
            ))
        else:
            grant.can_view = data.can_view or data.can_edit
            grant.can_edit = data.can_edit
        await db.commit()
        return await VacancyService.get_vacancy_permissions(db, user, vacancy_id)

    @staticmethod
    async def create_vacancy(
        db: AsyncSession,
        employer_id: uuid.UUID,
        data: VacancyCreate,
    ) -> Vacancy:
        vacancy = Vacancy(
            employer_id=employer_id,
            title=data.title,
            specialization=data.specialization,
            required_grade=data.required_grade,
            required_skills=data.required_skills,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_tax_type=data.salary_tax_type,
            currency=data.currency,
            work_format=data.work_format,
            city=data.city,
            description=data.description,
            is_published=data.is_published,
        )
        db.add(vacancy)
        await db.commit()
        await db.refresh(vacancy)
        return vacancy

    @staticmethod
    async def update_vacancy(
        db: AsyncSession,
        user_id: uuid.UUID,
        vacancy_id: uuid.UUID,
        data: VacancyUpdate,
    ) -> Vacancy:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        await VacancyService._permission(db, user_id, vacancy, edit=True)

        update_dict = data.model_dump(exclude_unset=True)
        if "salary_min" in update_dict or "salary_max" in update_dict:
            s_min = update_dict.get("salary_min", vacancy.salary_min)
            s_max = update_dict.get("salary_max", vacancy.salary_max)
            if s_max < s_min:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="salary_max не может быть меньше salary_min",
                )

        for key, value in update_dict.items():
            setattr(vacancy, key, value)

        await db.commit()
        await db.refresh(vacancy)
        return vacancy

    @staticmethod
    async def delete_vacancy(
        db: AsyncSession,
        user_id: uuid.UUID,
        vacancy_id: uuid.UUID,
    ) -> bool:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
        if profile is None or profile.id != vacancy.employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Удалять вакансию может только её автор",
            )
        await db.delete(vacancy)
        await db.commit()
        return True

    @staticmethod
    async def get_vacancies(
        db: AsyncSession,
        specialization: str | None = None,
        required_grade: str | None = None,
        work_format: str | None = None,
        salary_tax_type: str | None = None,
        min_salary: float | None = None,
        city: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Vacancy]:
        query = select(Vacancy).options(selectinload(Vacancy.employer)).where(Vacancy.is_published.is_(True))

        if specialization:
            query = query.where(Vacancy.specialization.ilike(f"%{specialization}%"))
        if required_grade:
            query = query.where(Vacancy.required_grade.ilike(f"%{required_grade}%"))
        if work_format:
            query = query.where(Vacancy.work_format == work_format)
        if salary_tax_type:
            query = query.where(Vacancy.salary_tax_type == salary_tax_type)
        if min_salary is not None:
            query = query.where(Vacancy.salary_max >= min_salary)
        if city:
            query = query.where(Vacancy.city.ilike(f"%{city}%"))

        query = query.order_by(Vacancy.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_employer_vacancies(
        db: AsyncSession,
        employer_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Vacancy]:
        profile = await db.get(EmployerProfile, employer_id)
        if profile is None:
            return []
        organization = await db.get(EmployerOrganization, profile.organization_id) if profile.organization_id else None
        if organization and organization.owner_user_id == user_id:
            query = select(Vacancy).join(
                EmployerProfile, EmployerProfile.id == Vacancy.employer_id
            ).where(EmployerProfile.organization_id == organization.id)
        else:
            query = select(Vacancy).outerjoin(
                VacancyAccess,
                (VacancyAccess.vacancy_id == Vacancy.id) & (VacancyAccess.user_id == user_id),
            ).where(or_(
                Vacancy.employer_id == employer_id,
                VacancyAccess.can_view.is_(True),
                VacancyAccess.can_edit.is_(True),
            ))
        result = await db.execute(
            query.options(selectinload(Vacancy.employer)).order_by(Vacancy.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_vacancy_by_id(
        db: AsyncSession,
        vacancy_id: uuid.UUID,
    ) -> Vacancy:
        result = await db.execute(
            select(Vacancy)
            .options(selectinload(Vacancy.employer))
            .where(Vacancy.id == vacancy_id)
        )
        vacancy = result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вакансия не найдена",
            )
        return vacancy

    @staticmethod
    async def apply_to_vacancy(
        db: AsyncSession,
        candidate_id: uuid.UUID,
        vacancy_id: uuid.UUID,
        data: ApplicationCreate,
    ) -> VacancyApplication:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        if not vacancy.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вакансия в данный момент закрыта для откликов",
            )
        employer_user = await db.get(User, vacancy.employer.user_id)
        if employer_user and not employer_user.is_active and employer_user.email.endswith("@example.test"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Это демонстрационная вакансия. Для настоящего отклика выберите действующую компанию.",
            )

        # Проверяем, не откликался ли уже кандидат
        existing = await db.execute(
            select(VacancyApplication).where(
                VacancyApplication.vacancy_id == vacancy_id,
                VacancyApplication.candidate_id == candidate_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже отправили отклик на эту вакансию",
            )

        application = VacancyApplication(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            cover_letter=data.cover_letter,
            status="pending",
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def get_candidate_applications(
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> list[dict]:
        result = await db.execute(
            select(VacancyApplication)
            .options(
                selectinload(VacancyApplication.vacancy).selectinload(Vacancy.employer)
            )
            .where(VacancyApplication.candidate_id == candidate_id)
            .order_by(VacancyApplication.created_at.desc())
        )
        applications = result.scalars().all()

        response = []
        for app_obj in applications:
            vac = app_obj.vacancy
            emp = vac.employer if vac else None
            response.append({
                "id": app_obj.id,
                "vacancy_id": app_obj.vacancy_id,
                "status": app_obj.status,
                "cover_letter": app_obj.cover_letter,
                "created_at": app_obj.created_at,
                "status_updated_at": app_obj.status_updated_at,
                "vacancy_title": vac.title if vac else "Неизвестно",
                "company_name": emp.company_name if emp else "Неизвестно",
                "salary_min": vac.salary_min if vac else 0.0,
                "salary_max": vac.salary_max if vac else 0.0,
                "salary_tax_type": vac.salary_tax_type if vac else "gross",
            })
        return response

    @staticmethod
    async def get_vacancy_applications(
        db: AsyncSession,
        user_id: uuid.UUID,
        vacancy_id: uuid.UUID,
    ) -> list[dict]:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        await VacancyService._permission(db, user_id, vacancy, edit=False)

        result = await db.execute(
            select(VacancyApplication)
            .options(
                selectinload(VacancyApplication.candidate).selectinload(CandidateProfile.user)
            )
            .where(VacancyApplication.vacancy_id == vacancy_id)
            .order_by(VacancyApplication.created_at.desc())
        )
        applications = result.scalars().all()

        response = []
        for app_obj in applications:
            cand = app_obj.candidate
            cand_user = cand.user if cand else None
            contact_info = {
                "candidate_id": cand.id if cand else uuid.uuid4(),
                "first_name": cand.first_name if cand else "",
                "last_name": cand.last_name if cand else "",
                "middle_name": cand.middle_name if cand else None,
                "email": cand_user.email if cand_user else "",
                "phone": cand.phone if cand else None,
                "telegram": cand.telegram if cand else None,
                "city": cand.city if cand else None,
                "github_url": cand.github_url if cand else None,
                "specialization": cand.specialization if cand else None,
                "declared_grade": cand.declared_grade if cand else None,
                "verified_grade": cand.verified_grade if cand else None,
                "skills": cand.skills if cand else [],
                "resume_text": cand.resume_text if cand else None,
            }
            response.append({
                "id": app_obj.id,
                "vacancy_id": app_obj.vacancy_id,
                "status": app_obj.status,
                "cover_letter": app_obj.cover_letter,
                "created_at": app_obj.created_at,
                "status_updated_at": app_obj.status_updated_at,
                "candidate": contact_info,
            })
        return response

    @staticmethod
    async def update_application_status(
        db: AsyncSession,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        new_status: str,
    ) -> VacancyApplication:
        result = await db.execute(
            select(VacancyApplication)
            .options(selectinload(VacancyApplication.vacancy))
            .where(VacancyApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отклик не найден",
            )

        await VacancyService._permission(db, user_id, application.vacancy, edit=True)

        application.status = new_status
        application.status_updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(application)
        return application
