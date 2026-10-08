from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import UserRole
from app.core.security import hash_password
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.fsp import FSPAchievement
from app.models.invitation import Invitation
from app.models.need import EmployerNeed
from app.models.test import TestSession
from app.models.user import User
from app.services.fsp_service import FSP_REGISTRY_FIXTURES
from app.services.testing_service import testing_service


class SeedService:
    @staticmethod
    async def seed_all(db: AsyncSession) -> dict[str, Any]:
        # 1. Ensure question bank is seeded
        await testing_service.ensure_questions_seeded(db)

        now = datetime.now(timezone.utc)

        # 2. Seed Candidates
        candidates_data = [
            {
                "email": "alex@fsp.ru",
                "first_name": "Алексей",
                "last_name": "Смирнов",
                "phone": "+7 (999) 111-22-33",
                "telegram": "@alex_smirnov",
                "city": "Москва",
                "specialization": "Backend",
                "declared_grade": "senior",
                "verified_grade": "senior",
                "work_format": "remote",
                "fsp_id": "FSP-77-001",
                "fsp_verified": True,
                "skills": ["SQL & Транзакции", "AsyncIO & Конкурентность", "Распределённые системы & CAP", "PostgreSQL", "Docker"],
                "bio": "Мастер спорта по спортивному программированию РФ. Чемпион России 2025. Архитектор highload-бэкендов.",
            },
            {
                "email": "kate@fsp.ru",
                "first_name": "Екатерина",
                "last_name": "Кузнецова",
                "phone": "+7 (999) 222-33-44",
                "telegram": "@kate_kuznetsova",
                "city": "Санкт-Петербург",
                "specialization": "Frontend",
                "declared_grade": "middle",
                "verified_grade": "middle",
                "work_format": "hybrid",
                "fsp_id": "FSP-78-042",
                "fsp_verified": True,
                "skills": ["JavaScript & Event Loop", "React & Производительность", "TypeScript", "Tailwind"],
                "bio": "КМС по спортивному программированию. Победитель Кубка Санкт-Петербурга 2025. Специализация — React и Web Vitals.",
            },
            {
                "email": "dmitry@fsp.ru",
                "first_name": "Дмитрий",
                "last_name": "Волков",
                "phone": "+7 (999) 333-44-55",
                "telegram": "@dmitry_volkov",
                "city": "Новосибирск",
                "specialization": "DevOps / SRE",
                "declared_grade": "junior",
                "verified_grade": "junior",
                "work_format": "remote",
                "fsp_id": "FSP-54-105",
                "fsp_verified": True,
                "skills": ["Linux & Сети", "Docker & Контейнеризация", "Bash", "CI/CD"],
                "bio": "1-й разряд ФСП. Сибирский турнир 2025. Настройка инфраструктуры, Linux, автоматизация деплоя.",
            },
            {
                "email": "ivan@tech.ru",
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+7 (999) 444-55-66",
                "telegram": "@ivan_petrov_dev",
                "city": "Москва",
                "specialization": "Backend",
                "declared_grade": "middle",
                "verified_grade": "middle",
                "work_format": "office",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": ["SQL & Оптимизация индексов", "Кэширование & Redis", "Python", "FastAPI"],
                "bio": "Опытный бэкенд-разработчик. Кандидат без истории ФСП (успешно прошел все платформенные тесты).",
            },
            {
                "email": "maria@frontend.ru",
                "first_name": "Мария",
                "last_name": "Сидорова",
                "phone": "+7 (999) 555-66-77",
                "telegram": "@maria_frontend",
                "city": "Екатеринбург",
                "specialization": "Frontend",
                "declared_grade": "senior",
                "verified_grade": "senior",
                "work_format": "remote",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": ["Web Vitals & Архитектура", "React & Производительность", "Next.js", "Redux"],
                "bio": "Senior Frontend инженер. Архитектура дизайн-систем, Core Web Vitals, SSR.",
            },
        ]

        candidate_profiles = []
        for c in candidates_data:
            stmt = select(User).where(User.email == c["email"])
            res = await db.execute(stmt)
            user = res.scalar_one_or_none()
            if not user:
                user = User(
                    email=c["email"],
                    hashed_password=hash_password("Password123!"),
                    role=UserRole.CANDIDATE,
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                await db.flush()

                profile = CandidateProfile(
                    user_id=user.id,
                    first_name=c["first_name"],
                    last_name=c["last_name"],
                    phone=c["phone"],
                    telegram=c["telegram"],
                    city=c["city"],
                    bio=c["bio"],
                    specialization=c["specialization"],
                    declared_grade=c["declared_grade"],
                    verified_grade=c["verified_grade"],
                    verified_grade_updated_at=now,
                    work_format=c["work_format"],
                    skills=c["skills"],
                    fsp_id=c["fsp_id"],
                    fsp_verified=c["fsp_verified"],
                    agreed_152_fz=True,
                    agreed_152_fz_at=now,
                    agreed_publication=True,
                    agreed_publication_at=now,
                    visibility_public=True,
                    agreed_osint=True,
                    agreed_osint_at=now,
                    onboarding_completed=True,
                )
                db.add(profile)
                await db.flush()

                # Add FSP achievements if present
                if c["fsp_id"] and c["fsp_id"] in FSP_REGISTRY_FIXTURES:
                    fsp_data = FSP_REGISTRY_FIXTURES[c["fsp_id"]]
                    for ach in fsp_data["achievements"]:
                        achievement = FSPAchievement(
                            candidate_profile_id=profile.id,
                            fsp_id=c["fsp_id"],
                            tournament_name=ach["tournament_name"],
                            year=ach["year"],
                            rank_or_place=ach["rank_or_place"],
                            sport_category=ach["sport_category"],
                            score_or_rating=ach["score_or_rating"],
                            verified=True,
                        )
                        db.add(achievement)

                # Add test session
                session = TestSession(
                    user_id=user.id,
                    candidate_profile_id=profile.id,
                    specialization=c["specialization"],
                    target_grade=c["verified_grade"] or "junior",
                    status="completed",
                    score=95.0,
                    max_score=100.0,
                    percentage=95.0,
                    passed=True,
                    feedback="Тест успешно сдан с отличием.",
                    completed_at=now,
                )
                db.add(session)
                candidate_profiles.append(profile)
            else:
                stmt_p = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
                res_p = await db.execute(stmt_p)
                p = res_p.scalar_one_or_none()
                if p:
                    candidate_profiles.append(p)

        # 3. Seed Employers
        employers_data = [
            {
                "email": "hr@yandex-team.ru",
                "company_name": "Яндекс Технологии",
                "description": "Ведущая технологическая компания, создающая умные продукты и сервисы на основе искусственного интеллекта и передового бэкенда.",
                "industry": "IT & Telecom",
                "website": "https://yandex.ru",
                "contact_person": "Анна Соколова (Tech Lead HR)",
                "phone": "+7 (495) 739-70-00",
                "city": "Москва",
                "needs": [
                    {
                        "title": "Senior Backend Python Developer (Highload)",
                        "specialization": "Backend",
                        "required_grade": "senior",
                        "required_skills": [
                            {"name": "AsyncIO & Конкурентность", "weight": 1.5, "required": True},
                            {"name": "SQL & Оптимизация индексов", "weight": 1.2, "required": True},
                            {"name": "Распределённые системы & CAP", "weight": 2.0, "required": True},
                        ],
                        "salary_min": 280000.0,
                        "salary_max": 420000.0,
                        "currency": "RUB",
                        "work_format": "remote",
                        "city": "Москва",
                        "description": "Разработка распределенного ядра высоконагруженных сервисов. Ищем экспертов с глубоким пониманием асинхронности и алгоритмической базы.",
                    },
                    {
                        "title": "Middle Frontend Developer (React / Web Vitals)",
                        "specialization": "Frontend",
                        "required_grade": "middle",
                        "required_skills": [
                            {"name": "React & Производительность", "weight": 1.5, "required": True},
                            {"name": "JavaScript & Event Loop", "weight": 1.0, "required": True},
                        ],
                        "salary_min": 170000.0,
                        "salary_max": 250000.0,
                        "currency": "RUB",
                        "work_format": "hybrid",
                        "city": "Москва",
                        "description": "Разработка интерфейсов пользовательских сервисов Яндекса с упором на скорость загрузки и надежность.",
                    },
                ],
            },
            {
                "email": "hr@tbank.ru",
                "company_name": "Т-Банк Финтех",
                "description": "Финтех-экосистема номер один. Создаем передовые финансовые технологии и инженерную культуру.",
                "industry": "FinTech / Banking",
                "website": "https://tbank.ru",
                "contact_person": "Михаил Григорьев",
                "phone": "+7 (495) 648-11-11",
                "city": "Москва",
                "needs": [
                    {
                        "title": "DevOps Engineer / SRE",
                        "specialization": "DevOps / SRE",
                        "required_grade": "junior",
                        "required_skills": [
                            {"name": "Linux & Сети", "weight": 1.0, "required": True},
                            {"name": "Docker & Контейнеризация", "weight": 1.5, "required": True},
                        ],
                        "salary_min": 140000.0,
                        "salary_max": 210000.0,
                        "currency": "RUB",
                        "work_format": "remote",
                        "city": "Москва",
                        "description": "Поддержка и автоматизация сред разработки и деплоя кластеров микросервисов.",
                    }
                ],
            },
        ]

        employer_profiles = []
        created_needs = []

        for ed in employers_data:
            stmt = select(User).where(User.email == ed["email"])
            res = await db.execute(stmt)
            user = res.scalar_one_or_none()
            if not user:
                user = User(
                    email=ed["email"],
                    hashed_password=hash_password("Password123!"),
                    role=UserRole.EMPLOYER,
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                await db.flush()

                emp_profile = EmployerProfile(
                    user_id=user.id,
                    company_name=ed["company_name"],
                    description=ed["description"],
                    industry=ed["industry"],
                    website=ed["website"],
                    contact_person=ed["contact_person"],
                    phone=ed["phone"],
                    city=ed["city"],
                    onboarding_completed=True,
                )
                db.add(emp_profile)
                await db.flush()
                employer_profiles.append(emp_profile)

                for nd in ed["needs"]:
                    need = EmployerNeed(
                        employer_id=emp_profile.id,
                        title=nd["title"],
                        specialization=nd["specialization"],
                        required_grade=nd["required_grade"],
                        required_skills=nd["required_skills"],
                        salary_min=nd["salary_min"],
                        salary_max=nd["salary_max"],
                        currency=nd["currency"],
                        work_format=nd["work_format"],
                        city=nd["city"],
                        description=nd["description"],
                        is_active=True,
                    )
                    db.add(need)
                    created_needs.append(need)
            else:
                stmt_ep = select(EmployerProfile).where(EmployerProfile.user_id == user.id)
                res_ep = await db.execute(stmt_ep)
                ep = res_ep.scalar_one_or_none()
                if ep:
                    employer_profiles.append(ep)

        await db.commit()

        # 4. Seed sample invitations
        if employer_profiles and candidate_profiles:
            emp = employer_profiles[0]
            cand1 = candidate_profiles[0]  # Alex Smirnov
            cand2 = candidate_profiles[1]  # Kate Kuznetsova

            stmt_inv = select(Invitation).where(Invitation.employer_id == emp.id)
            res_inv = await db.execute(stmt_inv)
            if not res_inv.scalars().first():
                inv1 = Invitation(
                    employer_id=emp.id,
                    candidate_id=cand1.id,
                    need_id=created_needs[0].id if created_needs else None,
                    company_name=emp.company_name,
                    offer_description="Здравствуйте, Алексей! Ваш профиль в реестре ФСП и подтверждённый Senior-грейд идеально подходят под задачи нашей платформенной команды. Предлагаем позицию Senior Python Архитектора.",
                    contact_method="Telegram: @yandex_lead_hr, email: hr@yandex-team.ru",
                    salary_min=320000.0,
                    salary_max=400000.0,
                    currency="RUB",
                    status="accepted",
                    candidate_reply="Добрый день! Предложение очень интересно, готов пообщаться.",
                    accepted_at=now,
                )
                inv2 = Invitation(
                    employer_id=emp.id,
                    candidate_id=cand2.id,
                    need_id=created_needs[1].id if len(created_needs) > 1 else None,
                    company_name=emp.company_name,
                    offer_description="Екатерина, здравствуйте! Приглашаем на позицию Middle Frontend разработчика в команду клиентских интерфейсов.",
                    contact_method="email: kate-invite@yandex-team.ru",
                    salary_min=180000.0,
                    salary_max=240000.0,
                    currency="RUB",
                    status="sent",
                )
                db.add(inv1)
                db.add(inv2)
                await db.commit()

        return {
            "message": "Демонстрационный набор данных успешно инициализирован",
            "candidates_seeded": len(candidates_data),
            "employers_seeded": len(employers_data),
            "credentials_hint": {
                "candidates": ["alex@fsp.ru", "kate@fsp.ru", "dmitry@fsp.ru", "ivan@tech.ru"],
                "employers": ["hr@yandex-team.ru", "hr@tbank.ru"],
                "password_for_all": "Password123!",
            },
        }


seed_service = SeedService()
