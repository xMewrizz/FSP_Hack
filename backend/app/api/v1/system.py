from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.services.seed_service import seed_service

router = APIRouter(prefix="/system", tags=["System & Demo Seeding"])


@router.post(
    "/seed",
    status_code=status.HTTP_201_CREATED,
    summary="Инициализировать базу тестовыми кандидатами, компаниями и вакансиями",
)
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    if not settings.ENABLE_DEMO_SEED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await seed_service.seed_all(db)
