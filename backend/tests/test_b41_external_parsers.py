from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.core.constants import UserRole
from app.core.security import create_access_token
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.user import User
from app.services.parsers.careerist_parser import CareeristParser
from app.services.parsers.experience_verifier import ExperienceVerifier
from app.services.parsers.habr_career_parser import HabrCareerParser
from app.services.parsers.profi_ru_parser import ProfiRuParser
from app.services.parsers.schemas import (
    ExperienceAuditStatus,
    ExternalWorkPeriod,
    ParsedExternalProfile,
)
from app.services.trust_score_service import calculate_trust_score


# --- Тесты парсера Хабр Карьеры ---

def test_habr_career_api_status_checks():
    # 1. Приложение не зарегистрировано
    check_no_app = HabrCareerParser.check_api_status(client_id=None)
    assert not check_no_app.app_registered
    assert not check_no_app.habr_activated
    assert not check_no_app.can_access_api
    assert "необходимо создать клиентское приложение" in check_no_app.legal_summary

    # 2. Зарегистрировано, но не активировано Хабром
    check_pending = HabrCareerParser.check_api_status(client_id="app_12345", is_activated=False)
    assert check_pending.app_registered
    assert not check_pending.habr_activated
    assert not check_pending.can_access_api
    assert "ожидает подтверждения и ручной активации" in check_pending.legal_summary

    # 3. Активировано
    check_active = HabrCareerParser.check_api_status(client_id="app_12345", is_activated=True)
    assert check_active.app_registered
    assert check_active.habr_activated
    assert "first_name" in check_active.returned_fields
    assert "companies" in check_active.returned_fields


def test_habr_career_api_payload_parsing():
    payload = {
        "user": {
            "username": "sultan_dev",
            "first_name": "Султан",
            "last_name": "Хабибов",
            "specialization": "Backend-разработчик",
            "city": "Москва",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "experiences": [
                {
                    "company_name": "ООО Финтех Системы",
                    "position": "Middle Python Developer",
                    "start_date": "2022-03-01",
                    "end_date": "2024-08-01",
                    "is_current": False,
                    "duration_months": 29,
                },
                {
                    "company_name": "Платформа Роста",
                    "position": "Senior Backend Developer",
                    "start_date": "2024-09-01",
                    "end_date": None,
                    "is_current": True,
                    "duration_months": 14,
                },
            ],
        }
    }
    profile = HabrCareerParser.parse_api_response(payload)
    assert profile.source == "habr_career"
    assert profile.full_name == "Султан Хабибов"
    assert profile.headline == "Backend-разработчик"
    assert len(profile.work_periods) == 2
    assert profile.total_experience_months == 43
    assert profile.work_periods[0].company == "ООО Финтех Системы"
    assert profile.work_periods[1].is_current is True
    assert "Python" in profile.skills


def test_habr_career_html_parsing():
    html_sample = """
    <html>
      <body>
        <h1 class="user-name">Александр Петров</h1>
        <div class="user-specialization">Senior Data Engineer</div>
        <div class="experience-item">
          <a class="company_name">VK</a>
          <div class="position">Data Engineer</div>
          <div class="date">сентябрь 2021 — настоящее время (2 года 1 месяц)</div>
        </div>
        <div class="experience-item">
          <a class="company_name">СберТех</a>
          <div class="position">Junior Python Developer</div>
          <div class="date">май 2019 — август 2021 (2 года 4 месяца)</div>
        </div>
        <a class="skill-tag">Python</a>
        <a class="skill-tag">Spark</a>
        <a class="skill-tag">PostgreSQL</a>
      </body>
    </html>
    """
    profile = HabrCareerParser.parse_html(html_sample, "https://career.habr.com/alex_petrov")
    assert profile.full_name == "Александр Петров"
    assert profile.headline == "Senior Data Engineer"
    assert len(profile.work_periods) == 2
    assert profile.work_periods[0].company == "VK"
    assert profile.work_periods[0].is_current is True
    assert profile.work_periods[1].company == "СберТех"
    assert "Spark" in profile.skills
    assert profile.total_experience_months > 40


# --- Тесты парсера Careerist ---

