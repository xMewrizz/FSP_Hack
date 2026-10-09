from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.vacancy import Vacancy, VacancyApplication
from app.schemas.vacancy import (
    ApplicationCreate,
    CandidateContactInfo,
    CompanyShortInfo,
    VacancyCreate,
    VacancyResponse,
    VacancyUpdate,
)


class VacancyService:
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
        employer_id: uuid.UUID,
        vacancy_id: uuid.UUID,
        data: VacancyUpdate,
    ) -> Vacancy:
        result = await db.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id, Vacancy.employer_id == employer_id)
        )
        vacancy = result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вакансия не найдена или у вас нет прав на её изменение",
            )

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
        employer_id: uuid.UUID,
        vacancy_id: uuid.UUID,
    ) -> bool:
        result = await db.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id, Vacancy.employer_id == employer_id)
        )
        vacancy = result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вакансия не найдена или у вас нет прав на её удаление",
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
    ) -> list[Vacancy]:
        result = await db.execute(
            select(Vacancy)
            .options(selectinload(Vacancy.employer))
            .where(Vacancy.employer_id == employer_id)
            .order_by(Vacancy.created_at.desc())
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
        employer_id: uuid.UUID,
        vacancy_id: uuid.UUID,
    ) -> list[dict]:
        vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
        if vacancy.employer_id != employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к откликам этой вакансии (152-ФЗ)",
            )

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
        employer_id: uuid.UUID,
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

        if application.vacancy.employer_id != employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав на изменение этого отклика",
            )

        application.status = new_status
        application.status_updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(application)
        return application
