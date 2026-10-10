import io
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from fastapi import HTTPException
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.models.candidate import CandidateProfile
from app.schemas.resume import ResumeParsedData
from app.services.resume_sanity import resume_warnings

EMPTY_RESUME_TEXT = (
    "Не удалось найти текст в PDF. Возможно, это скан, "
    "загрузите пдф с выделяемым текстом или заполните профиль вручную"
)

KNOWN_TECH_SKILLS = [
    "Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes",
    "AsyncIO", "SQLAlchemy", "Git", "React", "TypeScript", "JavaScript", "HTML",
    "CSS", "Tailwind", "Next.js", "Redux", "Linux", "CI/CD", "Kafka", "RabbitMQ",
    "Go", "Golang", "Java", "C++", "Rust", "Nginx", "ClickHouse", "MongoDB"
]


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
            raise HTTPException(status_code=400, detail=EMPTY_RESUME_TEXT)

        # Regex extractors
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", full_text)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r"(\+7|8)[\s\(\-]*\d{3}[\s\)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", full_text)
        phone = phone_match.group(0) if phone_match else None

        tg_match = re.search(r"@([A-Za-z0-9_]{4,32})|t\.me/([A-Za-z0-9_]{4,32})", full_text)
        telegram = tg_match.group(0) if tg_match else None
        if telegram and email and telegram.lstrip("@") in email:
            telegram = None

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
            warnings=resume_warnings(full_text),
        )

    @staticmethod
    def generate_candidate_profile_pdf(profile: CandidateProfile) -> bytes:
        if not profile.agreed_publication:
            raise HTTPException(status_code=403, detail="Для PDF-профиля разрешите публикацию профиля в настройках")

        font_paths = (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        )
        font_path = next((path for path in font_paths if path.is_file()), None)
        if font_path is None:
            raise RuntimeError("Для PDF-профиля нужен шрифт с поддержкой кириллицы")
        if "ProfileUnicode" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ProfileUnicode", str(font_path)))
            pdfmetrics.registerFontFamily("ProfileUnicode", normal="ProfileUnicode", bold="ProfileUnicode", italic="ProfileUnicode", boldItalic="ProfileUnicode")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="ProfileUnicode",
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Heading3"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#3B82F6"),
            fontName="ProfileUnicode",
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
            fontName="ProfileUnicode",
        )
        badge_style = ParagraphStyle(
            "DocBadge",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#065F46"),
            fontName="ProfileUnicode",
        )

        elements = []

        # Title
        full_name = escape(f"{profile.first_name or ''} {profile.last_name or ''}".strip() or "Кандидат платформы FSP")
        elements.append(Paragraph(full_name, title_style))
        elements.append(Spacer(1, 6))

        # Role & Grade
        grade_text = escape(profile.verified_grade or profile.declared_grade or "не указан")
        status_suffix = " (ПОДТВЕРЖДЁН ТЕСТОМ)" if profile.verified_grade else " (заявленный)"
        spec_text = f"{escape(profile.specialization or 'IT-специалист')} — {grade_text.upper()}{status_suffix}"
        elements.append(Paragraph(spec_text, subtitle_style))
        elements.append(Spacer(1, 14))

        # Meta Table
        data_info = [
            [Paragraph("<b>Город:</b>", body_style), Paragraph(escape(profile.city or "Не указан"), body_style)],
            [Paragraph("<b>Формат работы:</b>", body_style), Paragraph(escape((profile.work_format or "Не указан").capitalize()), body_style)],
        ]

        t_info = Table(data_info, colWidths=[120, 420])
        t_info.setStyle(TableStyle([
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 14))

        # FSP Section
        if profile.fsp_verified and profile.fsp_id:
            elements.append(Paragraph("<b>Спортивное программирование · демонстрационные данные ФСП</b>", subtitle_style))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<b>ФСП ID:</b> {escape(profile.fsp_id)} · тестовая запись, личность не проверена", badge_style))
            elements.append(Spacer(1, 6))

            if profile.fsp_achievements:
                ach_rows = [[
                    Paragraph("<b>Турнир</b>", body_style),
                    Paragraph("<b>Год</b>", body_style),
                    Paragraph("<b>Результат</b>", body_style),
                    Paragraph("<b>Разряд/Категория</b>", body_style),
                ]]
                for ach in profile.fsp_achievements:
                    ach_rows.append([
                        Paragraph(escape(ach.tournament_name), body_style),
                        Paragraph(str(ach.year), body_style),
                        Paragraph(escape(ach.rank_or_place), body_style),
                        Paragraph(escape(ach.sport_category or ""), body_style),
                    ])
                t_ach = Table(ach_rows, colWidths=[240, 50, 120, 130])
                t_ach.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E7FF")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                elements.append(t_ach)
                elements.append(Spacer(1, 14))

        # Skills & Tests
        elements.append(Paragraph("<b>Навыки, указанные кандидатом</b>", subtitle_style))
        elements.append(Spacer(1, 6))
        skills_str = escape(", ".join(profile.skills) if profile.skills else "Не указаны")
        elements.append(Paragraph(skills_str, body_style))
        elements.append(Spacer(1, 14))

        # Bio
        if profile.bio:
            elements.append(Paragraph("<b>О себе</b>", subtitle_style))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(escape(profile.bio), body_style))
            elements.append(Spacer(1, 14))

        # Footer Notice
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("<i>PDF-профиль для передачи по решению кандидата. Контакты в него не включены.</i>", ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.gray)))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


pdf_service = PDFService()
