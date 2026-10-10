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
                "salary_expectation": 320000.0,
                "salary_tax_type": "gross",
                "fsp_id": "FSP-77-001",
                "fsp_verified": True,
                "skills": ["SQL & Транзакции", "AsyncIO & Конкурентность", "Распределённые системы & CAP", "PostgreSQL", "Docker"],
                "bio": "Мастер спорта по спортивному программированию РФ. Чемпион России 2025. Архитектор highload-бэкендов.",
                "mentor_available": True,
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
                "verified_grade": None,
                "work_format": "hybrid",
                "salary_expectation": 220000.0,
                "salary_tax_type": "gross",
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
                "verified_grade": None,
                "work_format": "remote",
                "salary_expectation": 160000.0,
                "salary_tax_type": "gross",
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
                "salary_expectation": 200000.0,
                "salary_tax_type": "net",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": ["SQL & Оптимизация индексов", "Кэширование & Redis", "Python", "FastAPI"],
                "bio": "Опытный бэкенд-разработчик. Кандидат без истории ФСП (успешно прошел все платформенные тесты).",
                "mentor_available": True,
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
                "verified_grade": None,
                "work_format": "remote",
                "salary_expectation": 300000.0,
                "salary_tax_type": "gross",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": ["Web Vitals & Архитектура", "React & Производительность", "Next.js", "Redux"],
                "bio": "Senior Frontend инженер. Архитектура дизайн-систем, Core Web Vitals, SSR.",
            },
        ]

        mock_profiles = [
            ("backend-middle-olga@example.ru", "Ольга", "Лебедева", "Backend", "middle", "Санкт-Петербург", "hybrid", 215000,
             ["Python", "FastAPI", "PostgreSQL", "Redis"], "Развиваю сервисы бронирования, отвечаю за API и стабильность данных.", True),
            ("backend-middle-egor@example.ru", "Егор", "Савин", "Backend", "middle", "Москва", "remote", 240000,
             ["Python", "Django", "PostgreSQL", "Celery", "Docker"], "Создаю сервисы для электронной коммерции и автоматизирую обработку заказов.", True),
            ("backend-middle-marina@example.ru", "Марина", "Беляева", "Backend", "middle", "Казань", "remote", 205000,
             ["Go", "gRPC", "Kafka", "PostgreSQL"], "Разрабатываю сервисы обмена событиями и помогаю команде улучшать наблюдаемость.", False),
            ("backend-middle-kirill@example.ru", "Кирилл", "Орлов", "Backend", "middle", "Екатеринбург", "hybrid", 225000,
             ["Python", "FastAPI", "SQL", "Redis", "Pytest"], "Работаю над API внутренней продуктовой платформы и качеством тестирования.", False),
            ("backend-senior-pavel@example.ru", "Павел", "Зайцев", "Backend", "senior", "Москва", "remote", 360000,
             ["Java", "Spring", "Kafka", "PostgreSQL", "Kubernetes"], "Проектирую распределённые системы и помогаю инженерам расти до самостоятельных лидов.", True),
            ("frontend-middle-olga@example.ru", "Ольга", "Романова", "Frontend", "middle", "Москва", "hybrid", 210000,
             ["TypeScript", "React", "HTML", "CSS", "Playwright"], "Создаю интерфейсы продуктовых сервисов и развиваю доступность компонентов.", True),
            ("devops-middle-timur@example.ru", "Тимур", "Гареев", "DevOps / SRE", "middle", "Новосибирск", "remote", 230000,
             ["Linux", "Docker", "Kubernetes", "CI/CD", "Prometheus"], "Автоматизирую поставку сервисов и дежурю за надёжность инфраструктуры.", True),
            ("qa-middle-irina@example.ru", "Ирина", "Киселёва", "QA / Testing", "middle", "Санкт-Петербург", "remote", 190000,
             ["Python", "Pytest", "Playwright", "API testing", "SQL"], "Строю автоматизацию проверок веб-продуктов и помогаю командам выпускать изменения увереннее.", False),
        ]
        for email, first_name, last_name, specialization, grade, city, work_format, salary, skills, bio, mentor_available in mock_profiles:
            candidates_data.append({
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": None,
                "telegram": None,
                "city": city,
                "specialization": specialization,
                "declared_grade": grade,
                "verified_grade": grade,
                "demo_test_percentage": 82,
                "work_format": work_format,
                "salary_expectation": float(salary),
                "salary_tax_type": "gross",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": skills,
                "bio": f"Вымышленный профиль для демо. {bio}",
                "mentor_available": mentor_available,
            })

        # Вымышленные профили для демонстрации разных направлений в Data Science.
        # Навыки в анкете указаны кандидатом; отдельные тесты по ним не выдумываем.
        ds_profiles = [
            ("ds-junior-anna@example.com", "Анна", "Морозова", "junior", "Казань", "remote", 130000,
             ["Python", "Pandas", "NumPy", "SQL", "Статистика", "Jupyter", "Matplotlib", "Git"],
             "Аналитика продукта и подготовка данных. Дополнительно: Jupyter и Matplotlib."),
            ("ds-junior-ilya@example.com", "Илья", "Егоров", "junior", "Москва", "hybrid", 150000,
             ["Python", "Pandas", "SQL", "A/B-тесты", "Seaborn", "PostgreSQL"],
             "Первые проекты в продуктовой аналитике. Дополнительно: Seaborn и PostgreSQL."),
            ("ds-junior-polina@example.com", "Полина", "Федорова", "junior", "Новосибирск", "remote", 120000,
             ["Python", "NumPy", "Pandas", "Scikit-learn", "SQL", "Plotly", "Git"],
             "Обработка табличных данных и базовые модели. Дополнительно: Plotly и Git."),
            ("ds-middle-marina@example.com", "Марина", "Соколова", "middle", "Санкт-Петербург", "remote", 250000,
             ["Python", "Pandas", "SQL", "A/B-тесты", "Scikit-learn", "Airflow", "ClickHouse", "Docker"],
             "Продуктовые эксперименты и пайплайны данных. Дополнительно: Airflow, ClickHouse и Docker."),
            ("ds-middle-daniil@example.com", "Даниил", "Орлов", "middle", "Москва", "hybrid", 270000,
             ["Python", "NumPy", "SQL", "Scikit-learn", "PyTorch", "OpenCV", "MLflow", "Docker"],
             "Компьютерное зрение и воспроизводимые эксперименты. Дополнительно: OpenCV и MLflow."),
            ("ds-middle-alina@example.com", "Алина", "Беляева", "middle", "Екатеринбург", "remote", 240000,
             ["Python", "Pandas", "SQL", "Статистика", "XGBoost", "PySpark", "FastAPI"],
             "Модели для табличных данных. Дополнительно: PySpark и FastAPI."),
            ("ds-senior-viktor@example.com", "Виктор", "Крылов", "senior", "Москва", "remote", 390000,
             ["Python", "SQL", "Статистика", "A/B-тесты", "Scikit-learn", "Causal inference", "Spark", "Airflow"],
             "Дизайн экспериментов и оценка причинного эффекта. Дополнительно: Spark и Airflow."),
            ("ds-senior-elizaveta@example.com", "Елизавета", "Романова", "senior", "Санкт-Петербург", "hybrid", 410000,
             ["Python", "SQL", "PyTorch", "Transformers", "NLP", "MLflow", "Kubernetes", "FastAPI"],
             "Модели обработки текста и вывод моделей в сервис. Дополнительно: MLflow и Kubernetes."),
            ("ds-senior-artem@example.com", "Артём", "Лебедев", "senior", "Нижний Новгород", "remote", 380000,
             ["Python", "SQL", "Scikit-learn", "PyTorch", "MLOps", "Kubeflow", "Docker", "CI/CD"],
             "Жизненный цикл ML-моделей и мониторинг качества. Дополнительно: Kubeflow и CI/CD."),
        ]
        for index, (email, first_name, last_name, grade, city, work_format, salary, skills, bio) in enumerate(ds_profiles):
            candidates_data.append({
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": None,
                "telegram": None,
                "city": city,
                "specialization": "Data Science / ML",
                "declared_grade": grade,
                "verified_grade": grade,
                "demo_test_percentage": (78, 82, 76, 84, 88, 80, 91, 94, 86)[index],
                "work_format": work_format,
                "salary_expectation": float(salary),
                "salary_tax_type": "gross",
                "fsp_id": None,
                "fsp_verified": False,
                "skills": skills,
                "bio": f"Вымышленный профиль для демо; результат теста сгенерирован. {bio}",
            })

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
                    verified_specialization=c["specialization"] if c["verified_grade"] else None,
                    verified_grade_updated_at=now if c["verified_grade"] else None,
                    work_format=c["work_format"],
                    salary_expectation=c.get("salary_expectation"),
                    salary_tax_type=c.get("salary_tax_type", "gross"),
                    skills=c["skills"],
                    fsp_id=c["fsp_id"],
                    fsp_verified=c["fsp_verified"],
                    agreed_152_fz=True,
                    agreed_152_fz_at=now,
                    agreed_publication=True,
                    agreed_publication_at=now,
                    visibility_public=True,
                    mentor_available=c.get("mentor_available", False),
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

                if c["verified_grade"]:
                    percentage = float(c.get("demo_test_percentage", 95.0))
                    session = TestSession(
                        user_id=user.id,
                        candidate_profile_id=profile.id,
                        specialization=c["specialization"],
                        target_grade=c["verified_grade"],
                        status="completed",
                        score=percentage,
                        max_score=100.0,
                        percentage=percentage,
                        passed=True,
                        feedback="Демонстрационный результат теста.",
                        completed_at=now,
                    )
                    db.add(session)
                candidate_profiles.append(profile)
            else:
                stmt_p = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
                res_p = await db.execute(stmt_p)
                p = res_p.scalar_one_or_none()
                if p:
                    if c.get("mentor_available") is True:
                        p.mentor_available = True
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
                            {"name": "AsyncIO & Конкурентность", "weight": 5.0, "required": True},
                            {"name": "SQL & Транзакции", "weight": 4.0, "required": True},
                            {"name": "Распределённые системы & CAP", "weight": 5.0, "required": True},
                            {"name": "PostgreSQL", "weight": 3.0, "required": True},
                        ],
                        "salary_min": 280000.0,
                        "salary_max": 420000.0,
                        "salary_tax_type": "gross",
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
                            {"name": "React & Производительность", "weight": 5.0, "required": True},
                            {"name": "JavaScript & Event Loop", "weight": 4.0, "required": True},
                            {"name": "TypeScript", "weight": 3.0, "required": True},
                        ],
                        "salary_min": 170000.0,
                        "salary_max": 250000.0,
                        "salary_tax_type": "gross",
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
                            {"name": "Linux & Сети", "weight": 5.0, "required": True},
                            {"name": "Docker & Контейнеризация", "weight": 4.0, "required": True},
                            {"name": "CI/CD", "weight": 3.0, "required": True},
                        ],
                        "salary_min": 140000.0,
                        "salary_max": 210000.0,
                        "salary_tax_type": "gross",
                        "currency": "RUB",
                        "work_format": "remote",
                        "city": "Москва",
                        "description": "Поддержка и автоматизация сред разработки и деплоя кластеров микросервисов.",
                    },
                    {
                        "title": "Middle Backend Developer (PostgreSQL / Redis)",
                        "specialization": "Backend",
                        "required_grade": "middle",
                        "required_skills": [
                            {"name": "SQL & Оптимизация индексов", "weight": 5.0, "required": True},
                            {"name": "Кэширование & Redis", "weight": 4.0, "required": True},
                            {"name": "Python", "weight": 5.0, "required": True},
                            {"name": "FastAPI", "weight": 4.0, "required": True},
                        ],
                        "salary_min": 180000.0,
                        "salary_max": 240000.0,
                        "salary_tax_type": "net",
                        "currency": "RUB",
                        "work_format": "office",
                        "city": "Москва",
                        "description": "Разработка платежного шлюза и высоконагруженных сервисов процессинга. Зарплата указана на руки («net»).",
                    },
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
                        salary_tax_type=nd.get("salary_tax_type", "gross"),
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

        if employer_profiles:
            employer = employer_profiles[0]
            mentor_emails = {item["email"] for item in candidates_data if item.get("mentor_available")}
            mentors = (await db.scalars(
                select(CandidateProfile)
                .join(User, User.id == CandidateProfile.user_id)
                .where(User.email.in_(mentor_emails))
            )).all()
            for index, mentor in enumerate(mentors):
                existing = await db.scalar(
                    select(Invitation.id).where(
                        Invitation.employer_id == employer.id,
                        Invitation.candidate_id == mentor.id,
                        Invitation.status == "accepted",
                    ).limit(1)
                )
                if existing:
                    continue
                db.add(Invitation(
                    employer_id=employer.id,
                    candidate_id=mentor.id,
                    need_id=None,
                    company_name=employer.company_name,
                    offer_description="Демонстрационная связь кандидата с компанией для показа HR-раздела наставников.",
                    contact_method="Контакт доступен после принятия приглашения",
                    salary_min=180000.0,
                    salary_max=320000.0,
                    currency="RUB",
                    status="accepted",
                    candidate_reply="Демонстрационный профиль связан с компанией.",
                    accepted_at=now,
                ))
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