def test_careerist_access_and_terms_check():
    # Без авторизации работодателя
    guest_check = CareeristParser.check_access_and_terms(is_authorized_employer=False)
    assert guest_check.terms_of_use_verified
    assert not guest_check.captcha_bypass_attempted
    assert not guest_check.full_cv_access
    assert guest_check.access_level == "preview_snippets"
    assert "Отсутствие капчи не означает права" in guest_check.legal_summary

    # С авторизацией работодателя
    auth_check = CareeristParser.check_access_and_terms(is_authorized_employer=True)
    assert auth_check.full_cv_access
    assert auth_check.access_level == "authorized_employer_full"


def test_careerist_catalog_parsing():
    catalog_html = """
    <div class="cv-item">
      <h2 class="title">Программист Python / Django</h2>
      <div class="exp">Опыт работы: <strong>3 года 4 месяца</strong></div>
      <div class="company">Последнее место: <strong>ООО ТехноЛаб</strong></div>
      <div class="city">Город: <strong>Москва</strong></div>
      <a href="/cv/9821/">Посмотреть резюме</a>
    </div>
    <div class="cv-item">
      <h2 class="title">Junior Backend Developer</h2>
      <div class="exp">Опыт работы: <strong>10 месяцев</strong></div>
      <div class="company">Последнее место: <strong>Стартап ИТ</strong></div>
      <div class="city">Город: <strong>Казань</strong></div>
      <a href="/cv/9822/">Посмотреть резюме</a>
    </div>
    """
    items = CareeristParser.parse_cv_catalog(catalog_html)
    assert len(items) == 2
    assert items[0]["title"] == "Программист Python / Django"
    assert items[0]["experience_months"] == 40
    assert items[0]["latest_company"] == "ООО ТехноЛаб"
    assert items[1]["experience_months"] == 10


def test_careerist_cv_detail_parsing():
    detail_html = """
    <html>
      <h1>Иван Сидоров</h1>
      <div class="position">Ведущий разработчик Python</div>
      <div class="header-exp">Общий стаж: <strong>5 лет 2 месяца</strong></div>
      <div class="work-experience-item">
        <div class="company-name">Яндекс</div>
        <div class="job-title">Backend Developer</div>
        <div class="period">2021 — настоящее время</div>
      </div>
      <span class="skill-item">FastAPI</span>
      <span class="skill-item">Docker</span>
    </html>
    """
    profile = CareeristParser.parse_cv_detail(detail_html, "https://careerist.ru/cv/777/")
    assert profile.source == "careerist"
    assert profile.full_name == "Иван Сидоров"
    assert profile.total_experience_months >= 60
    assert "FastAPI" in profile.skills


# --- Тесты парсера Профи.ру ---

def test_profi_ru_policy_and_tutoring_protection():
    policy = ProfiRuParser.check_profi_policy()
    assert policy.is_freelance_or_tutoring is True
    assert policy.does_not_indicate_inflated_experience is True
    assert "ни при каких обстоятельствах не трактуется как признак накрутки опыта" in policy.legal_summary


def test_profi_ru_catalog_and_profile_parsing():
    catalog_html = """
    <div class="specialist-card">
      <h3 class="name">Елена Васильева</h3>
      <div class="rating">рейтинг: <strong>4.95</strong></div>
      <div class="orders">выполнено 42 заказа</div>
      <div class="exp">опыт: 4 года</div>
      <a href="/profile/elena_ml/">Анкета</a>
    </div>
    """
    items = ProfiRuParser.parse_specialist_catalog(catalog_html)
    assert len(items) == 1
    assert items[0]["name"] == "Елена Васильева"
    assert items[0]["rating"] == 4.95
    assert items[0]["orders_count"] == 42
    assert items[0]["experience_months"] == 48

    profile_html = """
    <html>
      <h1>Елена Васильева</h1>
      <div class="rating">4.95</div>
      <div class="orders">42 отзыва</div>
      <div class="service-name">Data Science</div>
      <div class="service-name">Репетитор по Python</div>
      <div class="exp">частная практика: 3 года</div>
    </html>
    """
    profile = ProfiRuParser.parse_profile(profile_html, "https://profi.ru/profile/elena_ml/")
    assert profile.source == "profi_ru"
    assert profile.is_freelance_or_part_time is True
    assert profile.rating == 4.95
    assert profile.orders_count == 42
    assert profile.total_experience_months == 36
    assert "Data Science" in profile.skills


# --- Тесты логики верификации опыта и статуса «возможно крутит опыт» ---

