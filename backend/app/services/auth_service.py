from datetime import datetime, timedelta, timezone
import random
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import UserRole
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.token import EmailVerification, RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
    VerifyEmailRequest,
)


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, request: RegisterRequest) -> dict:
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже зарегистрирован",
            )

        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            role=request.role,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже зарегистрирован",
            )

        if request.role == UserRole.CANDIDATE:
            db.add(
                CandidateProfile(
                    user_id=user.id,
                    first_name="",
                    last_name="",
                    agreed_osint=request.agreed_osint,
                    agreed_osint_at=datetime.now(timezone.utc) if request.agreed_osint else None,
                    onboarding_completed=False,
                )
            )
        elif request.role == UserRole.EMPLOYER:
            db.add(
                EmployerProfile(
                    user_id=user.id,
                    company_name="Моя компания",
                    contact_person="",
                    onboarding_completed=False,
                )
            )

        code = f"{random.randint(100000, 999999)}"
        verification = EmailVerification(
            user_id=user.id,
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            is_used=False,
        )
        db.add(verification)
        await db.commit()

        return {
            "message": "Код подтверждения сформирован",
            "email": user.email,
            "verification_code": code,
        }

    @staticmethod
    async def verify_email(
        db: AsyncSession, request: VerifyEmailRequest, user_agent: str | None = None
    ) -> TokenResponse:
        stmt = (
            select(User)
            .options(
                selectinload(User.candidate_profile),
                selectinload(User.employer_profile),
            )
            .where(User.email == request.email)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        stmt_ver = (
            select(EmailVerification)
            .where(
                EmailVerification.user_id == user.id,
                EmailVerification.code == request.code,
                EmailVerification.is_used.is_(False),
                EmailVerification.expires_at > datetime.now(timezone.utc),
            )
            .order_by(EmailVerification.created_at.desc())
        )
        res_ver = await db.execute(stmt_ver)
        verification = res_ver.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или просроченный код подтверждения",
            )

        verification.is_used = True
        user.is_verified = True
        await db.flush()

        return await AuthService._create_user_tokens(db, user, user_agent)

    @staticmethod
    async def resend_code(db: AsyncSession, email: str) -> dict:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        code = f"{random.randint(100000, 999999)}"
        verification = EmailVerification(
            user_id=user.id,
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            is_used=False,
        )
        db.add(verification)
        await db.commit()

        return {
            "message": "Новый код подтверждения сформирован",
            "email": email,
            "verification_code": code,
        }

    @staticmethod
    async def login(
        db: AsyncSession, request: LoginRequest, user_agent: str | None = None
    ) -> TokenResponse:
        stmt = (
            select(User)
            .options(
                selectinload(User.candidate_profile),
                selectinload(User.employer_profile),
            )
            .where(User.email == request.email)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учётная запись деактивирована",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email не подтверждён",
            )

        return await AuthService._create_user_tokens(db, user, user_agent)

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession, raw_refresh_token: str, user_agent: str | None = None
    ) -> TokenResponse:
        payload = decode_token(raw_refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный refresh-токен",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Некорректный идентификатор в токене",
            )

        user_id = uuid.UUID(user_id_str)
        t_hash = hash_token(raw_refresh_token)

        stmt_token = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == t_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        res_token = await db.execute(stmt_token)
        token_record = res_token.scalar_one_or_none()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh-токен отозван или истёк",
            )

        token_record.revoked = True
        await db.flush()

        stmt_user = (
            select(User)
            .options(
                selectinload(User.candidate_profile),
                selectinload(User.employer_profile),
            )
            .where(User.id == user_id)
        )
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или заблокирован",
            )

        return await AuthService._create_user_tokens(db, user, user_agent)

    @staticmethod
    async def logout(db: AsyncSession, raw_refresh_token: str) -> dict:
        t_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == t_hash)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if token_record:
            token_record.revoked = True
            await db.commit()

        return {"message": "Успешный выход из системы"}

    @staticmethod
    async def get_me(db: AsyncSession, user: User) -> UserMeResponse:
        onboarding_completed = False
        profile_data = None

        if user.role == UserRole.CANDIDATE:
            stmt = (
                select(CandidateProfile)
                .options(selectinload(CandidateProfile.fsp_achievements))
                .where(CandidateProfile.user_id == user.id)
            )
            res = await db.execute(stmt)
            prof = res.scalar_one_or_none()
            if prof:
                onboarding_completed = prof.onboarding_completed
                profile_data = {
                    "id": str(prof.id),
                    "first_name": prof.first_name,
                    "last_name": prof.last_name,
                    "middle_name": prof.middle_name,
                    "phone": prof.phone,
                    "telegram": prof.telegram,
                    "city": prof.city,
                    "specialization": prof.specialization,
                    "declared_grade": prof.declared_grade,
                    "verified_grade": prof.verified_grade,
                    "work_format": prof.work_format,
                    "fsp_id": prof.fsp_id,
                    "fsp_verified": prof.fsp_verified,
                    "agreed_152_fz": prof.agreed_152_fz,
                    "agreed_osint": prof.agreed_osint,
                    "achievements_count": len(prof.fsp_achievements),
                }
        elif user.role == UserRole.EMPLOYER:
            stmt = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
            res = await db.execute(stmt)
            prof = res.scalar_one_or_none()
            if prof:
                onboarding_completed = prof.onboarding_completed
                profile_data = {
                    "id": str(prof.id),
                    "company_name": prof.company_name,
                    "description": prof.description,
                    "industry": prof.industry,
                    "website": prof.website,
                    "contact_person": prof.contact_person,
                    "phone": prof.phone,
                    "city": prof.city,
                }

        return UserMeResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            onboarding_completed=onboarding_completed,
            profile=profile_data,
        )

    @staticmethod
    async def _create_user_tokens(
        db: AsyncSession, user: User, user_agent: str | None = None
    ) -> TokenResponse:
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            user_agent=user_agent,
        )
        db.add(token_record)
        await db.commit()

        onboarding_completed = False
        if user.role == UserRole.CANDIDATE:
            stmt_cand = select(CandidateProfile.onboarding_completed).where(CandidateProfile.user_id == user.id)
            res_cand = await db.execute(stmt_cand)
            val = res_cand.scalar_one_or_none()
            if val is not None:
                onboarding_completed = val
        elif user.role == UserRole.EMPLOYER:
            stmt_emp = select(EmployerProfile.onboarding_completed).where(EmployerProfile.user_id == user.id)
            res_emp = await db.execute(stmt_emp)
            val = res_emp.scalar_one_or_none()
            if val is not None:
                onboarding_completed = val

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            email=user.email,
            is_verified=user.is_verified,
            onboarding_completed=onboarding_completed,
        )


auth_service = AuthService()
