import io
import os
import re
from typing import Any
from fastapi import HTTPException
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.candidate import CandidateProfile
from app.schemas.resume import ResumeParsedData

KNOWN_TECH_SKILLS = [
    "Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes",
    "AsyncIO", "SQLAlchemy", "Git", "React", "TypeScript", "JavaScript", "HTML",
    "CSS", "Tailwind", "Next.js", "Redux", "Linux", "CI/CD", "Kafka", "RabbitMQ",
    "Go", "Golang", "Java", "C++", "Rust", "Nginx", "ClickHouse", "MongoDB"
]

# Unicode font registration with multi-platform fallbacks (Windows / Linux / Docker)
_FONT_INITIALIZED = False
_FONT_NAME = "Helvetica"
_FONT_BOLD_NAME = "Helvetica-Bold"


def _init_fonts() -> tuple[str, str]:
    global _FONT_INITIALIZED, _FONT_NAME, _FONT_BOLD_NAME
    if _FONT_INITIALIZED:
        return _FONT_NAME, _FONT_BOLD_NAME

    font_search_paths = [
        # Windows
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
        # Linux (Debian / Ubuntu / Docker / Alpine)
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    for reg_path, bold_path in font_search_paths:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont("FSP-Regular", reg_path))
                b_path = bold_path if os.path.exists(bold_path) else reg_path
                pdfmetrics.registerFont(TTFont("FSP-Bold", b_path))
                pdfmetrics.registerFontFamily("FSPFont", normal="FSP-Regular", bold="FSP-Bold")
                _FONT_NAME = "FSP-Regular"
                _FONT_BOLD_NAME = "FSP-Bold"
                _FONT_INITIALIZED = True
                return _FONT_NAME, _FONT_BOLD_NAME
            except Exception:
                continue

    _FONT_INITIALIZED = True
    return _FONT_NAME, _FONT_BOLD_NAME


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "Скрыто в соответствии со 152-ФЗ"
    user_part, domain = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[0] + "***" + user_part[-1]
    return f"{masked_user}@{domain}"


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return "Не указан"
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        return f"+7 ({digits[1:4]}) ***-**-{digits[-2:]}"
    return "Скрыто в соответствии со 152-ФЗ"


def _mask_telegram(telegram: str | None) -> str:
    if not telegram:
        return "Не указан"
    return "@*** (Скрыто до принятия приглашения)"


