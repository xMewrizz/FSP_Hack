import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_candidate, get_current_user, get_db
from app.core.constants import UserRole
from app.models.candidate import CandidateProfile
from app.models.user import User
from app.schemas.resume import ResumeParsedData, ResumeVersionItem
from app.models.resume_version import ResumeVersion
from app.services.resume_versions import changed_roles, changed_work_lines
from app.services.candidate_photo_service import MAX_PHOTO_SIZE, candidate_photo_service
from app.services.candidate_service import candidate_service
from app.services.pdf_service import pdf_service

router = APIRouter(tags=["Candidate PDF & Resume Tools"])


@router.get("/resume/versions", response_model=list[ResumeVersionItem], summary="История сохранённых резюме")
async def list_resume_versions(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль кандидата не найден")
    return await _load_resume_versions(db, profile.id)


async def _load_resume_versions(db: AsyncSession, profile_id: uuid.UUID) -> list[ResumeVersionItem]:
    versions = (await db.scalars(
        select(ResumeVersion).where(ResumeVersion.candidate_profile_id == profile_id)
        .order_by(ResumeVersion.created_at, ResumeVersion.id)
    )).all()
    result = []
    prior: list[str] = []
    prior_text = ""
    for index, version in enumerate(versions):
        changes = changed_work_lines(prior, version.work_lines) if index else {"added": [], "removed": []}
        result.append(ResumeVersionItem(
            id=version.id, created_at=version.created_at,
            work_lines=version.work_lines,
            role_changes=changed_roles(prior_text, version.text) if index else [],
            **changes,
        ))
        prior = version.work_lines
        prior_text = version.text
    return list(reversed(result))


@router.get("/{candidate_id}/resume/versions", response_model=list[ResumeVersionItem], summary="История резюме опубликованного кандидата")
async def list_published_resume_versions(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.EMPLOYER or not current_user.is_verified:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    profile = await db.scalar(select(CandidateProfile).where(
        CandidateProfile.id == candidate_id,
        CandidateProfile.agreed_publication.is_(True),
        CandidateProfile.visibility_public.is_(True),
        CandidateProfile.onboarding_completed.is_(True),
    ))
    if profile is None:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return await _load_resume_versions(db, profile.id)


@router.delete("/resume/versions", status_code=204, summary="Удалить сохранённые версии резюме")
async def delete_resume_versions(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль кандидата не найден")
    await db.execute(delete(ResumeVersion).where(ResumeVersion.candidate_profile_id == profile.id))
    profile.resume_text = None
    await db.commit()


@router.post(
    "/profile/photo",
    summary="Загрузить фото профиля кандидата",
)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read(MAX_PHOTO_SIZE + 1)
    if len(content) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="Размер фотографии не должен превышать 5 МБ.")
    extension, _ = candidate_photo_service.detect_format(content)

    profile = await db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль кандидата не найден.")

    new_filename = candidate_photo_service.save(content, extension)
    old_filename = profile.photo_filename
    profile.photo_filename = new_filename
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        candidate_photo_service.delete(new_filename)
        raise

    candidate_photo_service.delete(old_filename)
    return await candidate_service.get_profile(db, current_user)


@router.delete(
    "/profile/photo",
    summary="Удалить фото профиля кандидата",
)
async def delete_profile_photo(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль кандидата не найден.")
    old_filename = profile.photo_filename
    profile.photo_filename = None
    await db.commit()
    candidate_photo_service.delete(old_filename)
    return await candidate_service.get_profile(db, current_user)


@router.get(
    "/profile/photo",
    summary="Получить собственное фото профиля кандидата",
)
async def get_my_profile_photo(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Фото не найдено.")
    content, media_type = candidate_photo_service.read(profile.photo_filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{candidate_id}/photo",
    summary="Получить опубликованное фото кандидата",
)
async def get_candidate_photo(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуется подтверждение email.")
    profile = await db.scalar(
        select(CandidateProfile)
        .options(selectinload(CandidateProfile.user))
        .where(CandidateProfile.id == candidate_id)
    )
    if profile is None or profile.user is None:
        raise HTTPException(status_code=404, detail="Фото не найдено.")

    is_owner = current_user.role == UserRole.CANDIDATE and profile.user_id == current_user.id
    is_public_to_employers = (
        current_user.role == UserRole.EMPLOYER
        and profile.user.is_verified
        and profile.agreed_publication
        and profile.visibility_public
        and profile.onboarding_completed
    )
    if not (is_owner or is_public_to_employers):
        raise HTTPException(status_code=404, detail="Фото не найдено.")

    content, media_type = candidate_photo_service.read(profile.photo_filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/resume/upload",
    response_model=ResumeParsedData,
    summary="Загрузить PDF-резюме и извлечь данные для предзаполнения формы",
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Поддерживается только формат PDF")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 10 МБ")

    parsed_data = pdf_service.parse_resume_pdf(content)

    return parsed_data


@router.get(
    "/profile/pdf",
    summary="Скачать стандартизированный PDF-профиль текущего кандидата",
)
async def download_my_profile_pdf(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CandidateProfile)
        .options(selectinload(CandidateProfile.fsp_achievements))
        .where(CandidateProfile.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Профиль кандидата не найден")

    pdf_bytes = pdf_service.generate_candidate_profile_pdf(profile)

    filename = "fsp_candidate_profile.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{candidate_id}/pdf",
    summary="Скачать стандартизированный PDF-профиль кандидата по ID (Работодатель, 152-ФЗ)",
)
async def download_candidate_pdf_by_id(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.fsp_achievements),
            selectinload(CandidateProfile.user),
        )
        .where(CandidateProfile.id == candidate_id)
    )
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    if current_user.id != profile.user_id:
        if current_user.role != UserRole.EMPLOYER or not profile.agreed_publication or not profile.visibility_public:
            raise HTTPException(status_code=404, detail="Кандидат не найден")

    pdf_bytes = pdf_service.generate_candidate_profile_pdf(profile)

    filename = "fsp_candidate_profile.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
