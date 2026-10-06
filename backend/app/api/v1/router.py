from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.candidate import router as candidate_router
from app.api.v1.employer import router as employer_router
from app.api.v1.fsp_mock import router as fsp_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.matching import router as matching_router
from app.api.v1.needs import router as needs_router
from app.api.v1.resume import router as resume_router
from app.api.v1.system import router as system_router
from app.api.v1.testing import router as testing_router

api_v1_router = APIRouter()

# Auth & System
api_v1_router.include_router(auth_router)
api_v1_router.include_router(fsp_router)
api_v1_router.include_router(system_router)

# Candidate routes (support both singular and plural)
api_v1_router.include_router(candidate_router, prefix="/candidate")
api_v1_router.include_router(candidate_router, prefix="/candidates")
api_v1_router.include_router(resume_router, prefix="/candidate")
api_v1_router.include_router(resume_router, prefix="/candidates")

# Employer routes (support both singular and plural)
api_v1_router.include_router(employer_router, prefix="/employer")
api_v1_router.include_router(employer_router, prefix="/employers")

# Core reverse hiring, testing, needs, and matching
api_v1_router.include_router(testing_router)
api_v1_router.include_router(needs_router)
api_v1_router.include_router(matching_router)
api_v1_router.include_router(invitations_router)