class PDFService:
    @staticmethod
    def parse_resume_pdf(file_bytes: bytes) -> ResumeParsedData:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text_pages = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n".join(text_pages).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Не удалось прочитать PDF файл: {str(e)}")

        if not full_text:
            return ResumeParsedData(text_preview="Пустой документ или скан без текстового слоя")

        # Regex extractors
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", full_text)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r"(\+7|8)[\s\(\-]*\d{3}[\s\)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", full_text)
        phone = phone_match.group(0) if phone_match else None

        tg_match = re.search(r"@([A-Za-z0-9_]{4,32})|t\.me/([A-Za-z0-9_]{4,32})", full_text)
        telegram = tg_match.group(0) if tg_match else None

        # Skill extractor
        lower_text = full_text.lower()
        extracted_skills = []
        for skill in KNOWN_TECH_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", lower_text):
                extracted_skills.append(skill)

        # Detect suggested grade
        suggested_grade = None
        if "senior" in lower_text or "ведущий" in lower_text or "сеньор" in lower_text:
            suggested_grade = "senior"
        elif "middle" in lower_text or "мидл" in lower_text:
            suggested_grade = "middle"
        elif "junior" in lower_text or "джуниор" in lower_text:
            suggested_grade = "junior"

        # Detect specialization
        specialization = None
        if "backend" in lower_text or "бэкенд" in lower_text or "python" in lower_text:
            specialization = "Backend"
        elif "frontend" in lower_text or "фронтенд" in lower_text or "react" in lower_text:
            specialization = "Frontend"
        elif "devops" in lower_text or "девопс" in lower_text or "sre" in lower_text:
            specialization = "DevOps / SRE"

        preview = full_text[:400] + ("..." if len(full_text) > 400 else "")

        return ResumeParsedData(
            email=email,
            phone=phone,
            telegram=telegram,
            specialization=specialization,
            suggested_grade=suggested_grade,
            extracted_skills=extracted_skills,
            text_preview=preview,
        )

    @staticmethod
    def generate_candidate_profile_pdf(
        profile: CandidateProfile,
        user_email: str,
        mask_contacts: bool = False,
    ) -> bytes:
        font_regular, font_bold = _init_fonts()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        title_style = ParagraphStyle(
            "DocTitle",
            fontName=font_bold,
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E3A8A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            fontName=font_bold,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2563EB"),
        )
        body_style = ParagraphStyle(
            "DocBody",
            fontName=font_regular,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
        )
        body_bold_style = ParagraphStyle(
            "DocBodyBold",
            fontName=font_bold,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
        )
        badge_style = ParagraphStyle(
            "DocBadge",
            fontName=font_bold,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#065F46"),
        )
        disclaimer_style = ParagraphStyle(
            "DocDisclaimer",
            fontName=font_regular,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6B7280"),
        )

        elements = []

        # Header Title
        full_name = f"{profile.first_name} {profile.last_name}".strip() or "Кандидат платформы FSP"
        elements.append(Paragraph(full_name, title_style))
        elements.append(Spacer(1, 4))

        # Specialization & Verified Grade (B-06, B-11, B-12)
        if profile.verified_grade:
            grade_badge = f"{profile.verified_grade.upper()} [ПОДТВЕРЖДЁН ОНЛАЙН-ТЕСТОМ]"
            grade_color = "#059669"
        else:
            declared = (profile.declared_grade or "junior").upper()
            grade_badge = f"{declared} [ЗАЯВЛЕННЫЙ — ТЕСТ НЕ ПРОЙДЕН]"
            grade_color = "#D97706"

        spec_line = (
            f"<font color='#1E3A8A'>{profile.specialization or 'IT-специалист'}</font> • "
            f"<font color='{grade_color}'><b>{grade_badge}</b></font>"
        )
        elements.append(Paragraph(spec_line, subtitle_style))
        elements.append(Spacer(1, 12))

        # Contacts & Privacy handling (152-FZ requirement: caller determines mask based on consent/application)
        effective_mask = mask_contacts

        if effective_mask:
            email_val = _mask_email(user_email)
            phone_val = _mask_phone(profile.phone)
            tg_val = _mask_telegram(profile.telegram)
        else:
            email_val = user_email
            phone_val = profile.phone or "Не указан"
            tg_val = profile.telegram or "Не указан"

        data_info = [
            [Paragraph("Город:", body_bold_style), Paragraph(profile.city or "Не указан", body_style)],
            [Paragraph("Формат работы:", body_bold_style), Paragraph((profile.work_format or "remote").capitalize(), body_style)],
            [Paragraph("Email (152-ФЗ):", body_bold_style), Paragraph(email_val, body_style)],
            [Paragraph("Телефон:", body_bold_style), Paragraph(phone_val, body_style)],
            [Paragraph("Telegram:", body_bold_style), Paragraph(tg_val, body_style)],
        ]
        if profile.github_url and not effective_mask:
            data_info.append([Paragraph("GitHub / Портфолио:", body_bold_style), Paragraph(profile.github_url, body_style)])

        t_info = Table(data_info, colWidths=[130, 410])
        t_info.setStyle(TableStyle([
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 14))

        # FSP Section (B-08: Explicit demo achievements indicator)
        if profile.fsp_verified and profile.fsp_id:
            elements.append(Paragraph("Спортивное программирование (Федерация спортивного программирования)", subtitle_style))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(f"ФСП ID: {profile.fsp_id} — ВЕРИФИЦИРОВАН [ДЕМО-РЕЕСТР]", badge_style))
            elements.append(Spacer(1, 2))
            elements.append(Paragraph("* Тестовые достижения демонстрационного стенда. Не меняют профессиональный грейд (согласно ТЗ).", disclaimer_style))
            elements.append(Spacer(1, 6))

            if profile.fsp_achievements:
                ach_rows = [[
                    Paragraph("Турнир", body_bold_style),
                    Paragraph("Год", body_bold_style),
                    Paragraph("Результат", body_bold_style),
                    Paragraph("Разряд/Категория", body_bold_style),
                ]]
                for ach in profile.fsp_achievements:
                    ach_rows.append([
                        Paragraph(ach.tournament_name, body_style),
                        Paragraph(str(ach.year), body_style),
                        Paragraph(ach.rank_or_place, body_style),
                        Paragraph(ach.sport_category or "Участник", body_style),
                    ])
                t_ach = Table(ach_rows, colWidths=[230, 50, 130, 130])
                t_ach.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                elements.append(t_ach)
                elements.append(Spacer(1, 14))

        # Verified Skills & Competencies
        elements.append(Paragraph("Стек технологий и подтверждённые компетенции", subtitle_style))
        elements.append(Spacer(1, 4))
        skills_str = ", ".join(profile.skills) if profile.skills else "Компетенции подтверждаются через тестирование платформы"
        elements.append(Paragraph(skills_str, body_style))
        elements.append(Spacer(1, 14))

        # Bio
        if profile.bio:
            elements.append(Paragraph("О себе", subtitle_style))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(profile.bio, body_style))
            elements.append(Spacer(1, 14))

        # 152-FZ Footer
        elements.append(Spacer(1, 10))
        notice_text = (
            "Сформировано платформой FSP.Career в строгом соответствии с 152-ФЗ РФ. "
            "Документ содержит только те сведения, публикацию которых явно одобрил субъект персональных данных."
        )
        elements.append(Paragraph(notice_text, disclaimer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


pdf_service = PDFService()
