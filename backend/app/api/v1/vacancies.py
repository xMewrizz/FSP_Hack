from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate, get_current_employer, get_db
from app.models.user import User
from app.schemas.vacancy import (
    ApplicationCandidateResponse,
    ApplicationCreate,
    ApplicationEmployerResponse,
    ApplicationStatusUpdate,
    CompanyShortInfo,
    VacancyCreate,
    VacancyResponse,
    VacancyUpdate,
)
from app.services.vacancy_service import VacancyService

router = APIRouter(prefix="/vacancies", tags=["Vacancies & Candidate Applications (B-30)"])


def to_vacancy_response(v) -> VacancyResponse:
    company = None
    if v.employer:
        company = CompanyShortInfo(
            id=v.employer.id,
            company_name=v.employer.company_name,
            industry=v.employer.industry,
            website=v.employer.website,
            city=v.employer.city,
        )
    return VacancyResponse(
        id=v.id,
        employer_id=v.employer_id,
        title=v.title,
        specialization=v.specialization,
        required_grade=v.required_grade,
        required_skills=v.required_skills,
        salary_min=v.salary_min,
        salary_max=v.salary_max,
        salary_tax_type=v.salary_tax_type,
        currency=v.currency,
        work_format=v.work_format,
        city=v.city,
        description=v.description,
        is_published=v.is_published,
        created_at=v.created_at,
        updated_at=v.updated_at,
        company=company,
    )


@router.post(
    "",
    response_model=VacancyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Опубликовать вакансию (Работодатель)",
)
async def create_vacancy(
    data: VacancyCreate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль работодателя не заполнен",
        )
    vacancy = await VacancyService.create_vacancy(
        db, current_user.employer_profile.id, data
    )
    # Load employer relationship
    vacancy_with_emp = await VacancyService.get_vacancy_by_id(db, vacancy.id)
    return to_vacancy_response(vacancy_with_emp)


@router.get(
    "",
    response_model=list[VacancyResponse],
    summary="Поиск открытых вакансий по фильтрам",
)
async def list_vacancies(
    specialization: str | None = Query(None, description="Фильтр по специализации"),
    required_grade: str | None = Query(None, description="Фильтр по грейду"),
    work_format: str | None = Query(None, description="Формат: remote, office, hybrid"),
    salary_tax_type: Literal["gross", "net"] | None = Query(None, description="до вычета НДФЛ / на руки"),
    min_salary: float | None = Query(None, description="Минимальная зарплата"),
    city: str | None = Query(None, description="Город"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    vacancies = await VacancyService.get_vacancies(
        db=db,
        specialization=specialization,
        required_grade=required_grade,
        work_format=work_format,
        salary_tax_type=salary_tax_type,
        min_salary=min_salary,
        city=city,
        skip=skip,
        limit=limit,
    )
    return [to_vacancy_response(v) for v in vacancies]


@router.get(
    "/my",
    response_model=list[VacancyResponse],
    summary="Список вакансий текущей компании (Работодатель)",
)
async def get_my_vacancies(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        return []
    vacancies = await VacancyService.get_employer_vacancies(
        db, current_user.employer_profile.id
    )
    return [to_vacancy_response(v) for v in vacancies]


@router.get(
    "/applications/my",
    response_model=list[ApplicationCandidateResponse],
    summary="Мои отклики на вакансии (Кандидат)",
)
async def get_my_applications(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        return []
    return await VacancyService.get_candidate_applications(
        db, current_user.candidate_profile.id
    )


@router.get(
    "/{vacancy_id}",
    response_model=VacancyResponse,
    summary="Получить детальную информацию о вакансии",
)
async def get_vacancy(
    vacancy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
    return to_vacancy_response(vacancy)


@router.patch(
    "/{vacancy_id}",
    response_model=VacancyResponse,
    summary="Обновить вакансию (Работодатель)",
)
async def update_vacancy(
    vacancy_id: uuid.UUID,
    data: VacancyUpdate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль не найден")
    vacancy = await VacancyService.update_vacancy(
        db, current_user.employer_profile.id, vacancy_id, data
    )
    return to_vacancy_response(vacancy)


@router.delete(
    "/{vacancy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить вакансию (Работодатель)",
)
async def delete_vacancy(
    vacancy_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль не найден")
    await VacancyService.delete_vacancy(
        db, current_user.employer_profile.id, vacancy_id
    )
    return None


@router.post(
    "/{vacancy_id}/apply",
    response_model=ApplicationCandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Откликнуться на вакансию (Кандидат)",
)
async def apply_to_vacancy(
    vacancy_id: uuid.UUID,
    data: ApplicationCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.candidate_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль кандидата не заполнен",
        )
    application = await VacancyService.apply_to_vacancy(
        db, current_user.candidate_profile.id, vacancy_id, data
    )
    vacancy = await VacancyService.get_vacancy_by_id(db, vacancy_id)
    company_name = vacancy.employer.company_name if vacancy.employer else "Неизвестно"
    return ApplicationCandidateResponse(
        id=application.id,
        vacancy_id=vacancy.id,
        status=application.status,
        cover_letter=application.cover_letter,
        created_at=application.created_at,
        status_updated_at=application.status_updated_at,
        vacancy_title=vacancy.title,
        company_name=company_name,
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        salary_tax_type=vacancy.salary_tax_type,
    )


@router.get(
    "/{vacancy_id}/applications",
    response_model=list[ApplicationEmployerResponse],
    summary="Список кандидатов, откликнувшихся на вакансию (Работодатель, 152-ФЗ)",
)
async def get_vacancy_applications(
    vacancy_id: uuid.UUID,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль не найден")
    return await VacancyService.get_vacancy_applications(
        db, current_user.employer_profile.id, vacancy_id
    )


@router.patch(
    "/applications/{application_id}/status",
    summary="Изменить статус отклика кандидата (Работодатель)",
)
async def update_application_status(
    application_id: uuid.UUID,
    data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.employer_profile:
        raise HTTPException(status_code=400, detail="Профиль не найден")
    updated = await VacancyService.update_application_status(
        db, current_user.employer_profile.id, application_id, data.status
    )
    return {
        "status": "ok",
        "application_id": updated.id,
        "new_status": updated.status,
        "status_updated_at": updated.status_updated_at,
    }
