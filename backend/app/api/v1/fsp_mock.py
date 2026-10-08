from fastapi import APIRouter
from app.schemas.fsp import FSPMockAthlete, FSPVerificationResult
from app.services.fsp_service import fsp_service

router = APIRouter(prefix="/fsp", tags=["FSP demo"])


@router.get(
    "/athletes",
    response_model=list[FSPMockAthlete],
    summary="Тестовые записи ФСП для демонстрации",
)
def get_athletes():
    return fsp_service.get_all_demo_athletes()


@router.get(
    "/verify/{fsp_id}",
    response_model=FSPVerificationResult,
    summary="Поиск ФСП ID в демонстрационных данных",
)
async def verify_fsp_id(fsp_id: str):
    return await fsp_service.verify_fsp_id(fsp_id)