def test_verifier_honest_candidate():
    candidate_id = uuid.uuid4()
    # Кандидат заявляет Middle (3 года), Хабр Карьера подтверждает 3 года (36 месяцев)
    external_profile = ParsedExternalProfile(
        source="habr_career",
        source_name="Хабр Карьера",
        total_experience_months=36,
        work_periods=[
            ExternalWorkPeriod(
                company="ИТ Компания",
                role="Python Developer",
                start_date="2021-09",
                end_date="2024-09",
                duration_months=36,
            )
        ],
    )

    audit = ExperienceVerifier.verify_candidate_experience(
        candidate_id=candidate_id,
        declared_grade="middle",
        resume_text="Опыт работы с 2021 по 2024 год в ООО ИТ Компания",
        external_profiles=[external_profile],
    )

    assert audit.status == ExperienceAuditStatus.NORMAL
    assert not audit.is_flagged_for_inflation
    assert "возможно крутит опыт" not in audit.flags
    assert audit.discrepancy_months == 0


def test_verifier_inflated_experience_detected():
    candidate_id = uuid.uuid4()
    # Кандидат заявляет Senior (5+ лет, с 2019 года), но на Хабре опыт всего 10 месяцев (с конца 2024 года)
    external_profile = ParsedExternalProfile(
        source="habr_career",
        source_name="Хабр Карьера",
        total_experience_months=10,
        work_periods=[
            ExternalWorkPeriod(
                company="Стартап",
                role="Junior Developer",
                start_date="2024-11",
                end_date="настоящее время",
                duration_months=10,
            )
        ],
    )

    audit = ExperienceVerifier.verify_candidate_experience(
        candidate_id=candidate_id,
        declared_grade="senior",
        resume_text="Senior Developer c 2019 года по настоящее время. Опыт 5 лет.",
        external_profiles=[external_profile],
    )

    # СИСТЕМА ПРИСУЖДАЕТ СТАТУС «возможно крутит опыт»
    assert audit.status == ExperienceAuditStatus.POSSIBLY_INFLATED
    assert audit.is_flagged_for_inflation is True
    assert "возможно крутит опыт" in audit.flags
    assert any("существенно превышает" in r or "Нестыковка года" in r for r in audit.reasons)


def test_verifier_profi_ru_tutoring_does_not_flag_inflation():
    candidate_id = uuid.uuid4()
    # Кандидат имеет только профиль репетитора/фрилансера на Профи.ру
    profi_profile = ParsedExternalProfile(
        source="profi_ru",
        source_name="Профи.ру (Фриланс)",
        total_experience_months=24,
        is_freelance_or_part_time=True,
        rating=4.9,
        orders_count=20,
    )

    audit = ExperienceVerifier.verify_candidate_experience(
        candidate_id=candidate_id,
        declared_grade="middle",
        resume_text="Middle Data Scientist, 2022-2024",
        external_profiles=[profi_profile],
    )

    # ПОДРАБОТКА НА ПРОФИ.РУ НЕ ЯВЛЯЕТСЯ ЗАВЫШЕНИЕМ ОПЫТА!
    assert audit.status == ExperienceAuditStatus.NORMAL
    assert not audit.is_flagged_for_inflation
    assert "возможно крутит опыт" not in audit.flags
    assert any("Профи.ру" in r for r in audit.reasons)


# --- Тесты защиты приватности кандидата ---

def test_candidate_never_sees_inflated_experience_status():
    candidate_id = uuid.uuid4()
    external_profile = ParsedExternalProfile(
        source="habr_career",
        source_name="Хабр Карьера",
        total_experience_months=8,
    )
    audit = ExperienceVerifier.verify_candidate_experience(
        candidate_id=candidate_id,
        declared_grade="senior",
        resume_text="Опыт 6 лет с 2018 года",
        external_profiles=[external_profile],
    )

    # 1. В аудите статус присуждён
    assert audit.status == ExperienceAuditStatus.POSSIBLY_INFLATED

    # 2. Представление для кандидата СТРОГО ОЧИЩЕНО
    candidate_view = ExperienceVerifier.get_candidate_view(audit)
    candidate_data = candidate_view.model_dump()

    assert "возможно крутит опыт" not in str(candidate_data)
    assert "status" not in candidate_data or candidate_data.get("status") != ExperienceAuditStatus.POSSIBLY_INFLATED
    assert "is_flagged_for_inflation" not in candidate_data
    assert "reasons" not in candidate_data
    assert candidate_view.has_external_data is True


