from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import UserRole
from app.core.database import get_db
from app.models.candidate import CandidateProfile
from app.models.fsp import FSPAchievement
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.fsp import FSPMockAthlete, FSPVerificationResult
from app.services.auth_service import auth_service
from app.services.fsp_service import FSP_REGISTRY_FIXTURES, fsp_service

router = APIRouter(prefix="/fsp", tags=["FSP & Keycloak"])


@router.get(
    "/athletes",
    response_model=list[FSPMockAthlete],
    summary="Список спортсменов реестра ФСП",
)
def get_athletes():
    return fsp_service.get_all_demo_athletes()


@router.get(
    "/verify/{fsp_id}",
    response_model=FSPVerificationResult,
    summary="Верификация ФСП ID",
)
async def verify_fsp_id(fsp_id: str):
    return await fsp_service.verify_fsp_id(fsp_id)


@router.get(
    "/keycloak/userinfo",
    summary="Keycloak OIDC UserInfo endpoint",
)
async def keycloak_userinfo(fsp_id: str = Query("FSP-77-001")):
    v_res = await fsp_service.verify_fsp_id(fsp_id)
    if not v_res.found:
        raise HTTPException(status_code=404, detail="Спортсмен не найден")

    athlete_data = FSP_REGISTRY_FIXTURES[v_res.fsp_id]
    names = athlete_data["full_name"].split()
    first_name = names[0] if len(names) > 0 else ""
    last_name = names[1] if len(names) > 1 else ""

    return {
        "sub": f"keycloak-fsp-{fsp_id.lower()}",
        "preferred_username": fsp_id.lower(),
        "email": f"{fsp_id.lower()}@fsp-russia.ru",
        "email_verified": True,
        "given_name": first_name,
        "family_name": last_name,
        "fsp_id": v_res.fsp_id,
        "fsp_verified": True,
        "fsp_sport_category": athlete_data["sport_category"],
        "fsp_rating": athlete_data["rating"],
        "achievements": athlete_data["achievements"],
    }


@router.post(
    "/login-by-fsp-id",
    response_model=TokenResponse,
    summary="Авторизация через ФСП ID (Keycloak SSO)",
)
async def login_by_fsp_id(
    fsp_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    v_res = await fsp_service.verify_fsp_id(fsp_id)
    if not v_res.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Спортсмен с ID {fsp_id} не найден в реестре ФСП",
        )

    fsp_email = f"{fsp_id.lower()}@fsp-russia.ru"
    stmt = select(User).where(User.email == fsp_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    athlete_data = FSP_REGISTRY_FIXTURES[v_res.fsp_id]
    names = athlete_data["full_name"].split()
    first_name = names[0] if len(names) > 0 else "Спортсмен"
    last_name = names[1] if len(names) > 1 else "ФСП"

    if not user:
        user = User(
            email=fsp_email,
            hashed_password="oauth_managed_fsp_keycloak",
            role=UserRole.CANDIDATE,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        profile = CandidateProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            city=athlete_data.get("region", "Москва"),
            specialization="Backend",
            declared_grade="senior",
            verified_grade=None,  # Грейд подтверждается только тестом (ТЗ B-08)
            fsp_id=v_res.fsp_id,
            fsp_verified=True,
            agreed_152_fz=True,
            agreed_osint=True,
            onboarding_completed=True,
        )
        db.add(profile)
        await db.flush()

        for ach in v_res.achievements:
            achievement = FSPAchievement(
                candidate_profile_id=profile.id,
                fsp_id=v_res.fsp_id,
                tournament_name=ach.tournament_name,
                year=ach.year,
                rank_or_place=ach.rank_or_place,
                sport_category=ach.sport_category,
                score_or_rating=ach.score_or_rating,
                verified=True,
                is_demo=True,
                disclaimer="Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП",
            )
            db.add(achievement)
        await db.commit()

    return await auth_service._create_user_tokens(db, user, user_agent="FSP-Keycloak-OAuth")
