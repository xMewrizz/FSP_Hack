import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_candidate, get_current_user, get_db
from app.core.constants import UserRole
from app.models.candidate import CandidateProfile
from app.models.user import User
from app.schemas.resume import ResumeParsedData
from app.services.pdf_service import pdf_service

router = APIRouter(tags=["Candidate PDF & Resume Tools"])


@router.post(
    "/resume/upload",
    response_model=ResumeParsedData,
    summary="Загрузить PDF-резюме и извлечь данные для предзаполнения формы",
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Поддерживается только формат PDF")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 10 МБ")

    parsed_data = pdf_service.parse_resume_pdf(content)

    # Save raw text preview to candidate profile
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if profile:
        profile.resume_text = parsed_data.text_preview
        if parsed_data.extracted_skills:
            current_skills = set(profile.skills or [])
            current_skills.update(parsed_data.extracted_skills)
            profile.skills = list(current_skills)
        await db.commit()

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