def test_trust_score_hides_suspicion_flag_from_candidate():
    now = datetime.now(timezone.utc)
    candidate = CandidateProfile(
        id=uuid.uuid4(),
        first_name="Тест",
        last_name="Тестов",
        verified_grade="Senior",
        fsp_verified=True,
        bio="Тестовый био",
        city="Москва",
        work_format="remote",
        last_active_at=now,
        resume_text="Работа 2018-2024 в компании ААА",
    )
    candidate.fsp_achievements = []
    candidate.test_sessions = []

    # Создаём аудит с накруткой опыта
    inflated_audit = ExperienceVerifier.verify_candidate_experience(
        candidate_id=candidate.id,
        declared_grade="senior",
        resume_text=candidate.resume_text,
        external_profiles=[
            ParsedExternalProfile(
                source="habr_career",
                source_name="Хабр Карьера",
                total_experience_months=6,
            )
        ],
    )
    assert inflated_audit.status == ExperienceAuditStatus.POSSIBLY_INFLATED

    # 1. Кандидатский просмотр (for_employer=False):
    cand_score, cand_flags = calculate_trust_score(candidate, for_employer=False, external_audit=inflated_audit)
    # Кандидат НЕ должен видеть флаг «Внешний опыт» или предупреждение о накрутке
    assert not any(f.get("label") == "Внешний опыт" for f in cand_flags)
    assert not any("крутит" in str(f) for f in cand_flags)

    # 2. Работодательский просмотр (for_employer=True):
    emp_score, emp_flags = calculate_trust_score(candidate, for_employer=True, external_audit=inflated_audit)
    # Работодатель ВИДИТ предупреждение
    ext_flag = next((f for f in emp_flags if f.get("label") == "Внешний опыт"), None)
    assert ext_flag is not None
    assert ext_flag["status"] == "warning"
    assert "Возможно крутит опыт" in ext_flag["detail"]


# --- Тесты API эндпоинта доступа работодателя / кандидата ---

@pytest.mark.asyncio
async def test_experience_audit_endpoint_permissions(client: AsyncClient):
    # 1. Создаём кандидата
    candidate_user = User(
        id=uuid.uuid4(),
        email="candidate_b41@example.com",
        hashed_password="hash",
        role=UserRole.CANDIDATE,
        is_active=True,
        is_verified=True,
    )
    candidate_profile = CandidateProfile(
        id=uuid.uuid4(),
        user_id=candidate_user.id,
        first_name="Иван",
        last_name="Кандидатов",
        declared_grade="senior",
        agreed_publication=True,
        visibility_public=True,
        agreed_osint=True,
        resume_text="Senior Developer с 2018 года. https://career.habr.com/ivankand",
    )

    # 2. Создаём работодателя
    employer_user = User(
        id=uuid.uuid4(),
        email="employer_b41@example.com",
        hashed_password="hash",
        role=UserRole.EMPLOYER,
        is_active=True,
        is_verified=True,
    )
    employer_profile = EmployerProfile(
        id=uuid.uuid4(),
        user_id=employer_user.id,
        company_name="ООО Работодатель",
        onboarding_completed=True,
    )

    from conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        session.add_all([candidate_user, candidate_profile, employer_user, employer_profile])
        await session.commit()

    candidate_token = create_access_token({"sub": str(candidate_user.id), "type": "access", "role": UserRole.CANDIDATE.value})
    employer_token = create_access_token({"sub": str(employer_user.id), "type": "access", "role": UserRole.EMPLOYER.value})

    # 3. Кандидат пытается вызвать аудит -> 403 Forbidden
    cand_resp = await client.get(
        f"/api/v1/employer/candidates/{candidate_profile.id}/experience-audit",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert cand_resp.status_code == 403
    assert "Недостаточно прав. Требуется роль: employer" in cand_resp.json()["detail"]

    # 4. Работодатель вызывает аудит -> 200 OK
    emp_resp = await client.get(
        f"/api/v1/employer/candidates/{candidate_profile.id}/experience-audit",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert emp_resp.status_code == 200
    data = emp_resp.json()
    assert data["candidate_id"] == str(candidate_profile.id)
    assert "status" in data
    assert "habr_check" in data
    assert "careerist_check" in data
    assert "profi_check" in data
    assert data["visible_to_candidate"] is False
