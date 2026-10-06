from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.candidate import router as candidate_router
from app.api.v1.employer import router as employer_router
from app.api.v1.fsp_mock import router as fsp_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(candidate_router)
api_v1_router.include_router(employer_router)
api_v1_router.include_router(fsp_router)
