import { useEffect, useMemo, useRef, useState, type DragEvent as ReactDragEvent, type FormEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { apiGet, apiPost, apiPut, apiRequest, clearSession, saveSession } from "./api";
import {
  ALL_GRADES,
  ALL_SPECIALIZATIONS,
  TEST_AVAILABILITY_HINT,
  isTestablePair,
} from "./catalog";

type Candidate = {
  id: number;
  backendId?: string;
  achievementsCount?: number;
  fspVerified?: boolean;
  verifiedGrade?: boolean;
  matchedSkills?: string[];
  missingSkills?: string[];
  requestedSkillTests?: RequestedSkillTest[];
  availableFrom?: string | null;
  trueScore?: number | null;
  trueScoreFlags?: Array<{ label: string; status: "verified" | "review" | "warning"; detail: string }>;
  resumeVersions?: Array<{ id: string; label: string; date: string; summary: string }>;
  initials: string;
  name: string;
  role: string;
  level: string;
  score: number;
  salary: string;
  location: string;
  format: string;
  experience: string;
  updated: string;
  trust: number;
  skills: string[];
  radar: number[];
  jobRadar: number[];
  achievements: string[];
  summary: string;
  gap: string;
  about: string;
  email: string;
  telegram: string;
  education: string;
  experienceItems: { period: string; company: string; position: string; description: string }[];
};

const candidates: Candidate[] = [
  {
    id: 1,
    initials: "АМ",
    name: "Алексей Морозов",
    role: "Backend-разработчик",
    level: "Middle",
    score: 94,
    salary: "220–280 тыс. ₽",
    location: "Москва",
    format: "Удалённо",
    experience: "4 года",
    updated: "2 дня назад",
    trust: 0.92,
    skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    radar: [8, 9, 8, 7, 6, 7],
    jobRadar: [8, 8, 8, 7, 7, 7],
    achievements: ["Призёр ИТМО 2024", "Финалист хакатона ФСП"],
    summary:
      "Подтверждён Middle. Сильные API и базы данных, опыт высоконагруженных сервисов. Профиль актуален.",
    gap: "CI/CD: 6 из 7",
    about: "Проектирую и развиваю backend-сервисы для финансовых продуктов. Люблю задачи на производительность, надёжность и понятную архитектуру.",
    email: "alexey.morozov@example.ru",
    telegram: "@alexey_backend",
    education: "МГТУ им. Н. Э. Баумана · Программная инженерия · 2020",
    experienceItems: [
      { period: "2022 — сейчас", company: "FinCore", position: "Backend-разработчик", description: "Развитие платёжного API, оптимизация PostgreSQL, обработка до 8 млн событий в сутки." },
      { period: "2020 — 2022", company: "DataLab", position: "Junior Python Developer", description: "Сервисы аналитики на Django и Celery, покрытие кода тестами." },
    ],
  },
  {
    id: 2,
    initials: "ЕС",
    name: "Елена Смирнова",
    role: "Backend-разработчик",
    level: "Middle",
    score: 89,
    salary: "200–260 тыс. ₽",
    location: "Санкт-Петербург",
    format: "Гибрид",
    experience: "3,5 года",
    updated: "5 дней назад",
    trust: 0.88,
    skills: ["Go", "gRPC", "PostgreSQL", "Kafka", "Kubernetes"],
    radar: [8, 8, 7, 8, 7],
    jobRadar: [8, 8, 8, 7, 7],
    achievements: ["Топ-10 Codeforces ФСП"],
    summary:
      "Подтверждён Middle. Сильные алгоритмы и распределённые системы. Регулярная задача пройдена 5 дней назад.",
    gap: "Базы данных: 7 из 8",
    about: "Backend-инженер с фокусом на Go и распределённые системы. Проектирую сервисы, устойчивые к росту нагрузки и отказам.",
    email: "elena.smirnova@example.ru",
    telegram: "@elena_golang",
    education: "ИТМО · Информационные системы · 2021",
    experienceItems: [
      { period: "2023 — сейчас", company: "CloudLine", position: "Go-разработчик", description: "Микросервисы, gRPC, Kafka и Kubernetes. Снизила время ответа критичного API на 34%." },
      { period: "2021 — 2023", company: "Retail Systems", position: "Backend Developer", description: "Сервисы каталога и управления остатками." },
    ],
  },
  {
    id: 3,
    initials: "ДК",
    name: "Дмитрий Ким",
    role: "Backend-разработчик",
    level: "Middle",
    score: 84,
    salary: "190–240 тыс. ₽",
    location: "Казань",
    format: "Удалённо",
    experience: "3 года",
    updated: "12 дней назад",
    trust: 0.76,
    skills: ["Python", "Django", "PostgreSQL", "Celery", "GitLab CI"],
    radar: [7, 8, 8, 6, 7, 7],
    jobRadar: [8, 8, 8, 7, 7, 7],
    achievements: [],
    summary:
      "Подтверждён Middle. Уверенная работа с API и данными. Опыт участия в соревнованиях ФСП не найден.",
    gap: "Алгоритмы: 6 из 7",
    about: "Разрабатываю продуктовые сервисы на Python. Сильные стороны — базы данных, фоновые задачи и интеграции.",
    email: "dmitry.kim@example.ru",
    telegram: "@dmitry_codes",
    education: "КФУ · Прикладная информатика · 2022",
    experienceItems: [
      { period: "2022 — сейчас", company: "MarketHub", position: "Python Developer", description: "Django-сервисы маркетплейса, Celery, PostgreSQL и GitLab CI." },
      { period: "2021 — 2022", company: "WebCraft", position: "Стажёр-разработчик", description: "Внутренние инструменты и REST API." },
    ],
  },
  {
    id: 4,
    initials: "АП",
    name: "Анна Петрова",
    role: "Backend-разработчик",
    level: "Senior",
    score: 91,
    salary: "280–350 тыс. ₽",
    location: "Новосибирск",
    format: "Удалённо",
    experience: "7 лет",
    updated: "сегодня",
    trust: 0.95,
    skills: ["Java", "Spring", "Kafka", "PostgreSQL", "Kubernetes"],
    radar: [9, 8, 9, 8, 8, 8],
    jobRadar: [8, 8, 8, 7, 7, 7],
    achievements: ["Победитель хакатона ФСП 2023"],
    summary: "Подтверждён Senior. Сильная архитектура сервисов, данные и эксплуатация. Профиль обновлён сегодня.",
    gap: "Значимых разрывов нет",
    about: "Технический лидер backend-команд. Проектирую нагруженные системы и помогаю разработчикам расти.",
    email: "anna.petrova@example.ru",
    telegram: "@anna_arch",
    education: "НГУ · Информатика · 2018",
    experienceItems: [
      { period: "2021 — сейчас", company: "ScaleBank", position: "Senior Backend Developer", description: "Архитектура кредитного конвейера, Kafka, Kubernetes, команда из 6 разработчиков." },
      { period: "2018 — 2021", company: "Siberian Tech", position: "Java Developer", description: "Интеграционные сервисы и обработка платежей." },
    ],
  },
  {
    id: 5,
    initials: "МИ",
    name: "Максим Иванов",
    role: "Backend-разработчик",
    level: "Middle",
    score: 82,
    salary: "190–250 тыс. ₽",
    location: "Екатеринбург",
    format: "Гибрид",
    experience: "4 года",
    updated: "3 дня назад",
    trust: 0.81,
    skills: ["Node.js", "TypeScript", "NestJS", "PostgreSQL", "Redis"],
    radar: [8, 8, 7, 7, 7, 6],
    jobRadar: [8, 8, 8, 7, 7, 7],
    achievements: [],
    summary: "Подтверждён Middle. Хорошая работа с API и TypeScript, уверенное тестирование.",
    gap: "CI/CD: 6 из 7",
    about: "Создаю backend для веб-продуктов на TypeScript. Ценю строгую типизацию, тесты и понятные контракты.",
    email: "maxim.ivanov@example.ru",
    telegram: "@max_nest",
    education: "УрФУ · Программная инженерия · 2020",
    experienceItems: [
      { period: "2022 — сейчас", company: "EdTech Pro", position: "Backend Developer", description: "API образовательной платформы, NestJS, PostgreSQL и Redis." },
      { period: "2020 — 2022", company: "Digital Office", position: "Node.js Developer", description: "Корпоративные сервисы и интеграции." },
    ],
  },
  {
    id: 6,
    initials: "СВ",
    name: "Софья Волкова",
    role: "Backend-разработчик",
    level: "Junior",
    score: 76,
    salary: "130–170 тыс. ₽",
    location: "Томск",
    format: "Удалённо",
    experience: "1,5 года",
    updated: "вчера",
    trust: 0.9,
    skills: ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Pytest"],
    radar: [7, 7, 6, 7, 7, 5],
    jobRadar: [7, 7, 7, 6, 6, 5],
    achievements: ["Призёр олимпиады ФСП 2024"],
    summary: "Подтверждён Junior. Быстро растёт, сильные алгоритмы и тестирование.",
    gap: "Инфраструктура: 5 из 7",
    about: "Начинающий backend-разработчик. Участвую в олимпиадах и развиваю практические навыки на продуктовых задачах.",
    email: "sofia.volkova@example.ru",
    telegram: "@sofia_python",
    education: "ТГУ · Компьютерные науки · 2025",
    experienceItems: [
      { period: "2024 — сейчас", company: "StartLab", position: "Junior Backend Developer", description: "FastAPI-сервисы, тестирование и работа с PostgreSQL." },
    ],
  },
  {
    id: 7,
    initials: "РГ",
    name: "Роман Гусев",
    role: "DevOps-инженер",
    level: "Middle",
    score: 79,
    salary: "220–290 тыс. ₽",
    location: "Москва",
    format: "Гибрид",
    experience: "5 лет",
    updated: "6 дней назад",
    trust: 0.87,
    skills: ["Kubernetes", "Terraform", "GitLab CI", "Prometheus", "Linux"],
    radar: [8, 6, 7, 7, 8, 9],
    jobRadar: [7, 7, 7, 7, 7, 8],
    achievements: ["Участник DevOps Challenge ФСП"],
    summary: "Подтверждён Middle DevOps. Сильная инфраструктура, мониторинг и автоматизация поставки.",
    gap: "Разработка API: 6 из 7",
    about: "Автоматизирую инфраструктуру и поставку приложений. Работаю с Kubernetes-кластерами и наблюдаемостью.",
    email: "roman.gusev@example.ru",
    telegram: "@roman_sre",
    education: "МИРЭА · Информационные технологии · 2019",
    experienceItems: [
      { period: "2021 — сейчас", company: "InfraCloud", position: "DevOps Engineer", description: "Kubernetes, Terraform, GitLab CI и observability для 40 сервисов." },
      { period: "2019 — 2021", company: "HostPro", position: "System Engineer", description: "Linux-инфраструктура и мониторинг." },
    ],
  },
  {
    id: 8,
    initials: "НО",
    name: "Никита Орлов",
    role: "Backend-разработчик",
    level: "Middle",
    score: 80,
    salary: "210–270 тыс. ₽",
    location: "Самара",
    format: "Удалённо",
    experience: "4,5 года",
    updated: "8 дней назад",
    trust: 0.73,
    skills: ["Go", "REST", "ClickHouse", "RabbitMQ", "Docker"],
    radar: [8, 8, 7, 7, 6, 7],
    jobRadar: [8, 8, 8, 7, 7, 7],
    achievements: [],
    summary: "Подтверждён Middle. Сильные Go и API, опыт аналитических хранилищ.",
    gap: "Тестирование: 6 из 7",
    about: "Разрабатываю сервисы сбора и обработки данных на Go, работаю с очередями и ClickHouse.",
    email: "nikita.orlov@example.ru",
    telegram: "@nikita_go",
    education: "Самарский университет · Прикладная математика · 2020",
    experienceItems: [
      { period: "2021 — сейчас", company: "AdMetrics", position: "Go Developer", description: "Сервисы аналитики, ClickHouse, RabbitMQ и Docker." },
      { period: "2020 — 2021", company: "LocalSoft", position: "Backend Developer", description: "REST API и интеграции." },
    ],
  },
];

const labels = ["Язык", "API", "БД", "Алгоритмы", "Тесты", "CI/CD"];

const SPECIALTY_RADAR_SAMPLES = [
  {
    specialization: "Backend",
    labels: ["Язык и runtime", "API и интеграции", "Базы данных", "Алгоритмы", "Тестирование", "Надёжность"],
    values: [7.8, 7.2, 8.1, 6.9, 7.4, 6.8],
  },
  {
    specialization: "Frontend",
    labels: ["JavaScript", "UI и доступность", "Архитектура", "Тестирование", "Производительность"],
    values: [8.2, 7.6, 6.8, 7.1, 7.3],
  },
  {
    specialization: "Data Science / ML",
    labels: ["Python и данные", "Статистика", "Модели ML", "Эксперименты", "Инженерия данных", "Продуктовая оценка"],
    values: [7.4, 6.7, 7.9, 7.1, 6.8, 7.2],
  },
  {
    specialization: "QA / Testing",
    labels: ["Тест-дизайн", "Автоматизация", "API и данные", "Процессы QA", "Надёжность"],
    values: [8.1, 7.3, 6.8, 7.7, 7.1],
  },
];

const CAREER_PATHS: Record<string, Array<{ specialization: string; signals: string[]; description: string }>> = {
  Backend: [
    { specialization: "Fullstack", signals: ["frontend", "javascript", "typescript", "react", "ui"], description: "Соедините серверную разработку с интерфейсами продукта." },
    { specialization: "DevOps / SRE", signals: ["docker", "ci/cd", "kubernetes", "linux", "облако"], description: "Попробуйте инфраструктуру, автоматизацию и надёжность сервисов." },
    { specialization: "Data Science / ML", signals: ["python", "данные", "sql", "статистика", "ml"], description: "Исследуйте обработку данных и прикладные модели." },
  ],
  Frontend: [
    { specialization: "Fullstack", signals: ["api", "backend", "node", "базы данных", "sql"], description: "Расширьте интерфейсный опыт серверной логикой и API." },
    { specialization: "Mobile", signals: ["react", "typescript", "javascript", "ui", "доступность"], description: "Перенесите опыт интерфейсов на мобильные приложения." },
    { specialization: "QA / Testing", signals: ["тесты", "тестирование", "автоматизация", "доступность", "ui"], description: "Используйте знание интерфейсов для качества и автоматизации тестов." },
  ],
  Fullstack: [
    { specialization: "Backend", signals: ["api", "базы данных", "sql", "надёжность"], description: "Углубитесь в серверную архитектуру и хранение данных." },
    { specialization: "Frontend", signals: ["javascript", "typescript", "react", "ui"], description: "Сфокусируйтесь на пользовательских интерфейсах и доступности." },
    { specialization: "DevOps / SRE", signals: ["docker", "ci/cd", "linux", "надёжность"], description: "Попробуйте эксплуатацию и автоматизацию полного цикла." },
  ],
  Mobile: [
    { specialization: "Frontend", signals: ["ui", "react", "typescript", "доступность"], description: "Исследуйте веб-интерфейсы и общие подходы к UI." },
    { specialization: "Fullstack", signals: ["api", "backend", "sql", "интеграции"], description: "Добавьте серверную часть к мобильным продуктам." },
    { specialization: "QA / Testing", signals: ["тесты", "тестирование", "автоматизация", "ui"], description: "Попробуйте тестирование приложений и автоматизацию проверок." },
  ],
  "DevOps / SRE": [
    { specialization: "Backend", signals: ["api", "python", "go", "надёжность", "базы данных"], description: "Углубитесь в сервисы, для которых вы строите инфраструктуру." },
    { specialization: "System Programming / C++", signals: ["linux", "сети", "производительность", "c++"], description: "Исследуйте системное ПО, сети и производительность." },
    { specialization: "Data Science / ML", signals: ["данные", "python", "ml", "облако"], description: "Попробуйте платформы и инфраструктуру для данных и ML." },
  ],
  "Data Science / ML": [
    { specialization: "Backend", signals: ["python", "api", "sql", "надёжность"], description: "Превратите модели и данные в надёжные сервисы." },
    { specialization: "DevOps / SRE", signals: ["docker", "облако", "ci/cd", "автоматизация"], description: "Попробуйте инфраструктуру и доставку ML-систем." },
    { specialization: "QA / Testing", signals: ["тесты", "эксперименты", "данные", "автоматизация"], description: "Исследуйте качество данных, экспериментов и моделей." },
  ],
  "QA / Testing": [
    { specialization: "Backend", signals: ["api", "sql", "базы данных", "автоматизация"], description: "Используйте опыт проверок, чтобы глубже изучить API и сервисы." },
    { specialization: "Frontend", signals: ["ui", "доступность", "javascript", "typescript"], description: "Перейдите от проверки интерфейсов к их созданию." },
    { specialization: "Mobile", signals: ["ui", "тестирование", "автоматизация"], description: "Попробуйте качество мобильных приложений." },
  ],
  "System Programming / C++": [
    { specialization: "Backend", signals: ["сети", "api", "производительность", "надёжность"], description: "Примените системное мышление к серверным платформам." },
    { specialization: "GameDev", signals: ["c++", "производительность", "графика"], description: "Исследуйте движки, графику и разработку игр." },
    { specialization: "DevOps / SRE", signals: ["linux", "сети", "автоматизация", "надёжность"], description: "Попробуйте эксплуатацию систем и инженерную надёжность." },
  ],
  GameDev: [
    { specialization: "System Programming / C++", signals: ["c++", "производительность", "графика"], description: "Углубитесь в движки и системную оптимизацию." },
    { specialization: "Frontend", signals: ["ui", "javascript", "typescript", "доступность"], description: "Перенесите игровой UI-опыт в веб-продукты." },
    { specialization: "Mobile", signals: ["ui", "c++", "тестирование"], description: "Попробуйте мобильные приложения и игры." },
  ],
};

function getCareerPathSuggestions(specialization: string | null | undefined, skills: string[]) {
  const paths = CAREER_PATHS[specialization ?? ""] ?? CAREER_PATHS.Backend;
  const evidence = skills.map((skill) =>
    ` ${skill.toLowerCase().replace(/[^a-zа-я0-9+#]+/gi, " ").trim()} `,
  );
  return paths.map((path) => {
    const matchedSignals = path.signals.filter((signal) => {
      const normalizedSignal = ` ${signal.toLowerCase().replace(/[^a-zа-я0-9+#]+/gi, " ").trim()} `;
      return evidence.some((skill) => skill.includes(normalizedSignal));
    });
    return { ...path, matchedSignals };
  }).sort((left, right) => right.matchedSignals.length - left.matchedSignals.length);
}

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  role: "candidate" | "employer";
  onboarding_completed: boolean;
};

const DEMO_ACCOUNTS = {
  candidate: "alex@fsp.ru",
  employer: "hr@yandex-team.ru",
} as const;
const DEMO_PASSWORD = "Password123!";

const EMPLOYER_PAGES = ["Обзор", "Подборка", "Банк кандидатов", "Потребности", "Диалоги", "Приглашения", "Вакансии компании", "Аналитика", "Настройки"];
const CANDIDATE_PAGES = ["Обзор", "Профиль", "Тестирование", "Мой грейд", "Задания", "Диалоги", "Приглашения", "Вакансии", "Настройки"];

function pageForRole(page: string, role: "employer" | "candidate") {
  const allowedPages = role === "employer" ? EMPLOYER_PAGES : CANDIDATE_PAGES;
  return allowedPages.includes(page) ? page : role === "employer" ? "Подборка" : "Обзор";
}

function formatSalaryRange(minimum: number, maximum: number) {
  if (minimum % 1000 === 0 && maximum % 1000 === 0) {
    return `${minimum / 1000}–${maximum / 1000} тыс. ₽`;
  }
  const format = new Intl.NumberFormat("ru-RU");
  return `${format.format(minimum)}–${format.format(maximum)} ₽`;
}

type MatchingCandidate = {
  candidate_id: string;
  first_name: string;
  last_name: string;
  specialization: string | null;
  verified_grade: string | null;
  declared_grade: string | null;
  city: string | null;
  work_format: string | null;
  salary_expectation?: number | null;
  salary_tax_type?: "gross" | "net" | null;
  fsp_verified: boolean;
  available_from?: string | null;
  trust_score?: number | null;
  trust_flags?: Array<{ label: string; status: "verified" | "review" | "warning"; detail: string }>;
  resume_versions?: Array<{ id: string; label: string; date: string; summary: string }>;
  achievements_count: number;
  skills: string[];
  match_score: number;
  requested_skill_tests: RequestedSkillTest[];
  match_explanation: {
    summary: string;
    matched_skills: string[];
    missing_skills: string[];
    salary_match?: boolean | null;
    salary_note?: string | null;
  };
};

type RequestedSkillTest = {
  name: string;
  weight: number;
  percentage: number | null;
  test_grade: string | null;
  test_kind: "base" | "additional" | null;
  completed_at: string | null;
};

type EmployerNeedRecord = {
  id: string;
  title: string;
  specialization: string;
  required_grade: string;
  required_skills?: Array<{ name: string; weight: number; required?: boolean }>;
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
  currency: string;
  work_format: string;
  city: string | null;
  is_active: boolean;
};

type NeedDraft = {
  source: "llm";
  specialization: string | null;
  required_grade: string | null;
  required_skills: Array<{ name: string; weight: number }>;
  salary_min: number | null;
  salary_max: number | null;
  salary_tax_type: "gross" | "net" | null;
  work_format: string | null;
};

type BankFilters = {
  query: string;
  skill: string;
  specialization: string;
  grade: string;
  format: string;
  city: string;
  fspOnly: boolean;
};

type VacancyRecord = {
  id: string;
  title: string;
  specialization: string;
  required_grade: string;
  required_skills: string[];
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
  work_format: string;
  city: string | null;
  description: string;
  is_published: boolean;
  company?: { company_name: string; city: string | null } | null;
};

type CandidateVacancyApplication = {
  id: string;
  vacancy_id: string;
  status: string;
  vacancy_title: string;
  company_name: string;
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
};

type EmployerVacancyApplication = {
  id: string;
  vacancy_id: string;
  status: string;
  cover_letter: string | null;
  candidate: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string | null;
    telegram: string | null;
    city: string | null;
    specialization: string | null;
    verified_grade: string | null;
    skills: string[];
  };
};

type EmployerProfileData = {
  email: string;
  company_name: string;
  description: string | null;
  industry: string | null;
  website: string | null;
  contact_person: string;
  phone: string | null;
  city: string | null;
  onboarding_completed: boolean;
};

type CandidateProfileData = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  telegram: string | null;
  bio: string | null;
  city: string | null;
  specialization: string | null;
  programming_language: string | null;
  declared_grade: string | null;
  verified_grade: string | null;
  work_format: string | null;
  salary_expectation?: number | null;
  salary_tax_type?: "gross" | "net";
  skills?: string[];
  fsp_id: string | null;
  fsp_verified: boolean;
  agreed_152_fz: boolean;
  agreed_publication: boolean;
  visibility_public: boolean;
  mentor_available: boolean;
  agreed_osint: boolean;
};

type ParsedResume = {
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  telegram: string | null;
  city: string | null;
  specialization: string | null;
  suggested_grade: string | null;
  extracted_skills: string[];
  text_preview: string;
};

type InvitationChatMessage = {
  id: string;
  body: string;
  created_at: string;
  is_mine: boolean;
};

type InvitationUnreadCount = {
  unread_count: number;
  by_invitation: Record<string, number>;
};

type DialogueInvitation = {
  id: string;
  company_name: string;
  candidate_name: string;
  need_title: string | null;
  status: string;
  created_at: string;
};

type MentorProfile = {
  user_id: string;
  name: string;
  specialization: string | null;
  verified_grade: string | null;
  skills: string[];
  city: string | null;
};

type NetworkConversation = {
  id: string;
  other_user_id: string;
  other_name: string;
  skill_focus: string;
  status: "pending" | "accepted" | "rejected";
  can_accept: boolean;
  last_message: string;
  updated_at: string;
};

type NetworkMessage = {
  id: string;
  body: string;
  created_at: string;
  is_mine: boolean;
};

type ApplicationDialogue = {
  id: string;
  vacancy_id: string;
  vacancy_title: string;
  company_name: string;
  candidate_name: string;
  status: string;
  last_message: string;
};

type TestQuestionData = {
  id: string;
  topic: string;
  question_type: string;
  question_text: string;
  options: Array<{ id: string; text: string }>;
};

type TestStartData = {
  session_id: string;
  specialization: string;
  target_grade: string;
  questions: TestQuestionData[];
  total_questions: number;
  skill_code?: string | null;
  assessment_id?: string | null;
};

type GradeRoadmapData = {
  id: string;
  specialization: string;
  programming_language: string | null;
  target_grade: string;
  status: string;
  skills: Array<{ code: string; label: string; status: string; percentage: number | null; level_out_of_ten: number | null; session_id: string | null }>;
  percentage: number | null;
  passed: boolean | null;
  grade_confirmed: boolean;
  verified_grade: string | null;
  suggested_grade: string | null;
  expires_at: string | null;
  retake_used: boolean;
  retry_available_at: string | null;
  promotion_available_at: string | null;
};

type AdditionalSkillTestData = {
  code: string;
  label: string;
  target_grade: string;
  latest_percentage: number | null;
  level_out_of_ten: number | null;
  latest_session_id: string | null;
};

type TestResultData = {
  session_id: string;
  specialization: string;
  target_grade: string;
  score: number;
  max_score: number;
  percentage: number;
  correct_count?: number;
  total_questions?: number;
  required_correct?: number;
  passed: boolean | null;
  grade_confirmed?: boolean;
  skill_code?: string | null;
  assessment_id?: string | null;
  verified_grade: string | null;
  skill_breakdown: Array<{ topic: string; score: number; max_score: number; percentage: number; correct_count?: number; total_questions?: number }>;
  question_review?: Array<{
    code: string;
    topic: string;
    question_text: string;
    selected_answers: string[];
    correct_answers: string[];
    is_correct: boolean;
    explanation: string;
  }>;
  feedback: string;
  suggested_grade: string | null;
};

type TestHistoryData = {
  id: string;
  specialization: string;
  target_grade: string;
  percentage: number;
  passed: boolean | null;
  grade_confirmed?: boolean;
  status: string;
  created_at: string;
  completed_at: string | null;
  skill_code?: string | null;
  assessment_id?: string | null;
};

type RadarComparison = {
  labels: string[];
  before: number[];
  after: number[];
  hasPriorResults: boolean;
  hasUnevaluatedBefore: boolean;
};

function mapMatchToCandidate(item: MatchingCandidate, index: number, demoMode = false): Candidate {
  const demoRadar = demoMode
    ? candidates.find((candidate) => candidate.name === `${item.first_name} ${item.last_name}`)
    : undefined;
  return {
    id: index + 1,
    backendId: item.candidate_id,
    achievementsCount: item.achievements_count,
    fspVerified: item.fsp_verified,
    verifiedGrade: Boolean(item.verified_grade),
    availableFrom: item.available_from ?? null,
    trueScore: item.trust_score ?? null,
    trueScoreFlags: item.trust_flags,
    resumeVersions: item.resume_versions,
    matchedSkills: item.match_explanation.matched_skills,
    missingSkills: item.match_explanation.missing_skills,
    requestedSkillTests: item.requested_skill_tests ?? [],
    initials: `${item.first_name[0] ?? "?"}${item.last_name[0] ?? ""}`.toUpperCase(),
    name: `${item.first_name} ${item.last_name}`.trim(),
    role: item.specialization ?? "Специализация не указана",
    level: item.verified_grade ?? item.declared_grade ?? "Не указан",
    score: Math.round(item.match_score),
    salary: item.salary_expectation
      ? `${new Intl.NumberFormat("ru-RU").format(item.salary_expectation)} ₽ (${item.salary_tax_type === "net" ? "на руки" : "до вычета"})`
      : "Не указана",
    location: item.city ?? "Не указан",
    format: item.work_format === "remote" ? "Удалённо" : item.work_format === "hybrid" ? "Гибрид" : item.work_format === "office" ? "Офис" : "Не указан",
    experience: "Не указан",
    updated: "Не указано",
    trust: 0,
    skills: item.skills,
    radar: demoRadar?.radar ?? [],
    jobRadar: demoRadar?.jobRadar ?? [],
    achievements: [],
    summary: item.match_explanation.summary,
    gap: item.match_explanation.missing_skills.length
      ? item.match_explanation.missing_skills.join(", ")
      : "нет",
    about: "Полный профиль доступен после открытия кандидата.",
    email: "",
    telegram: "",
    education: "Не указано",
    experienceItems: [],
  };
}

function Icon({
  name,
  size = 18,
}: {
  name: string;
  size?: number;
}) {
  const paths: Record<string, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    users: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    briefcase: (
      <>
        <rect x="3" y="7" width="18" height="13" rx="2" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" />
      </>
    ),
    send: (
      <>
        <path d="m22 2-7 20-4-9-9-4Z" />
        <path d="M22 2 11 13" />
      </>
    ),
    chat: (
      <>
        <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z" />
      </>
    ),
    mail: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="m3 7 9 6 9-6" />
      </>
    ),
    chart: (
      <>
        <path d="M3 3v18h18" />
        <path d="m7 16 4-5 4 3 5-7" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.08A1.7 1.7 0 0 0 9 19.37a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.63 15 1.7 1.7 0 0 0 3.08 14H3v-4h.08A1.7 1.7 0 0 0 4.63 9a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.63 1.7 1.7 0 0 0 10 3.08V3h4v.08A1.7 1.7 0 0 0 15 4.63a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.37 9 1.7 1.7 0 0 0 20.92 10H21v4h-.08A1.7 1.7 0 0 0 19.4 15Z" />
      </>
    ),
    search: <circle cx="11" cy="11" r="7" />,
    filter: (
      <>
        <path d="M4 6h16M7 12h10M10 18h4" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    check: <path d="m5 12 4 4L19 6" />,
    close: <path d="M18 6 6 18M6 6l12 12" />,
    logout: (
      <>
        <path d="M10 17l5-5-5-5M15 12H3" />
        <path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" />
      </>
    ),
    building: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M9 21v-4h6v4M8 7h.01M12 7h.01M16 7h.01M8 11h.01M12 11h.01M16 11h.01" /></>,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01" /></>,
    target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    money: <><rect x="2" y="5" width="20" height="14" rx="2" /><circle cx="12" cy="12" r="3" /><path d="M6 9h.01M18 15h.01" /></>,
    medal: <><circle cx="12" cy="8" r="6" /><path d="m8.2 13-1.2 9 5-3 5 3-1.2-9" /></>,
    sparkle: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3ZM19 14l1 2.5 2.5 1-2.5 1L19 21l-1-2.5-2.5-1 2.5-1L19 14Z" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
    upload: <><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v4h16v-4" /></>,
    school: <><path d="m2 10 10-6 10 6-10 6-10-6Z" /><path d="M6 12v5c3.5 3 8.5 3 12 0v-5M22 10v6" /></>,
    arrowUpRight: <><path d="M7 17 17 7M7 7h10v10" /></>,
    compare: (
      <>
        <path d="M8 3v18M16 3v18M3 8h5M16 16h5" />
        <path d="m5 5 3 3-3 3M19 13l-3 3 3 3" />
      </>
    ),
    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </>
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" />
      </>
    ),
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />,
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
    refresh: <><path d="M20 7v5h-5" /><path d="M4 17v-5h5" /><path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2" /></>,
  };

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
      {name === "search" && <path d="m20 20-4-4" />}
    </svg>
  );
}

function ModalFrame({
  children,
  className,
  labelledBy,
  onClose,
}: {
  children: ReactNode;
  className: string;
  labelledBy: string;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useDialogA11y(dialogRef, onClose);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={className}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function useDialogA11y<T extends HTMLElement>(
  dialogRef: { current: T | null },
  onClose: () => void,
) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const dialog = dialogRef.current;
    const selector = 'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusable = dialog ? Array.from(dialog.querySelectorAll<HTMLElement>(selector))
      .filter((element) => element.getClientRects().length > 0) : [];
    (focusable[0] ?? dialog)?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const visible = Array.from(dialog.querySelectorAll<HTMLElement>(selector))
        .filter((element) => element.getClientRects().length > 0);
      if (!visible.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = visible[0];
      const last = visible[visible.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, []);
}

function DiscardConfirmation({
  title,
  message,
  onKeepEditing,
  onDiscard,
}: {
  title: string;
  message: string;
  onKeepEditing: () => void;
  onDiscard: () => void;
}) {
  return (
    <ModalFrame className="discard-dialog" labelledBy="discard-dialog-title" onClose={onKeepEditing}>
      <div className="discard-dialog__content">
        <span>НЕСОХРАНЁННЫЕ ИЗМЕНЕНИЯ</span>
        <strong id="discard-dialog-title">{title}</strong>
        <p>{message}</p>
        <div className="modal__actions">
          <Button variant="outline" onClick={onKeepEditing}>Вернуться к форме</Button>
          <Button variant="ghost" onClick={onDiscard}>Закрыть без сохранения</Button>
        </div>
      </div>
    </ModalFrame>
  );
}

function Button({
  children,
  variant = "primary",
  onClick,
  className = "",
  type = "button",
  disabled = false,
  ariaPressed,
}: {
  children: ReactNode;
  variant?: "primary" | "ghost" | "outline" | "danger";
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  ariaPressed?: boolean;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      aria-pressed={ariaPressed}
      className={`button button--${variant} ${className}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Radar({
  values,
  target,
  compact = false,
  axisLabels,
  showAxisLabels = true,
  description = "Сравнение компетенций кандидата и вакансии",
  className = "",
}: {
  values: Array<number | null>;
  target: number[];
  compact?: boolean;
  axisLabels?: string[];
  showAxisLabels?: boolean;
  description?: string;
  className?: string;
}) {
  const center = compact ? 110 : 160;
  const maxR = compact ? 72 : 92;
  const visibleLabels = axisLabels ?? labels;
  const targetValues = target.length === values.length ? target : values.map(() => 10);
  const polarPoint = (radius: number, angle: number) =>
    `${center + Math.cos(angle) * radius},${center + Math.sin(angle) * radius}`;
  const point = (value: number, i: number) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * i) / values.length;
    return polarPoint((value / 10) * maxR, angle);
  };
  const ring = (level: number) =>
    values.map((_, i) => point(level, i)).join(" ");
  const labelPoint = (i: number) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * i) / values.length;
    return {
      x: center + Math.cos(angle) * (maxR + 26),
      y: center + Math.sin(angle) * (maxR + 26),
    };
  };
  const missingIndex = values.findIndex((value) => value === null);
  const measuredRuns: number[][] = [];
  if (missingIndex >= 0) {
    let run: number[] = [];
    for (let step = 1; step <= values.length; step++) {
      const index = (missingIndex + step) % values.length;
      if (values[index] !== null) {
        run.push(index);
      } else if (run.length > 0) {
        measuredRuns.push(run);
        run = [];
      }
    }
  }
  const partialAreaPoints = (run: number[]) => {
    const measuredPoints = run.map((index) => point(values[index]!, index));
    if (run.length > 1) return `${center},${center} ${measuredPoints.join(" ")}`;
    const index = run[0];
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / values.length;
    const radius = (values[index]! / 10) * maxR * 0.65;
    const halfWidth = Math.PI / (values.length * 2);
    return `${center},${center} ${polarPoint(radius, angle - halfWidth)} ${measuredPoints[0]} ${polarPoint(radius, angle + halfWidth)}`;
  };

  return (
    <svg
      className={`radar ${compact ? "radar--compact" : ""} ${className}`}
      viewBox={compact ? "0 0 220 220" : "0 0 320 320"}
      role="img"
      aria-label={description}
    >
      {[2, 4, 6, 8, 10].map((level) => (
        <polygon key={level} points={ring(level)} className="radar__ring" />
      ))}
      {values.map((_, i) => (
        <line
          key={i}
          x1={center}
          y1={center}
          x2={point(10, i).split(",")[0]}
          y2={point(10, i).split(",")[1]}
          className="radar__axis"
        />
      ))}
      <polygon
        points={targetValues.map((v, i) => point(v, i)).join(" ")}
        className="radar__target"
      />
      {missingIndex < 0 ? <polygon
        points={values.map((value, i) => point(value!, i)).join(" ")}
        className="radar__value"
      /> : <>
        {measuredRuns.map((run) => <polygon
          key={run[0]}
          points={partialAreaPoints(run)}
          className="radar__value"
        />)}
        {values.map((value, i) => value === null ? null : <circle
          key={i}
          cx={point(value, i).split(",")[0]}
          cy={point(value, i).split(",")[1]}
          r={compact ? 3 : 4}
          className="radar__measured-point"
        />)}
      </>}
      {!compact && showAxisLabels &&
        visibleLabels.map((label, i) => {
          const pos = labelPoint(i);
          const lines = label.split(/\s+/).reduce<string[]>((result, word) => {
            const chunks = word.match(/.{1,12}/gu) ?? [word];
            chunks.forEach((chunk, index) => {
              const lastLine = result[result.length - 1];
              if (index === 0 && lastLine && `${lastLine} ${chunk}`.length <= 12) {
                result[result.length - 1] = `${lastLine} ${chunk}`;
              } else {
                result.push(chunk);
              }
            });
            return result;
          }, []);
          return (
            <text
              key={`${label}-${i}`}
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="radar__label"
            >
              <title>{label}</title>
              {lines.map((line, lineIndex) => (
                <tspan key={`${label}-${lineIndex}`} x={pos.x} dy={lineIndex === 0 ? `${(1 - lines.length) * 0.55}em` : "1.1em"}>{line}</tspan>
              ))}
            </text>
          );
        })}
    </svg>
  );
}

function SpecialtyRadarGallery({
  currentSpecialization,
  currentSkills,
}: {
  currentSpecialization?: string | null;
  currentSkills: GradeRoadmapData["skills"];
}) {
  const samples = [...SPECIALTY_RADAR_SAMPLES].sort((left, right) =>
    left.specialization.toLowerCase() === currentSpecialization?.trim().toLowerCase() ? -1 : right.specialization.toLowerCase() === currentSpecialization?.trim().toLowerCase() ? 1 : 0,
  );

  return (
    <section className="specialty-radar-gallery" aria-labelledby="specialty-radar-title">
      <div className="specialty-radar-gallery__head">
        <div><span>КАРТЫ КОМПЕТЕНЦИЙ</span><h2 id="specialty-radar-title">Радар по направлениям</h2></div>
        <p>Синяя заливка — уровень навыка, пунктир — максимум 10. Демо-карты — примеры, а не ваша оценка.</p>
      </div>
      <div className="specialty-radar-gallery__grid">
        {samples.map((sample) => {
          const isCurrent = sample.specialization.toLowerCase() === currentSpecialization?.trim().toLowerCase();
          const hasResults = isCurrent && currentSkills.some((skill) => skill.level_out_of_ten !== null);
          const values = isCurrent && currentSkills.length > 0
            ? currentSkills.map((skill) => skill.level_out_of_ten ?? 0)
            : sample.values;
          const axisLabels = isCurrent && currentSkills.length > 0
            ? currentSkills.map((skill) => skill.label)
            : sample.labels;
          return (
            <article className={`specialty-radar-card${hasResults ? " specialty-radar-card--current" : ""}`} key={sample.specialization}>
              <div className="specialty-radar-card__head">
                <strong>{sample.specialization}</strong>
                <span>{hasResults ? "ВАШИ РЕЗУЛЬТАТЫ" : isCurrent ? "ОЖИДАЮТ ТЕСТА" : "ДЕМО-ПРИМЕР"}</span>
              </div>
              <Radar values={values} target={values.map(() => 10)} axisLabels={axisLabels} description={`Радар компетенций: ${sample.specialization}`} />
              <ul>
                {axisLabels.map((label, index) => (
                  <li key={`${sample.specialization}-${label}`}><span>{label}</span><strong>{values[index].toFixed(1)}<small> / 10</small></strong></li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Logo() {
  return (
    <div className="logo" aria-label="ФСП Карьера">
      <div className="logo__mark">
        <span />
        <span />
        <span />
      </div>
      <div>
        <div className="logo__name">ФСП</div>
        <div className="logo__sub">КАРЬЕРА</div>
      </div>
    </div>
  );
}

const pageCopy: Record<string, { eyebrow: string; title: string }> = {
  Обзор: { eyebrow: "РАБОЧЕЕ ПРОСТРАНСТВО", title: "Обзор платформы" },
  Подборка: { eyebrow: "ПОДБОР КОМАНДЫ / BACKEND", title: "Подборка кандидатов" },
  "Банк кандидатов": { eyebrow: "ВЕРИФИЦИРОВАННАЯ БАЗА", title: "Банк кандидатов" },
  Потребности: { eyebrow: "МАТЧИНГ И КАТЕГОРИЗАЦИЯ", title: "Потребности команды" },
  Приглашения: { eyebrow: "REVERSE RECRUITING", title: "Приглашения" },
  Диалоги: { eyebrow: "СООБЩЕСТВО И НЕТВОРКИНГ", title: "Диалоги" },
  Аналитика: { eyebrow: "КАЧЕСТВО ПОДБОРА", title: "Аналитика" },
  Настройки: { eyebrow: "УПРАВЛЕНИЕ АККАУНТОМ", title: "Настройки" },
  Профиль: { eyebrow: "ЛИЧНЫЙ КАБИНЕТ", title: "Профиль и резюме" },
  Тестирование: { eyebrow: "ПРОВЕРКА НАВЫКОВ", title: "Тестирование" },
  "Мой грейд": { eyebrow: "ВАШ ПРОФЕССИОНАЛЬНЫЙ ПРОФИЛЬ", title: "Мой грейд" },
  Задания: { eyebrow: "АКТУАЛЬНОСТЬ ПРОФИЛЯ", title: "Регулярные задания" },
  Вакансии: { eyebrow: "ОТКРЫТЫЕ ПОЗИЦИИ", title: "Вакансии" },
  "Вакансии компании": { eyebrow: "ПУБЛИКАЦИЯ И ОТКЛИКИ", title: "Вакансии компании" },
};

function MetricCard({
  label,
  value,
  detail,
  accent,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: boolean;
  icon?: string;
}) {
  const resolvedIcon = icon ?? (label.includes("ПРИГЛАШ") ? "send"
    : label.includes("УРОВЕН") ? "compare"
      : label.includes("ФСП") ? "shield"
        : "sparkle");
  return (
    <div className={`metric-card ${accent ? "metric-card--accent" : ""}`}>
      <span className="metric-card__icon"><Icon name={resolvedIcon} size={17} /></span>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function Progress({ value }: { value: number }) {
  return (
    <div className="progress">
      <span style={{ width: `${value}%` }} />
    </div>
  );
}

const DEFAULT_SKILLS_BY_SPEC: Record<string, Array<{ name: string; weight: number }>> = {
  Backend: [
    { name: "Python", weight: 5 },
    { name: "FastAPI", weight: 4 },
    { name: "PostgreSQL", weight: 4 },
    { name: "Docker", weight: 3 },
    { name: "CI/CD", weight: 3 },
  ],
  Frontend: [
    { name: "React", weight: 5 },
    { name: "TypeScript", weight: 5 },
    { name: "Redux", weight: 3 },
    { name: "CSS/HTML", weight: 4 },
    { name: "Git", weight: 3 },
  ],
  Fullstack: [
    { name: "TypeScript", weight: 5 },
    { name: "React", weight: 4 },
    { name: "Node.js", weight: 4 },
    { name: "PostgreSQL", weight: 4 },
    { name: "Docker", weight: 3 },
  ],
  Mobile: [
    { name: "Kotlin", weight: 5 },
    { name: "Android SDK", weight: 5 },
    { name: "Swift", weight: 4 },
    { name: "REST API", weight: 4 },
    { name: "Git", weight: 3 },
  ],
  "DevOps / SRE": [
    { name: "Docker", weight: 5 },
    { name: "Kubernetes", weight: 5 },
    { name: "CI/CD", weight: 4 },
    { name: "Linux", weight: 4 },
    { name: "Terraform", weight: 3 },
  ],
  "Data Science / ML": [
    { name: "Python", weight: 5 },
    { name: "Machine Learning", weight: 5 },
    { name: "SQL", weight: 4 },
    { name: "Pandas", weight: 4 },
    { name: "Docker", weight: 3 },
  ],
  "QA / Testing": [
    { name: "Автотестирование", weight: 5 },
    { name: "Python", weight: 4 },
    { name: "Postman", weight: 4 },
    { name: "SQL", weight: 3 },
    { name: "CI/CD", weight: 3 },
  ],
  "System Programming / C++": [
    { name: "C++", weight: 5 },
    { name: "Linux", weight: 4 },
    { name: "Multithreading", weight: 4 },
    { name: "Алгоритмы", weight: 4 },
    { name: "Git", weight: 3 },
  ],
  GameDev: [
    { name: "C++", weight: 5 },
    { name: "Unreal Engine", weight: 5 },
    { name: "C#", weight: 4 },
    { name: "Unity", weight: 4 },
    { name: "3D Математика", weight: 3 },
  ],
};

const SKILL_SUGGESTIONS = [
  "Python", "SQL", "HTTP API", "Надёжность сервиса", "Git", "Docker",
  "FastAPI", "PostgreSQL", "Redis", "React", "TypeScript", "JavaScript",
  "Node.js", "Java", "Spring", "Kubernetes", "Linux", "Pandas",
  "Machine Learning", "CI/CD", "Terraform", "Postman", "C++", "C#",
];

function EmployerScreen({
  active,
  onOpenCandidates,
  onOpenResume,
  onNeedCreated,
  onNotify,
  onNavigate,
  demoMode,
}: {
  active: string;
  onOpenCandidates: () => void;
  onOpenResume: (candidate: Candidate) => void;
  onNeedCreated: (need: EmployerNeedRecord) => void;
  onNotify: (message: string, type?: "success" | "error") => void;
  onNavigate: (screen: string, target?: string) => void;
  demoMode: boolean;
}) {
  const [saved, setSaved] = useState(false);
  const [vacancyEditor, setVacancyEditor] = useState(false);
  const [vacancyEditingId, setVacancyEditingId] = useState<string | null>(null);
  const [vacancies, setVacancies] = useState<VacancyRecord[]>([]);
  const [vacanciesLoading, setVacanciesLoading] = useState(false);
  const [vacancySaving, setVacancySaving] = useState(false);
  const [vacancyForm, setVacancyForm] = useState({
    title: "",
    specialization: "Backend",
    required_grade: "middle",
    required_skills: "",
    salary_min: "220000",
    salary_max: "280000",
    salary_tax_type: "gross" as "gross" | "net",
    work_format: "remote",
    city: "",
    description: "",
  });
  const [vacancyApplications, setVacancyApplications] = useState<EmployerVacancyApplication[]>([]);
  const [applicationsVacancy, setApplicationsVacancy] = useState<string | null>(null);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [vacancyListFilter, setVacancyListFilter] = useState<"published" | "drafts" | "all">("published");
  const [needs, setNeeds] = useState<EmployerNeedRecord[]>([]);
  const [needTitle, setNeedTitle] = useState("Backend-разработчик");
  const [needSpecialization, setNeedSpecialization] = useState("Backend");
  const [needGrade, setNeedGrade] = useState("middle");
  const [needDescription, setNeedDescription] = useState("");
  const [needSalaryMin, setNeedSalaryMin] = useState("220000");
  const [needSalaryMax, setNeedSalaryMax] = useState("280000");
  const [needSalaryTaxType, setNeedSalaryTaxType] = useState<"gross" | "net" | "">("gross");
  const [needCity, setNeedCity] = useState("");
  const [needWorkFormat, setNeedWorkFormat] = useState("remote");
  const [skillItems, setSkillItems] = useState<Array<{ name: string; weight: number }>>([
    { name: "Python", weight: 5 },
    { name: "FastAPI", weight: 4 },
    { name: "PostgreSQL", weight: 4 },
    { name: "Docker", weight: 3 },
    { name: "CI/CD", weight: 3 },
  ]);
  const [newSkillName, setNewSkillName] = useState("");
  const [skillSuggestionsOpen, setSkillSuggestionsOpen] = useState(false);
  const skillSuggestions = SKILL_SUGGESTIONS.filter((name) =>
    name.toLocaleLowerCase().startsWith(newSkillName.trim().toLocaleLowerCase())
    && !skillItems.some((item) => item.name.toLocaleLowerCase() === name.toLocaleLowerCase()),
  );
  const [needEntryMode, setNeedEntryMode] = useState<"manual" | "llm">("manual");
  const [needDraft, setNeedDraft] = useState<NeedDraft | null>(null);
  const [needParsing, setNeedParsing] = useState(false);

  const handleAddSkill = (name = newSkillName) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    if (trimmed.length > 100) {
      onNotify("Название навыка не должно превышать 100 символов", "error");
      return;
    }
    if (skillItems.some((s) => s.name.toLowerCase() === trimmed.toLowerCase())) {
      onNotify("Этот навык уже добавлен", "error");
      return;
    }
    setSkillItems((current) => [...current, { name: trimmed, weight: 3 }]);
    setNewSkillName("");
    setSkillSuggestionsOpen(false);
  };

  const handleRemoveSkill = (indexToRemove: number) => {
    setSkillItems((current) => current.filter((_, idx) => idx !== indexToRemove));
  };

  const handleUpdateSkillWeight = (indexToUpdate: number, weight: number) => {
    setSkillItems((current) =>
      current.map((item, idx) => (idx === indexToUpdate ? { ...item, weight } : item)),
    );
  };

  const handleSpecializationChange = (newSpec: string) => {
    setNeedSpecialization(newSpec);
    if (DEFAULT_SKILLS_BY_SPEC[newSpec]) {
      setSkillItems(DEFAULT_SKILLS_BY_SPEC[newSpec]);
    }
  };
  const [needSaving, setNeedSaving] = useState(false);
  const [companyProfile, setCompanyProfile] = useState<EmployerProfileData | null>(null);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [bankItems, setBankItems] = useState<Candidate[]>([]);
  const [bankFilters, setBankFilters] = useState<BankFilters>(() => {
    const defaults = { query: "", skill: "", specialization: "", grade: "", format: "", city: "", fspOnly: false };
    const savedFilters = window.localStorage.getItem("fsp-bank-filters");
    if (!savedFilters) return defaults;
    let parsed: unknown;
    try {
      parsed = JSON.parse(savedFilters);
    } catch {
      return defaults;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return defaults;
    const saved = parsed as Partial<BankFilters>;
    return {
      query: typeof saved.query === "string" ? saved.query : defaults.query,
      skill: typeof saved.skill === "string" ? saved.skill : defaults.skill,
      specialization: typeof saved.specialization === "string" ? saved.specialization : defaults.specialization,
      grade: typeof saved.grade === "string" ? saved.grade : defaults.grade,
      format: typeof saved.format === "string" ? saved.format : defaults.format,
      city: typeof saved.city === "string" ? saved.city : defaults.city,
      fspOnly: typeof saved.fspOnly === "boolean" ? saved.fspOnly : defaults.fspOnly,
    };
  });
  const [bankLoading, setBankLoading] = useState(false);
  const [bankCompare, setBankCompare] = useState<Candidate[]>([]);
  const [bankCompareOpen, setBankCompareOpen] = useState(false);
  const [sentInvitations, setSentInvitations] = useState<Array<{ status: string }>>([]);
  const { query: bankQuery, skill: bankSkill, specialization: bankSpecialization, grade: bankGrade, format: bankFormat, city: bankCity, fspOnly: bankFspOnly } = bankFilters;

  useEffect(() => {
    window.localStorage.setItem("fsp-bank-filters", JSON.stringify(bankFilters));
  }, [bankFilters]);

  useEffect(() => {
    if (active === "Потребности" || active === "Обзор") {
      apiGet<EmployerNeedRecord[]>("/needs").then(setNeeds).catch(() => setNeeds([]));
    }
    if (active === "Настройки") {
      setCompanyLoading(true);
      apiGet<EmployerProfileData>("/employer/profile")
        .then(setCompanyProfile)
        .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить компанию", "error"))
        .finally(() => setCompanyLoading(false));
    }
  }, [active]);

  useEffect(() => {
    if (active !== "Вакансии компании") return;
    setVacanciesLoading(true);
    apiGet<VacancyRecord[]>("/vacancies/my")
      .then(setVacancies)
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить вакансии", "error"))
      .finally(() => setVacanciesLoading(false));
  }, [active]);

  useEffect(() => {
    if (active !== "Обзор") return;
    apiGet<Array<{ status: string }>>("/invitations/sent")
      .then(setSentInvitations)
      .catch(() => setSentInvitations([]));
  }, [active]);

  useEffect(() => {
    if (active !== "Банк кандидатов" && active !== "Аналитика") return;
    const params = new URLSearchParams({ fsp_only: String(bankFspOnly) });
    if (bankSpecialization) params.set("specialization", bankSpecialization);
    if (bankGrade) params.set("grade", bankGrade);
    if (bankSkill.trim()) params.set("skill", bankSkill.trim());
    if (bankFormat) params.set("work_format", bankFormat);
    if (bankCity.trim()) params.set("city", bankCity.trim());
    setBankLoading(true);
    apiGet<MatchingCandidate[]>(`/matching/search?${params}`)
      .then((items) => setBankItems(items.map((item, index) => mapMatchToCandidate(item, index, demoMode))))
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось выполнить поиск", "error"))
      .finally(() => setBankLoading(false));
  }, [active, bankSpecialization, bankGrade, bankSkill, bankFormat, bankCity, bankFspOnly, demoMode]);

  const visibleBankItems = bankItems.filter((candidate) =>
    !bankQuery || candidate.name.toLowerCase().includes(bankQuery.trim().toLowerCase()),
  );

  const resetVacancyForm = () => {
    setVacancyEditingId(null);
    setVacancyForm({
      title: "",
      specialization: "Backend",
      required_grade: "middle",
      required_skills: "",
      salary_min: "220000",
      salary_max: "280000",
      salary_tax_type: "gross",
      work_format: "remote",
      city: "",
      description: "",
    });
  };

  const editVacancy = (vacancy: VacancyRecord) => {
    setVacancyEditingId(vacancy.id);
    setVacancyForm({
      title: vacancy.title,
      specialization: vacancy.specialization,
      required_grade: vacancy.required_grade,
      required_skills: vacancy.required_skills.join(", "),
      salary_min: String(vacancy.salary_min),
      salary_max: String(vacancy.salary_max),
      salary_tax_type: vacancy.salary_tax_type,
      work_format: vacancy.work_format,
      city: vacancy.city ?? "",
      description: vacancy.description,
    });
    setVacancyEditor(true);
    setApplicationsVacancy(null);
  };

  const saveVacancy = async () => {
    const salaryMin = Number(vacancyForm.salary_min.replace(/\D/g, ""));
    const salaryMax = Number(vacancyForm.salary_max.replace(/\D/g, ""));
    if (vacancyForm.title.trim().length < 2 || salaryMin <= 0 || salaryMax < salaryMin) {
      onNotify("Укажите название и корректный диапазон зарплаты", "error");
      return;
    }
    setVacancySaving(true);
    try {
      const payload = {
        ...vacancyForm,
        title: vacancyForm.title.trim(),
        salary_min: salaryMin,
        salary_max: salaryMax,
        required_skills: vacancyForm.required_skills.split(",").map((skill) => skill.trim()).filter(Boolean),
        city: vacancyForm.city.trim() || null,
        description: vacancyForm.description.trim(),
        ...(!vacancyEditingId ? { is_published: false } : {}),
      };
      const updated = vacancyEditingId
        ? await apiRequest<VacancyRecord>(`/vacancies/${vacancyEditingId}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await apiPost<VacancyRecord>("/vacancies", payload);
      setVacancies((current) => vacancyEditingId
        ? current.map((item) => item.id === updated.id ? updated : item)
        : [updated, ...current]);
      setVacancyListFilter(updated.is_published ? "published" : "drafts");
      setVacancyEditor(false);
      resetVacancyForm();
      onNotify(vacancyEditingId ? "Вакансия обновлена" : "Вакансия создана");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось сохранить вакансию", "error");
    } finally {
      setVacancySaving(false);
    }
  };

  const toggleVacancyPublication = async (vacancy: VacancyRecord) => {
    try {
      const updated = await apiRequest<VacancyRecord>(`/vacancies/${vacancy.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_published: !vacancy.is_published }),
      });
      setVacancies((current) => current.map((item) => item.id === updated.id ? updated : item));
      setVacancyListFilter(updated.is_published ? "published" : "drafts");
      onNotify(updated.is_published ? "Вакансия опубликована" : "Вакансия снята с публикации");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось изменить публикацию", "error");
    }
  };

  const loadVacancyApplications = async (vacancy: VacancyRecord) => {
    setApplicationsLoading(true);
    setApplicationsVacancy(vacancy.id);
    try {
      setVacancyApplications(await apiGet<EmployerVacancyApplication[]>(`/vacancies/${vacancy.id}/applications`));
    } catch (error) {
      setApplicationsVacancy(null);
      onNotify(error instanceof Error ? error.message : "Не удалось загрузить отклики", "error");
    } finally {
      setApplicationsLoading(false);
    }
  };

  const updateVacancyApplication = async (applicationId: string, status: "reviewed" | "accepted" | "rejected") => {
    try {
      await apiRequest(`/vacancies/applications/${applicationId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setVacancyApplications((current) => current.map((item) => item.id === applicationId ? { ...item, status } : item));
      onNotify("Статус отклика обновлён");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось обновить отклик", "error");
    }
  };

  const createNeed = async () => {
    if (needTitle.trim().length < 2 || !needSpecialization || !needGrade || !needSalaryTaxType || !needWorkFormat) {
      onNotify("Заполните название, специализацию, грейд, тип зарплаты и формат работы", "error");
      return;
    }
    const salaryMin = Number(needSalaryMin.replace(/\D/g, ""));
    const salaryMax = Number(needSalaryMax.replace(/\D/g, ""));
    if (salaryMin <= 0 || salaryMax < salaryMin) {
      onNotify("Проверьте зарплатный диапазон", "error");
      return;
    }
    if (skillItems.length === 0) {
      onNotify("Укажите хотя бы один навык для подбора", "error");
      return;
    }
    setNeedSaving(true);
    try {
      const created = await apiPost<EmployerNeedRecord>("/needs", {
        title: needTitle,
        specialization: needSpecialization,
        required_grade: needGrade,
        required_skills: skillItems.map((item) => ({
          name: item.name,
          weight: item.weight,
          required: true,
        })),
        salary_min: salaryMin,
        salary_max: salaryMax,
        salary_tax_type: needSalaryTaxType,
        currency: "RUB",
        work_format: needWorkFormat,
        city: needCity.trim() || null,
        description: needDescription,
      });
      setNeeds((current) => [created, ...current]);
      onNeedCreated(created);
      onNotify("Потребность сохранена. Подборка обновлена.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось сохранить потребность", "error");
    } finally {
      setNeedSaving(false);
    }
  };

  const parseNeedDescription = async () => {
    if (needDescription.trim().length < 20) {
      onNotify("Для разбора нужно описание хотя бы из 20 символов", "error");
      return;
    }
    setNeedParsing(true);
    setNeedDraft(null);
    try {
      const draft = await apiPost<NeedDraft>("/needs/parse", { text: needDescription.trim() });
      setNeedDraft(draft);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось разобрать описание", "error");
    } finally {
      setNeedParsing(false);
    }
  };

  const applyNeedDraft = () => {
    if (!needDraft) return;
    if (needDraft.specialization) setNeedSpecialization(needDraft.specialization);
    if (needDraft.required_grade) setNeedGrade(needDraft.required_grade);
    if (needDraft.required_skills.length > 0) setSkillItems(needDraft.required_skills);
    if (needDraft.salary_min !== null) setNeedSalaryMin(needDraft.salary_min.toString());
    if (needDraft.salary_max !== null) setNeedSalaryMax(needDraft.salary_max.toString());
    if (needDraft.salary_tax_type) setNeedSalaryTaxType(needDraft.salary_tax_type);
    if (needDraft.work_format) setNeedWorkFormat(needDraft.work_format);
    setNeedDraft(null);
    setNeedEntryMode("manual");
    onNotify("Найденные поля перенесены в форму. Проверьте их и заполните остальные.");
  };

  const needDraftSummary = needDraft ? [
    needDraft.specialization && `Специализация: ${needDraft.specialization}`,
    needDraft.required_grade && `Грейд: ${needDraft.required_grade}`,
    needDraft.required_skills.length > 0 && `Навыки: ${needDraft.required_skills.map((skill) => `${skill.name} ${skill.weight}/5`).join(", ")}`,
    needDraft.salary_min !== null && needDraft.salary_max !== null && `Зарплата: ${needDraft.salary_min}–${needDraft.salary_max} ₽`,
    needDraft.salary_tax_type && `Зарплата: ${needDraft.salary_tax_type === "net" ? "на руки" : "до вычета"}`,
    needDraft.work_format && `Формат: ${needDraft.work_format}`,
  ].filter(Boolean) : [];

  const saveCompanyProfile = async () => {
    if (!companyProfile) return;
    const payload = {
      company_name: companyProfile.company_name,
      description: companyProfile.description,
      industry: companyProfile.industry,
      website: companyProfile.website,
      contact_person: companyProfile.contact_person,
      phone: companyProfile.phone,
      city: companyProfile.city,
    };
    try {
      const savedProfile = companyProfile.onboarding_completed
        ? await apiPut<EmployerProfileData>("/employer/profile", payload)
        : await apiPost<EmployerProfileData>("/employers/onboarding", payload);
      setCompanyProfile(savedProfile);
      setSaved(true);
      onNotify("Профиль компании сохранён");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось сохранить компанию", "error");
    }
  };

  if (active === "Обзор") {
    const waitingInvitations = sentInvitations.filter((item) => item.status === "sent" || item.status === "viewed").length;
    const acceptedInvitations = sentInvitations.filter((item) => item.status === "accepted").length;
    return (
      <div className="page-content page-content--overview">
        <div className="metrics-grid">
          <MetricCard label="АКТИВНЫЕ ПОТРЕБНОСТИ" value={String(needs.filter((need) => need.is_active).length)} detail="По данным компании" accent icon="briefcase" />
          <MetricCard label="ОТПРАВЛЕНО ПРИГЛАШЕНИЙ" value={String(sentInvitations.length)} detail="По данным API" icon="mail" />
          <MetricCard label="ОЖИДАЮТ ОТВЕТА" value={String(waitingInvitations)} detail={`${acceptedInvitations} принято`} icon="clock" />
        </div>
        <div className="dashboard-grid">
          <section className="feature-card feature-card--wide">
            <div className="feature-head">
              <div><span>АКТИВНЫЙ ПОДБОР</span><strong>Текущие потребности</strong></div>
              <Button variant="ghost" onClick={() => onNavigate("Потребности")}>Все потребности</Button>
            </div>
            {needs.filter((need) => need.is_active).map((need) => (
              <button type="button" className="need-row" key={need.id} onClick={() => onNeedCreated(need)}>
                <div className="need-row__icon"><Icon name="briefcase" /></div>
                <div><strong>{need.title}</strong><span>{need.specialization} · {need.required_grade} · {need.work_format === "remote" ? "Удалённо" : need.work_format === "hybrid" ? "Гибрид" : "Офис"}</span></div>
                <div className="need-row__salary"><span>Зарплата</span><strong>{formatSalaryRange(need.salary_min, need.salary_max)}</strong><small>{need.salary_tax_type === "net" ? "на руки" : "до вычета НДФЛ"}</small></div>
                <Icon name="chevron" />
              </button>
            ))}
            {needs.filter((need) => need.is_active).length === 0 && <div className="empty-state">Активных потребностей нет. <Button variant="outline" onClick={() => onNavigate("Потребности")}>Создать потребность</Button></div>}
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>СТАТУСЫ</span><strong>Приглашения</strong></div><Button variant="ghost" onClick={() => onNavigate("Приглашения")}>Открыть</Button></div>
            <div className="funnel"><div><span>Отправлено</span><strong>{sentInvitations.length}</strong></div><div><span>Ожидают</span><strong>{waitingInvitations}</strong></div><div><span>Принято</span><strong>{acceptedInvitations}</strong></div></div>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Банк кандидатов") {
    return (
      <div className="page-content">
        <div className="bank-toolbar">
          <div className="search-field search-field--wide"><Icon name="search" /><input value={bankQuery} onChange={(event) => setBankFilters((current) => ({ ...current, query: event.target.value }))} placeholder="Имя кандидата" aria-label="Поиск по имени кандидата" /></div>
          <div className="search-field"><Icon name="search" /><input maxLength={100} value={bankSkill} onChange={(event) => setBankFilters((current) => ({ ...current, skill: event.target.value }))} placeholder="Навык или стек" aria-label="Фильтр по навыку или стеку" /></div>
          <select className="bank-select" aria-label="Фильтр специализации" value={bankSpecialization} onChange={(event) => setBankFilters((current) => ({ ...current, specialization: event.target.value }))}><option value="">Все специализации</option>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select>
          <select className="bank-select" aria-label="Фильтр грейда" value={bankGrade} onChange={(event) => setBankFilters((current) => ({ ...current, grade: event.target.value }))}><option value="">Любой грейд</option>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
          <select className="bank-select" aria-label="Фильтр формата работы" value={bankFormat} onChange={(event) => setBankFilters((current) => ({ ...current, format: event.target.value }))}><option value="">Любой формат</option><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select>
          <input className="bank-select" aria-label="Фильтр города" value={bankCity} onChange={(event) => setBankFilters((current) => ({ ...current, city: event.target.value }))} placeholder="Город" />
          <Button variant={bankFspOnly ? "primary" : "outline"} onClick={() => setBankFilters((current) => ({ ...current, fspOnly: !current.fspOnly }))}><Icon name="filter" /> Достижения ФСП</Button>
        </div>
        <div className="bank-results-heading">
          <div><strong>{bankLoading ? "Загрузка кандидатов…" : `${visibleBankItems.length} профилей`}</strong><span>Резюме и сравнение доступны в каждой карточке — не нужно искать кнопки в конце строки.</span></div>
          <span>Контакты открываются после принятия приглашения</span>
        </div>
        <div className="candidate-directory-grid">
          {visibleBankItems.map((candidate) => {
            const selectedForCompare = bankCompare.some((item) => item.id === candidate.id);
            return (
              <article className="candidate-directory-card" key={candidate.id}>
                <div className="candidate-directory-card__header">
                  <div className="avatar">{candidate.initials}</div>
                  <div><strong>{candidate.name}</strong><span>{candidate.location} · {candidate.format}</span></div>
                  {candidate.fspVerified && <span className="candidate-directory-card__badge"><Icon name="check" size={13} /> ФСП</span>}
                </div>
                <div className="candidate-directory-card__grade"><strong>{candidate.role}</strong><span>{candidate.level} · {candidate.verifiedGrade ? "подтверждён" : "заявлен"}</span></div>
                {demoMode && candidate.radar.length > 0 && <div className="candidate-directory-card__radar"><Radar values={candidate.radar} target={candidate.jobRadar} compact description={`Демонстрационное сравнение карты навыков ${candidate.name}`} /><span>ДЕМО · ПРОФИЛЬ / ВАКАНСИЯ</span></div>}
                <div className="mini-tags">{candidate.skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}{candidate.skills.length > 4 && <span>+{candidate.skills.length - 4}</span>}</div>
                <div className="candidate-directory-card__footer">
                  <Button variant="outline" onClick={() => onOpenResume(candidate)}><Icon name="users" size={15} /> Резюме</Button>
                  <Button
                    variant={selectedForCompare ? "primary" : "ghost"}
                    disabled={!selectedForCompare && bankCompare.length >= 3}
                    onClick={() => setBankCompare((current) => selectedForCompare
                      ? current.filter((item) => item.id !== candidate.id)
                      : [...current, candidate])}
                  ><Icon name="compare" size={15} />{selectedForCompare ? "Убрать" : "Сравнить"}</Button>
                </div>
              </article>
            );
          })}
          {!bankLoading && visibleBankItems.length === 0 && <div className="empty-state">По выбранным параметрам кандидаты не найдены</div>}
        </div>
        {bankCompare.length > 0 && <div className="bank-compare-bar"><span>Выбрано для сравнения: <strong>{bankCompare.length} / 3</strong></span><div>{bankCompare.map((candidate) => <span key={candidate.id}>{candidate.name}</span>)}</div><Button disabled={bankCompare.length < 2} onClick={() => setBankCompareOpen(true)}><Icon name="compare" /> Сравнить рядом</Button></div>}
        {bankCompareOpen && <CompareModal items={bankCompare} onClose={() => setBankCompareOpen(false)} onOpen={(candidate) => { setBankCompareOpen(false); onOpenResume(candidate); }} />}
      </div>
    );
  }

  if (active === "Потребности") {
    return (
      <div className="page-content">
        <section className="existing-needs" aria-label="Сохранённые потребности">
          {needs.map((need) => (
            <article key={need.id}>
              <div>
                <strong>{need.title}</strong>
                <span>
                  {need.specialization} · {need.required_grade} · {new Intl.NumberFormat("ru-RU").format(need.salary_min)}–{new Intl.NumberFormat("ru-RU").format(need.salary_max)} ₽ ({need.salary_tax_type === "net" ? "на руки" : "до вычета"})
                </span>
              </div>
              <Button variant="outline" onClick={() => onNeedCreated(need)}>
                Открыть подбор
              </Button>
            </article>
          ))}
          {needs.length === 0 && <span>Пока нет сохранённых потребностей. Создайте первую, чтобы запустить подбор.</span>}
        </section>
        <div className="steps">
          <div className="active"><b>1</b><span>Описание</span></div>
          <div><b>2</b><span>Оценка важности</span></div>
          <div><b>3</b><span>Публикация</span></div>
        </div>
        <div className="split-layout">
          <section className="feature-card">
            <div className="feature-head"><div><span>ПАРАМЕТРЫ ПОТРЕБНОСТИ</span><strong>Опишите специалиста</strong></div></div>
            <div className="field-row field-row--flush">
              <label className="field"><span>НАЗВАНИЕ РОЛИ</span><input value={needTitle} onChange={(event) => setNeedTitle(event.target.value)} /></label>
              <label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={needSpecialization} onChange={(event) => handleSpecializationChange(event.target.value)}><option value="">Выберите специализацию</option>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            </div>
            <label className="field field--flush"><span>ТРЕБУЕМЫЙ УРОВЕНЬ</span><select value={needGrade} onChange={(event) => setNeedGrade(event.target.value)}><option value="">Выберите грейд</option>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <div className="field-row field-row--flush">
              <label className="field"><span>ЗАРПЛАТА ОТ, ₽</span><input inputMode="numeric" value={needSalaryMin} onChange={(event) => setNeedSalaryMin(event.target.value)} /></label>
              <label className="field"><span>ЗАРПЛАТА ДО, ₽</span><input inputMode="numeric" value={needSalaryMax} onChange={(event) => setNeedSalaryMax(event.target.value)} /></label>
            </div>
            <label className="field field--flush">
              <span>ТИП ЗАРПЛАТЫ</span>
              <select
                aria-label="Тип зарплаты"
                value={needSalaryTaxType}
                onChange={(event) => setNeedSalaryTaxType(event.target.value as "gross" | "net" | "")}
              >
                <option value="">Укажите тип зарплаты</option>
                <option value="gross">До вычета НДФЛ (gross)</option>
                <option value="net">На руки (net)</option>
              </select>
            </label>
            <div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={needCity} onChange={(event) => setNeedCity(event.target.value)} placeholder="Любой город" /></label><label className="field"><span>ФОРМАТ</span><select value={needWorkFormat} onChange={(event) => setNeedWorkFormat(event.target.value)}><option value="">Выберите формат</option><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select></label></div>
            <label className="field field--flush need-description-field">
              <span>{needEntryMode === "llm" ? "ОПИШИТЕ ПОТРЕБНОСТЬ ПРОМТОМ" : "ОПИСАНИЕ ПОТРЕБНОСТИ (НЕОБЯЗАТЕЛЬНО)"}</span>
              <textarea value={needDescription} onChange={(event) => { setNeedDescription(event.target.value); setNeedDraft(null); }} placeholder="Опишите задачи команды, стек и приоритеты роли." />
            </label>
          </section>
          <section className="feature-card skill-entry-card">
            <div className="skill-entry-head">
              <div className="feature-head"><div><span>ТРЕБОВАНИЯ ДЛЯ ПОДБОРА</span><strong>Как задать навыки?</strong></div></div>
              <div className="skill-entry-switch" role="group" aria-label="Способ заполнения шкалы навыков">
                <Button type="button" variant={needEntryMode === "manual" ? "primary" : "outline"} ariaPressed={needEntryMode === "manual"} onClick={() => setNeedEntryMode("manual")}>Расставить веса</Button>
                <Button type="button" variant={needEntryMode === "llm" ? "primary" : "outline"} ariaPressed={needEntryMode === "llm"} onClick={() => setNeedEntryMode("llm")}>Описать промтом</Button>
              </div>
            </div>
            {needEntryMode === "manual" ? <>
              <p className="feature-description feature-description--left">Укажите навыки и их важность для подбора: от 1 — базовый приоритет до 5 — критически важный.</p>
              <div className="skill-weights">
                {skillItems.map((item, index) => (
                  <div key={`${item.name}-${index}`}>
                    <span>{item.name}</span>
                    <input
                      aria-label={`Вес ${item.name}`}
                      type="range"
                      min="1"
                      max="5"
                      step="1"
                      value={item.weight}
                      onChange={(event) => handleUpdateSkillWeight(index, Number(event.target.value))}
                    />
                    <strong>{item.weight}/5</strong>
                    <button
                      type="button"
                      className="skill-weight-del"
                      title={`Удалить ${item.name}`}
                      aria-label={`Удалить ${item.name}`}
                      onClick={() => handleRemoveSkill(index)}
                    >
                      <Icon name="close" size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <div className="skill-add-row">
                <div className="skill-add-autocomplete" onBlur={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) setSkillSuggestionsOpen(false);
                }}>
                  <input
                    type="text"
                    placeholder="Добавить навык (например, Redis)..."
                    aria-label="Новый навык"
                    role="combobox"
                    aria-expanded={skillSuggestionsOpen && skillSuggestions.length > 0}
                    aria-controls="skill-suggestions"
                    aria-autocomplete="list"
                    value={newSkillName}
                    onFocus={() => setSkillSuggestionsOpen(true)}
                    onChange={(e) => { setNewSkillName(e.target.value); setSkillSuggestionsOpen(true); }}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") setSkillSuggestionsOpen(false);
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddSkill();
                      }
                    }}
                  />
                  {skillSuggestionsOpen && skillSuggestions.length > 0 && <div className="skill-suggestions" id="skill-suggestions" role="listbox" aria-label="Подходящие навыки">
                    {skillSuggestions.map((name) => <button key={name} type="button" role="option" aria-selected={false} onClick={() => handleAddSkill(name)}>{name}</button>)}
                  </div>}
                </div>
                <Button variant="outline" onClick={() => handleAddSkill()}>+ Добавить</Button>
              </div>
            </> : <>
              <p className="feature-description feature-description--left">Опишите задачи и стек в поле слева — мы предложим навыки и веса. Результат можно проверить и отредактировать перед сохранением.</p>
              <Button variant="outline" disabled={needParsing} onClick={() => void parseNeedDescription()}>{needParsing ? "Подбираем навыки…" : "Предложить навыки по описанию"}</Button>
              {needDraft && <div className="need-draft" aria-label="Предложенные поля">
                <p className="feature-description feature-description--left">{needDraftSummary.join(" · ")}</p>
                <p className="feature-description feature-description--left">Проверьте предложенные навыки и значения весов перед переносом в форму.</p>
                <Button variant="outline" onClick={applyNeedDraft}>Подставить навыки и поля</Button>
              </div>}
            </>}
            <p className="feature-description feature-description--left">Требования и веса будут сохранены в потребности; подбор покажет кандидатов с объяснением совпадений.</p>
            <Button disabled={needSaving} className={needSaving ? "button--disabled" : ""} onClick={() => void createNeed()}>{needSaving ? "Сохраняем…" : "Сохранить и запустить подбор"} <Icon name="chevron" /></Button>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Приглашения") {
    return <Invitations employer onNotify={onNotify} onNavigate={onNavigate} />;
  }

  if (!demoMode && active === "Аналитика") {
    return <div className="page-content"><section className="feature-card"><div className="feature-head"><div><span>АНАЛИТИКА</span><strong>Метрики ещё не подключены</strong></div></div><p className="feature-description feature-description--left">Backend не предоставляет endpoint аналитики. Числа по конверсии, качеству Top-3 и динамике приглашений пока не рассчитываются.</p></section></div>;
  }

  if (active === "Аналитика" && demoMode) {
    const scheduled = bankItems.filter((candidate) => candidate.availableFrom).sort((left, right) => (left.availableFrom ?? "").localeCompare(right.availableFrom ?? ""));
    const averageScore = bankItems.length && bankItems.some((candidate) => candidate.score > 0)
      ? String(Math.round(bankItems.reduce((total, candidate) => total + candidate.score, 0) / bankItems.length))
      : "—";
    const confirmedDates = scheduled.length;
    return (
      <div className="page-content">
        <div className="demo-banner">Сроки выхода и совпадения рассчитаны на локальных demo-профилях. У production API нет поля available_from.</div>
        <div className="metrics-grid">        <MetricCard label="КАНДИДАТОВ В БАНКЕ" value={String(bankItems.length)} detail="По текущим фильтрам" accent icon="users" /><MetricCard label="СРЕДНИЙ БАЛЛ ПОДБОРА" value={averageScore} detail="Считается для конкретной потребности" icon="target" /><MetricCard label="ДАТА ВЫХОДА УКАЗАНА" value={`${confirmedDates} / ${bankItems.length}`} detail="Если кандидат указал дату" icon="calendar" /></div>
        <section className="feature-card feature-card--wide">
          <div className="feature-head"><div><span>ДОСТУПНОСТЬ КАНДИДАТОВ</span><strong>Планируемые даты выхода</strong></div><Button variant="outline" onClick={() => onNavigate("Подборка")}>Открыть подборку</Button></div>
          <div className="start-dates">{scheduled.map((candidate, index) => <div key={candidate.backendId}><b>{new Date(`${candidate.availableFrom}T00:00:00`).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}</b><i className={index === 0 ? "active" : ""} /><div><strong>{candidate.name}</strong><span>{candidate.role} · {candidate.level} · {candidate.score} баллов</span></div><em>{candidate.availableFrom ? "Готов к выходу" : "Дата не указана"}</em></div>)}</div>
          {!scheduled.length && <div className="empty-state">В профилях пока нет дат готовности</div>}
        </section>
      </div>
    );
  }

  if (active === "Вакансии компании") {
    const shownVacancies = vacancies.filter((vacancy) =>
      vacancyListFilter === "all" || vacancy.is_published === (vacancyListFilter === "published"),
    );
    const formatSalary = (vacancy: VacancyRecord) =>
      `${new Intl.NumberFormat("ru-RU").format(vacancy.salary_min)}–${new Intl.NumberFormat("ru-RU").format(vacancy.salary_max)} ₽ ${vacancy.salary_tax_type === "net" ? "на руки" : "до вычета НДФЛ"}`;
    return (
      <div className="page-content">
        <div className="vacancy-head"><div><strong>Вакансии компании</strong><span>Управляйте публикациями и откликами кандидатов</span></div><Button onClick={() => { resetVacancyForm(); setVacancyEditor(!vacancyEditor); setApplicationsVacancy(null); }}><span className="button-plus">+</span> Создать вакансию</Button></div>
        {vacancyEditor && (
          <section className="feature-card vacancy-editor">
            <div className="feature-head"><div><span>{vacancyEditingId ? "РЕДАКТИРОВАНИЕ" : "НОВАЯ ВАКАНСИЯ"}</span><strong>Основные условия</strong></div><Button variant="ghost" onClick={() => { setVacancyEditor(false); resetVacancyForm(); }}>Закрыть</Button></div>
            <div className="field-row field-row--flush">
              <label className="field"><span>НАЗВАНИЕ *</span><input value={vacancyForm.title} onChange={(event) => setVacancyForm((current) => ({ ...current, title: event.target.value }))} /></label>
              <label className="field"><span>СПЕЦИАЛИЗАЦИЯ *</span><select value={vacancyForm.specialization} onChange={(event) => setVacancyForm((current) => ({ ...current, specialization: event.target.value }))}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field"><span>УРОВЕНЬ *</span><select value={vacancyForm.required_grade} onChange={(event) => setVacancyForm((current) => ({ ...current, required_grade: event.target.value }))}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
              <label className="field"><span>ФОРМАТ *</span><select value={vacancyForm.work_format} onChange={(event) => setVacancyForm((current) => ({ ...current, work_format: event.target.value }))}><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field"><span>ЗАРПЛАТА ОТ, ₽ *</span><input inputMode="numeric" value={vacancyForm.salary_min} onChange={(event) => setVacancyForm((current) => ({ ...current, salary_min: event.target.value }))} /></label>
              <label className="field"><span>ЗАРПЛАТА ДО, ₽ *</span><input inputMode="numeric" value={vacancyForm.salary_max} onChange={(event) => setVacancyForm((current) => ({ ...current, salary_max: event.target.value }))} /></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field"><span>НАЛОГОВАЯ ПОМЕТКА *</span><select value={vacancyForm.salary_tax_type} onChange={(event) => setVacancyForm((current) => ({ ...current, salary_tax_type: event.target.value as "gross" | "net" }))}><option value="gross">До вычета НДФЛ</option><option value="net">На руки</option></select></label>
              <label className="field"><span>ГОРОД</span><input value={vacancyForm.city} onChange={(event) => setVacancyForm((current) => ({ ...current, city: event.target.value }))} /></label>
            </div>
            <label className="field field--flush"><span>НАВЫКИ ЧЕРЕЗ ЗАПЯТУЮ</span><input value={vacancyForm.required_skills} onChange={(event) => setVacancyForm((current) => ({ ...current, required_skills: event.target.value }))} placeholder="Python, FastAPI, PostgreSQL" /></label>
            <label className="field field--flush"><span>ОПИСАНИЕ</span><textarea value={vacancyForm.description} onChange={(event) => setVacancyForm((current) => ({ ...current, description: event.target.value }))} /></label>
            <div className="modal__actions"><Button variant="outline" onClick={() => { setVacancyEditor(false); resetVacancyForm(); }}>Отмена</Button><Button disabled={vacancySaving} onClick={() => void saveVacancy()}>{vacancySaving ? "Сохраняем…" : vacancyEditingId ? "Сохранить изменения" : "Сохранить черновик"}</Button></div>
          </section>
        )}
        <div className="vacancy-tabs" role="tablist" aria-label="Фильтр вакансий">
          <button type="button" className={vacancyListFilter === "published" ? "active" : ""} onClick={() => { setVacancyListFilter("published"); setApplicationsVacancy(null); }}>Опубликованы · {vacancies.filter((item) => item.is_published).length}</button>
          <button type="button" className={vacancyListFilter === "drafts" ? "active" : ""} onClick={() => { setVacancyListFilter("drafts"); setApplicationsVacancy(null); }}>Не опубликованы · {vacancies.filter((item) => !item.is_published).length}</button>
          <button type="button" className={vacancyListFilter === "all" ? "active" : ""} onClick={() => { setVacancyListFilter("all"); setApplicationsVacancy(null); }}>Все вакансии · {vacancies.length}</button>
        </div>
        {vacanciesLoading ? <div className="empty-state">Загружаем вакансии…</div> : null}
        <div className="vacancy-management">
          {shownVacancies.map((vacancy) => (
            <article key={vacancy.id}>
              <div className="need-row__icon"><Icon name="briefcase" /></div>
              <div className="vacancy-management__main"><strong>{vacancy.title}</strong><span>{vacancy.specialization} · {vacancy.required_grade} · {formatSalary(vacancy)}</span>{vacancy.required_skills.length > 0 && <div className="mini-tags">{vacancy.required_skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}</div>}</div>
              <em className={vacancy.is_published ? "vacancy-status vacancy-status--published" : "vacancy-status"}>{vacancy.is_published ? "Опубликована" : "Не опубликована"}</em>
              <div className="vacancy-management__actions">
                <Button variant="outline" onClick={() => editVacancy(vacancy)}>Редактировать</Button>
                <Button variant={vacancy.is_published ? "ghost" : "primary"} onClick={() => void toggleVacancyPublication(vacancy)}>{vacancy.is_published ? "Снять" : "Опубликовать"}</Button>
                <Button variant="ghost" onClick={() => { setVacancyEditor(false); void loadVacancyApplications(vacancy); }}>Отклики</Button>
              </div>
            </article>
          ))}
          {!vacanciesLoading && shownVacancies.length === 0 && <div className="empty-state">{vacancyListFilter === "published" ? "Опубликованных вакансий пока нет." : vacancyListFilter === "drafts" ? "Неопубликованных вакансий пока нет." : "Вакансий пока нет. Создайте первую вакансию."}</div>}
        </div>
        {applicationsVacancy && <section className="feature-card vacancy-applications">
          <div className="feature-head"><div><span>ОТКЛИКИ</span><strong>{vacancies.find((item) => item.id === applicationsVacancy)?.title}</strong></div><Button variant="ghost" onClick={() => setApplicationsVacancy(null)}>Закрыть</Button></div>
          {applicationsLoading ? <div className="empty-state">Загружаем отклики…</div> : vacancyApplications.length === 0 ? <div className="empty-state">Откликов пока нет</div> : vacancyApplications.map((application) => (
            <article className="vacancy-application" key={application.id}>
              <div className="avatar">{`${application.candidate.first_name[0] ?? ""}${application.candidate.last_name[0] ?? ""}`}</div>
              <div className="vacancy-application__person"><strong>{application.candidate.first_name} {application.candidate.last_name}</strong><span>{application.candidate.specialization ?? "Специализация не указана"} · {application.candidate.verified_grade ?? "Грейд не подтверждён"} · {application.candidate.city ?? "Город не указан"}</span><span>{application.candidate.email}{application.candidate.phone ? ` · ${application.candidate.phone}` : ""}{application.candidate.telegram ? ` · ${application.candidate.telegram}` : ""}</span>{application.cover_letter && <p>{application.cover_letter}</p>}</div>
              <span className="vacancy-application__status">{application.status === "accepted" ? "Принят" : application.status === "rejected" ? "Отклонён" : application.status === "reviewed" ? "Просмотрен" : "Новый"}</span>
              {demoMode && <Button variant="outline" onClick={() => onNavigate("Диалоги", `application:${application.id}`)}>Открыть диалог</Button>}
              {application.status !== "accepted" && application.status !== "rejected" && <div className="vacancy-application__actions"><Button variant="outline" onClick={() => void updateVacancyApplication(application.id, "reviewed")}>Просмотрен</Button><Button onClick={() => void updateVacancyApplication(application.id, "accepted")}>Принять</Button><Button variant="ghost" onClick={() => void updateVacancyApplication(application.id, "rejected")}>Отклонить</Button></div>}
            </article>
          ))}
        </section>}
      </div>
    );
  }

  if (active === "Аналитика") {
    return (
      <div className="page-content">
        <div className="metrics-grid">
          <MetricCard label="ТОЧНОСТЬ TOP-3" value="87%" detail="Цель ≥ 80%" accent icon="target" />
          <MetricCard label="СРЕДНЕЕ СОВПАДЕНИЕ" value="82%" detail="+6% за месяц" icon="chart" />
          <MetricCard label="ДО ОТВЕТА КАНДИДАТА" value="18 ч" detail="-4 часа за месяц" icon="clock" />
          <MetricCard label="ПРИНЯТЫЕ ПРИГЛАШЕНИЯ" value="50%" detail="8 из 16" icon="check" />
        </div>
        <div className="dashboard-grid">
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ДИНАМИКА ЗА 6 НЕДЕЛЬ</span><strong>Релевантность подборок</strong></div></div>
            <div className="bar-chart">
              {[62, 68, 72, 70, 81, 87].map((value, index) => <div key={value}><span style={{ height: `${value}%` }} /><small>{index + 1} нед.</small></div>)}
            </div>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>РАЗРЫВ В НАВЫКАХ</span><strong>Над чем стоит поработать</strong></div></div>
            <div className="funnel">
              <div><span>CI/CD</span><strong>38%</strong><Progress value={38} /></div>
              <div><span>Тестирование</span><strong>31%</strong><Progress value={31} /></div>
              <div><span>Алгоритмы</span><strong>22%</strong><Progress value={22} /></div>
              <div><span>Безопасность</span><strong>19%</strong><Progress value={19} /></div>
            </div>
          </section>
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ПЛАН ВЫХОДОВ</span><strong>Когда кандидаты готовы начать</strong></div><Button variant="outline">Экспорт календаря</Button></div>
            <div className="start-dates">
              {[
                ["27 мая", "Алексей Морозов", "Backend · Middle", "Оффер согласован"],
                ["3 июня", "Елена Смирнова", "Backend · Middle", "Финальное интервью"],
                ["10 июня", "Анна Петрова", "Backend · Senior", "Обсуждение условий"],
                ["17 июня", "Роман Гусев", "DevOps · Middle", "Резерв"],
              ].map((item, index) => <div key={item[1]}><b>{item[0]}</b><i className={index === 0 ? "active" : ""} /><div><strong>{item[1]}</strong><span>{item[2]}</span></div><em>{item[3]}</em></div>)}
            </div>
          </section>
          <section className="feature-card validation-card">
            <div className="feature-head"><div><span>ВАЛИДАЦИЯ ТЕСТИРОВАНИЯ</span><strong>Качество оценки</strong></div></div>
            <div className="validation-metrics"><div><span>Разделение уровней</span><strong>p = 0,018</strong><small>Статистически значимо</small></div><div><span>Повторный проход</span><strong>Δ 0,21</strong><small>Цель меньше 0,30</small></div><div><span>Разные задания</span><strong>Δ 0,34</strong><small>Цель меньше 0,50</small></div><div><span>Релевантный в топ-3</span><strong>87%</strong><small>Цель не ниже 80%</small></div></div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="settings-layout">
        <section className="feature-card">
          <div className="feature-head"><div><span>КОМПАНИЯ</span><strong>{companyProfile?.company_name || "Профиль компании"}</strong></div></div>
          {companyLoading && <div className="empty-state">Загружаем данные компании…</div>}
          <label className="field field--flush"><span>НАЗВАНИЕ КОМПАНИИ</span><input value={companyProfile?.company_name ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, company_name: event.target.value } : current)} /></label>
          <label className="field field--flush"><span>ОПИСАНИЕ</span><textarea value={companyProfile?.description ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, description: event.target.value } : current)} /></label>
          <div className="field-row field-row--flush"><label className="field"><span>ОТРАСЛЬ</span><input value={companyProfile?.industry ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, industry: event.target.value } : current)} /></label><label className="field"><span>ГОРОД</span><input value={companyProfile?.city ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, city: event.target.value } : current)} /></label></div>
          <div className="field-row field-row--flush"><label className="field"><span>САЙТ</span><input value={companyProfile?.website ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, website: event.target.value } : current)} /></label><label className="field"><span>КОНТАКТНОЕ ЛИЦО</span><input value={companyProfile?.contact_person ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, contact_person: event.target.value } : current)} /></label></div>
          <div className="field-row field-row--flush"><label className="field"><span>EMAIL АККАУНТА</span><input value={companyProfile?.email ?? ""} readOnly /></label><label className="field"><span>ТЕЛЕФОН</span><input value={companyProfile?.phone ?? ""} onChange={(event) => setCompanyProfile((current) => current ? { ...current, phone: event.target.value } : current)} /></label></div>
          <Button disabled={!companyProfile || companyLoading} className={saved ? "button--success" : ""} onClick={() => void saveCompanyProfile()}>{saved ? "Сохранено" : companyProfile?.onboarding_completed ? "Сохранить изменения" : "Завершить профиль компании"}</Button>
        </section>
        <section className="feature-card">
          <div className="feature-head"><div><span>ИНТЕГРАЦИИ</span><strong>Подключения компании</strong></div></div>
          <div className="integration-card"><Icon name="settings" /><div><strong>ATS-интеграция</strong><span>Подключение не настроено</span></div></div>
        </section>
      </div>
    </div>
  );
}

function ToggleRow({ title, detail, checked = false }: { title: string; detail: string; checked?: boolean }) {
  const [enabled, setEnabled] = useState(checked);
  return (
    <button type="button" className="toggle-row" onClick={() => setEnabled(!enabled)}>
      <div><strong>{title}</strong><span>{detail}</span></div>
      <i className={enabled ? "toggle toggle--on" : "toggle"}><b /></i>
    </button>
  );
}

function Invitations({ employer = false, onNotify, onNavigate }: { employer?: boolean; onNotify?: (message: string, type?: "success" | "error") => void; onNavigate: (screen: string, target?: string) => void }) {
  const [items, setItems] = useState<Array<{
    id: string;
    company_name: string;
    candidate_name: string;
    need_title: string | null;
    offer_description: string;
    contact_method: string;
    salary_min: number;
    salary_max: number;
    salary_tax_type: "gross" | "net";
    currency: string;
    status: string;
    candidate_reply: string | null;
    candidate_contacts: { email: string; phone: string | null; telegram: string | null } | null;
  }>>([]);
  const [filter, setFilter] = useState("Все");
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [unreadByInvitation, setUnreadByInvitation] = useState<Record<string, number>>({});

  useEffect(() => {
    setLoading(true);
    apiGet<typeof items>(employer ? "/invitations/sent" : "/invitations/my")
      .then(setItems)
      .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить приглашения"))
      .finally(() => setLoading(false));
  }, [employer]);

  useEffect(() => {
    const refresh = () => {
      apiGet<InvitationUnreadCount>("/invitations/messages/unread-count")
        .then((result) => setUnreadByInvitation(result.by_invitation))
        .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить счётчик сообщений"));
    };
    refresh();
    window.addEventListener("fsp-invitations-updated", refresh);
    return () => window.removeEventListener("fsp-invitations-updated", refresh);
  }, [employer]);

  const statusLabels: Record<string, string> = {
    sent: "Отправлено",
    viewed: "Просмотрено",
    accepted: "Принято",
    rejected: "Отклонено",
  };
  const filteredItems = items.filter((item) =>
    filter === "Все" || statusLabels[item.status] === filter,
  );
  const actOnInvitation = async (id: string, action: "accept" | "reject") => {
    setPendingId(id);
    try {
      const updated = await apiPost<(typeof items)[number]>(`/invitations/${id}/${action}`, {});
      setItems((current) => current.map((item) => item.id === id ? updated : item));
      window.dispatchEvent(new Event("fsp-invitations-updated"));
      onNotify?.(action === "accept" ? "Приглашение принято. Работодатель увидит контакты в статусе отклика." : "Приглашение отклонено.");
    } catch (requestError) {
      onNotify?.(requestError instanceof Error ? requestError.message : "Не удалось обновить приглашение", "error");
    } finally {
      setPendingId(null);
    }
  };
  const money = (value: number) => new Intl.NumberFormat("ru-RU").format(value);

  return (
    <div className="page-content">
      <div className="tab-row">{["Все", "Отправлено", "Просмотрено", "Принято", "Отклонено"].map((label) => <button type="button" key={label} className={filter === label ? "active" : ""} onClick={() => setFilter(label)}>{label}{label === "Все" && <span>{items.length}</span>}</button>)}</div>
      {error && <div className="form-error" role="alert">{error}</div>}
      {loading ? <div className="empty-state">Загружаем приглашения…</div> : filteredItems.length === 0 ? <div className="empty-state">Приглашений в этом разделе пока нет</div> : (
        <div className="invitation-list">
          {filteredItems.map((item) => (
                <article className={`invitation-card ${employer ? "invitation-card--employer" : "invitation-card--candidate"}`} key={item.id}>
              <div className="invitation-logo">{(employer ? item.candidate_name : item.company_name).slice(0, 2).toUpperCase()}</div>
              <div className="invitation-main">
                <span>{employer ? "КАНДИДАТ" : "ПРИГЛАШЕНИЕ ОТ КОМПАНИИ"}</span>
                <strong>{employer ? item.candidate_name : item.company_name}</strong>
                <p>{item.need_title ?? "Предложение о работе"}</p>
                <p className="invitation-description">{item.offer_description}</p>
                <div className="tags"><span>{money(item.salary_min)}–{money(item.salary_max)} ₽ {item.salary_tax_type === "net" ? "на руки" : "до вычета НДФЛ"}</span>{(employer || item.status !== "accepted") && <span>Связь: {item.contact_method}</span>}</div>
                {item.candidate_reply && <p className="invitation-description">Ответ: {item.candidate_reply}</p>}
              </div>
              <div className="invitation-status"><span className={`status-pill status-pill--${item.status === "accepted" ? "green" : "violet"}`}>{statusLabels[item.status] ?? item.status}</span></div>
              {!employer && ["sent", "viewed"].includes(item.status) && <div className="invitation-actions"><Button variant="ghost" disabled={pendingId === item.id} onClick={() => actOnInvitation(item.id, "reject")}>Отклонить</Button><Button disabled={pendingId === item.id} onClick={() => actOnInvitation(item.id, "accept")}>{pendingId === item.id ? "Сохраняем…" : "Принять"}</Button></div>}
              {employer && item.candidate_contacts && <div className="contact-box"><span>КОНТАКТ КАНДИДАТА</span><strong>{item.candidate_contacts.email}</strong>{item.candidate_contacts.telegram && <small>{item.candidate_contacts.telegram}</small>}{item.candidate_contacts.phone && <small>{item.candidate_contacts.phone}</small>}</div>}
              {!employer && item.status === "accepted" && <div className="contact-box"><span>КОНТАКТ КОМПАНИИ</span><strong>{item.contact_method}</strong></div>}
              {item.status === "accepted" && <div className="invitation-chat-action"><Button variant="outline" onClick={() => onNavigate("Диалоги", `invitation:${item.id}`)}>Перейти к диалогу{unreadByInvitation[item.id] ? ` · ${unreadByInvitation[item.id]} новых` : ""}</Button></div>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function DialogsScreen({
  employer,
  demoMode,
  initialTarget,
  onClearInitialTarget,
  onNotify,
}: {
  employer: boolean;
  demoMode: boolean;
  initialTarget: string | null;
  onClearInitialTarget: () => void;
  onNotify: (message: string, type?: "success" | "error") => void;
}) {
  const [invitations, setInvitations] = useState<DialogueInvitation[]>([]);
  const [networkConversations, setNetworkConversations] = useState<NetworkConversation[]>([]);
  const [applicationChats, setApplicationChats] = useState<ApplicationDialogue[]>([]);
  const [mentors, setMentors] = useState<MentorProfile[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(initialTarget);
  const [skillQuery, setSkillQuery] = useState("");
  const [mentorTarget, setMentorTarget] = useState<MentorProfile | null>(null);
  const [directoryMode, setDirectoryMode] = useState<"chats" | "mentors">("chats");
  const [requestMessage, setRequestMessage] = useState("");
  const [requestSending, setRequestSending] = useState(false);
  const [verifiedGrade, setVerifiedGrade] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    try {
      const invitationRequest = apiGet<DialogueInvitation[]>(employer ? "/invitations/sent" : "/invitations/my");
      const networkRequest = employer
        ? Promise.resolve([] as NetworkConversation[])
        : apiGet<NetworkConversation[]>("/network/conversations");
      const profileRequest = employer
        ? Promise.resolve(null)
        : apiGet<CandidateProfileData>("/candidate/profile");
      const applicationRequest = demoMode
        ? apiGet<ApplicationDialogue[]>("/vacancies/applications/conversations")
        : Promise.resolve([] as ApplicationDialogue[]);
      const [invitationItems, networkItems, candidateProfile, applicationItems] = await Promise.all([invitationRequest, networkRequest, profileRequest, applicationRequest]);
      setInvitations(invitationItems.filter((item) => item.status === "accepted"));
      setNetworkConversations(networkItems);
      setVerifiedGrade(candidateProfile?.verified_grade ?? null);
      setApplicationChats(applicationItems);
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить диалоги");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, [employer, demoMode]);

  useEffect(() => {
    if (!initialTarget) return;
    setSelectedTarget(initialTarget);
    onClearInitialTarget();
  }, [initialTarget]);

  const findMentors = async (event: FormEvent) => {
    event.preventDefault();
    if (!verifiedGrade) {
      onNotify("Сначала подтвердите свой грейд в разделе «Мой грейд», чтобы найти наставника выше вашего уровня.", "error");
      return;
    }
    try {
      const params = new URLSearchParams();
      if (skillQuery.trim()) params.set("skill", skillQuery.trim());
      setMentors(await apiGet<MentorProfile[]>(`/network/mentors?${params.toString()}`));
    } catch (requestError) {
      onNotify(requestError instanceof Error ? requestError.message : "Не удалось найти наставников", "error");
    }
  };

  const sendMentorshipRequest = async (event: FormEvent) => {
    event.preventDefault();
    if (!mentorTarget || !requestMessage.trim()) return;
    setRequestSending(true);
    try {
      const conversation = await apiPost<NetworkConversation>("/network/mentorship-requests", {
        mentor_user_id: mentorTarget.user_id,
        skill_focus: skillQuery.trim() || mentorTarget.skills[0] || "Профессиональный рост",
        message: requestMessage.trim(),
      });
      await refresh();
      setSelectedTarget(`network:${conversation.id}`);
      setDirectoryMode("chats");
      setMentorTarget(null);
      setRequestMessage("");
      onNotify("Запрос наставнику отправлен");
    } catch (requestError) {
      onNotify(requestError instanceof Error ? requestError.message : "Не удалось отправить запрос", "error");
    } finally {
      setRequestSending(false);
    }
  };

  const invitationTarget = selectedTarget?.startsWith("invitation:")
    ? selectedTarget.slice("invitation:".length)
    : null;
  const networkTarget = selectedTarget?.startsWith("network:")
    ? selectedTarget.slice("network:".length)
    : null;
  const selectedInvitation = invitations.find((item) => item.id === invitationTarget);
  const selectedNetworkConversation = networkConversations.find((item) => item.id === networkTarget);
  const applicationTarget = selectedTarget?.startsWith("application:")
    ? selectedTarget.slice("application:".length)
    : null;
  const selectedApplicationChat = applicationChats.find((item) => item.id === applicationTarget);

  return (
    <div className="page-content dialogues-page">
      <div className="dialogues-intro"><div><span>ОБЩЕНИЕ БЕЗ ПОТЕРИ КОНТЕКСТА</span><strong>{employer ? "Компании и кандидаты — в одном месте" : "Рабочие контакты и рост в профессии"}</strong><p>{employer ? "Здесь собраны чаты только по принятым приглашениям." : "Обсуждайте принятые приглашения и находите наставников с подтверждённым более высоким грейдом."}</p></div><div className="dialogues-intro__icon"><Icon name="send" size={22} /></div></div>
      {error && <div className="form-error" role="alert">{error}</div>}
      {!employer && <div className="dialogues-mode-switch" role="tablist" aria-label="Разделы общения">
        <button type="button" role="tab" aria-selected={directoryMode === "chats"} className={directoryMode === "chats" ? "active" : ""} onClick={() => setDirectoryMode("chats")}><Icon name="send" size={16} /> Диалоги <span>{invitations.length + networkConversations.length}</span></button>
        <button type="button" role="tab" aria-selected={directoryMode === "mentors"} className={directoryMode === "mentors" ? "active" : ""} onClick={() => setDirectoryMode("mentors")}><Icon name="school" size={16} /> Найти ментора</button>
      </div>}
      <div className={`dialogues-layout ${selectedTarget || mentorTarget ? "dialogues-layout--thread-open" : ""}`}>
        <aside className="dialogues-list">
          {directoryMode === "chats" && <><div className="dialogues-list__heading"><strong>Ваши диалоги</strong><Button variant="ghost" onClick={() => void refresh()} aria-label="Обновить диалоги"><Icon name="refresh" size={15} /></Button></div>
          {loading && <div className="empty-state">Обновляем список…</div>}
          {applicationChats.map((item) => {
            const target = `application:${item.id}`;
            const otherName = employer ? item.candidate_name : item.company_name;
            return <button type="button" className={`dialogue-list-item dialogue-list-item--application ${selectedTarget === target ? "dialogue-list-item--active" : ""}`} key={target} onClick={() => setSelectedTarget(target)}>
              <span className="dialogue-list-item__avatar dialogue-list-item__avatar--application">{otherName.slice(0, 2).toUpperCase()}</span><span className="dialogue-list-item__body"><strong>{otherName}</strong><small>{item.vacancy_title}</small><span>{item.last_message || "Отклик · ждёт ответа"}</span></span><Icon name="briefcase" size={15} />
            </button>;
          })}
          {invitations.map((item) => {
            const target = `invitation:${item.id}`;
            const otherName = employer ? item.candidate_name : item.company_name;
            return <button type="button" className={`dialogue-list-item ${selectedTarget === target ? "dialogue-list-item--active" : ""}`} key={target} onClick={() => setSelectedTarget(target)}>
              <span className="dialogue-list-item__avatar">{otherName.slice(0, 2).toUpperCase()}</span><span className="dialogue-list-item__body"><strong>{otherName}</strong><small>{item.need_title || "Принятое приглашение"}</small><span>Рабочее приглашение</span></span><Icon name="chevron" size={15} />
            </button>;
          })}
          {!employer && networkConversations.map((item) => {
            const target = `network:${item.id}`;
            return <button type="button" className={`dialogue-list-item ${selectedTarget === target ? "dialogue-list-item--active" : ""}`} key={target} onClick={() => setSelectedTarget(target)}>
              <span className="dialogue-list-item__avatar dialogue-list-item__avatar--mentor">{item.other_name.slice(0, 2).toUpperCase()}</span><span className="dialogue-list-item__body"><strong>{item.other_name}</strong><small>Наставник · {item.skill_focus}</small><span>{item.status === "pending" ? item.can_accept ? "Новый запрос" : "Ожидает ответа" : item.last_message || "Диалог наставничества"}</span></span><Icon name={item.can_accept ? "sparkle" : "chevron"} size={15} />
            </button>;
          })}
          {!loading && invitations.length === 0 && applicationChats.length === 0 && (employer || networkConversations.length === 0) && <div className="dialogues-empty">Пока нет диалогов. Принятые приглашения и отклики на вакансии появятся здесь.</div>}
          </>}
          {!employer && directoryMode === "mentors" && <section className="mentor-finder">
            <div><span>ПРОФЕССИОНАЛЬНЫЙ РОСТ</span><strong>Найти ментора</strong><p>{verifiedGrade ? "Показываем только тех, кто включил наставничество и подтвердил грейд выше вашего." : "Сначала подтвердите свой грейд — так мы найдём специалистов, которые действительно выше по уровню."}</p></div>
            <form onSubmit={(event) => void findMentors(event)}><label htmlFor="mentor-skill">Какой навык прокачать?</label><div className="search-field"><Icon name="search" /><input id="mentor-skill" value={skillQuery} onChange={(event) => setSkillQuery(event.target.value)} placeholder="Например, PostgreSQL" /></div><Button type="submit" variant="outline" disabled={!verifiedGrade}><Icon name="search" /> Найти ментора</Button></form>
            {mentors.map((mentor) => <article className="mentor-card" key={mentor.user_id}><div className="mentor-card__identity"><span className="dialogue-list-item__avatar dialogue-list-item__avatar--mentor">{mentor.name.slice(0, 2).toUpperCase()}</span><div><strong>{mentor.name}</strong><span>{mentor.specialization || "IT"} · {mentor.verified_grade}</span></div></div><div className="mini-tags">{mentor.skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}</div><Button variant="outline" onClick={() => { setMentorTarget(mentor); setRequestMessage(`Здравствуйте! Хочу прокачать ${skillQuery.trim() || mentor.skills[0] || "навыки"} и подготовиться к следующему грейду. Будете готовы стать моим наставником?`); }}>Запросить поддержку</Button></article>)}
            {mentors.length === 0 && <span className="mentor-finder__hint">Наставники появятся после поиска по навыку.</span>}
          </section>}
        </aside>
        <section className="dialogues-thread">
          {selectedInvitation && <InvitationChatDialog
            embedded
            invitationId={selectedInvitation.id}
            title={employer ? selectedInvitation.candidate_name : selectedInvitation.company_name}
            onClose={() => { setSelectedTarget(null); window.dispatchEvent(new Event("fsp-invitations-updated")); }}
          />}
          {selectedApplicationChat && <VacancyApplicationChat
            application={selectedApplicationChat}
            employer={employer}
            onRefresh={refresh}
          />}
          {selectedNetworkConversation && <NetworkChatPanel conversation={selectedNetworkConversation} onRefresh={refresh} onNotify={onNotify} />}
          {mentorTarget && <form className="mentor-request-card" onSubmit={(event) => void sendMentorshipRequest(event)}><div><span>ЗАПРОС НА НАСТАВНИЧЕСТВО</span><strong>{mentorTarget.name}</strong><small>{mentorTarget.verified_grade} · фокус: {skillQuery.trim() || mentorTarget.skills[0]}</small></div><label htmlFor="mentor-request-message">Коротко расскажите, с чем нужна помощь</label><textarea id="mentor-request-message" value={requestMessage} maxLength={4000} onChange={(event) => setRequestMessage(event.target.value)} rows={5} /><div><Button type="button" variant="ghost" onClick={() => setMentorTarget(null)}>Отмена</Button><Button type="submit" disabled={!requestMessage.trim() || requestSending}>{requestSending ? "Отправляем…" : "Отправить запрос"} <Icon name="send" /></Button></div></form>}
          {!selectedInvitation && !selectedNetworkConversation && !mentorTarget && <div className="dialogues-placeholder"><div><Icon name="send" size={24} /><strong>Выберите диалог</strong><span>История, контекст приглашения и отправка сообщений будут здесь.</span></div></div>}
        </section>
      </div>
    </div>
  );
}

function VacancyApplicationChat({
  application,
  employer,
  onRefresh,
}: {
  application: ApplicationDialogue;
  employer: boolean;
  onRefresh: () => Promise<void>;
}) {
  const [messages, setMessages] = useState<InvitationChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const result = await apiGet<{ messages: InvitationChatMessage[] }>(`/vacancies/applications/${application.id}/messages`);
        if (!cancelled) { setMessages(result.messages); setError(""); }
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить сообщения");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [application.id]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim()) return;
    setSending(true);
    try {
      const message = await apiPost<InvitationChatMessage>(`/vacancies/applications/${application.id}/messages`, { body: draft.trim() });
      setMessages((current) => [...current, message]);
      setDraft("");
      await onRefresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  };

  return <div className="conversation-panel application-conversation">
    <header className="conversation-panel__header"><div><span>ОТКЛИК НА ВАКАНСИЮ · {application.status === "pending" ? "НА РАССМОТРЕНИИ" : application.status.toUpperCase()}</span><strong>{employer ? application.candidate_name : application.company_name}</strong><small>{application.vacancy_title}</small></div><span className="dialogue-list-item__avatar dialogue-list-item__avatar--application">{(employer ? application.candidate_name : application.company_name).slice(0, 2).toUpperCase()}</span></header>
    <div className="application-conversation__note"><Icon name="info" size={15} /> Демо-чат отклика. История сохраняется в этой демонстрационной сессии.</div>
    {error && <div className="conversation-error" role="alert">{error}</div>}
    <div className="conversation-messages" aria-label="Переписка по отклику">
      {loading ? <div className="empty-state">Загружаем историю…</div> : messages.length === 0 ? <div className="empty-state">Начните общение по отклику.</div> : messages.map((message) => <article className={`conversation-message ${message.is_mine ? "conversation-message--mine" : ""}`} key={message.id}><p>{message.body}</p><time dateTime={message.created_at}>{new Date(message.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}</time></article>)}
      <div ref={bottomRef} />
    </div>
    <form className="conversation-composer" onSubmit={(event) => void send(event)}>
      <label htmlFor={`application-draft-${application.id}`}>Сообщение</label><textarea id={`application-draft-${application.id}`} value={draft} maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Напишите по поводу вакансии…" rows={3} />
      <div><small>{draft.length}/4000</small><Button type="submit" disabled={!draft.trim() || sending}>{sending ? "Отправляем…" : "Отправить"} <Icon name="send" /></Button></div>
    </form>
  </div>;
}

function NetworkChatPanel({
  conversation,
  onRefresh,
  onNotify,
}: {
  conversation: NetworkConversation;
  onRefresh: () => Promise<void>;
  onNotify: (message: string, type?: "success" | "error") => void;
}) {
  const [messages, setMessages] = useState<NetworkMessage[]>([]);
  const draftKey = `fsp-chat-draft:network:${conversation.id}`;
  const [draft, setDraft] = useState(() => window.sessionStorage.getItem(draftKey) ?? "");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    const load = async () => {
      try {
        const result = await apiGet<{ messages: NetworkMessage[] }>(`/network/conversations/${conversation.id}/messages`);
        if (!cancelled) { setMessages(result.messages); setError(""); }
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить сообщения");
      }
      if (!cancelled) timer = window.setTimeout(() => void load(), 5000);
    };
    void load();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [conversation.id]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);
  useEffect(() => {
    if (draft) window.sessionStorage.setItem(draftKey, draft);
    else window.sessionStorage.removeItem(draftKey);
  }, [draft, draftKey]);

  const decideRequest = async (decision: "accept" | "decline") => {
    try {
      await apiPost(`/network/conversations/${conversation.id}/${decision}`, {});
      await onRefresh();
      onNotify(decision === "accept" ? "Запрос принят — можно начинать диалог" : "Запрос отклонён");
    } catch (requestError) {
      onNotify(requestError instanceof Error ? requestError.message : "Не удалось обновить запрос", "error");
    }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || conversation.status !== "accepted") return;
    setSending(true);
    try {
      const message = await apiPost<NetworkMessage>(`/network/conversations/${conversation.id}/messages`, { body: draft.trim() });
      setMessages((current) => [...current, message]);
      setDraft("");
      window.sessionStorage.removeItem(draftKey);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  };

  return <div className="conversation-panel">
    <header className="conversation-panel__header"><div><span>НАСТАВНИЧЕСТВО · {conversation.skill_focus}</span><strong>{conversation.other_name}</strong><small>{conversation.status === "accepted" ? "Наставничество подтверждено" : conversation.can_accept ? "Входящий запрос" : "Ожидает ответа наставника"}</small></div><span className="dialogue-list-item__avatar dialogue-list-item__avatar--mentor">{conversation.other_name.slice(0, 2).toUpperCase()}</span></header>
    {error && <div className="conversation-error" role="alert">{error}</div>}
    <div className="conversation-messages">{messages.length ? messages.map((message) => <article className={`conversation-message ${message.is_mine ? "conversation-message--mine" : ""}`} key={message.id}><p>{message.body}</p><time>{new Date(message.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}</time></article>) : <div className="empty-state">Загружаем переписку…</div>}<div ref={bottomRef} /></div>
    {conversation.status === "pending" && conversation.can_accept ? <div className="mentor-request-actions"><p>Кандидат хочет развиваться по навыку «{conversation.skill_focus}» и попросил вас стать наставником.</p><Button variant="outline" onClick={() => void decideRequest("decline")}>Пока нет</Button><Button onClick={() => void decideRequest("accept")}>Принять запрос</Button></div> : conversation.status === "pending" ? <div className="mentor-request-pending">Запрос отправлен. Чат откроется после согласия наставника.</div> : conversation.status === "accepted" ? <form className="conversation-composer" onSubmit={(event) => void send(event)}><label htmlFor={`network-draft-${conversation.id}`}>Сообщение</label><textarea id={`network-draft-${conversation.id}`} value={draft} maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Напишите сообщение…" rows={3} /><div><small>{draft.length}/4000</small><Button type="submit" disabled={!draft.trim() || sending}>{sending ? "Отправляем…" : "Отправить"} <Icon name="send" /></Button></div></form> : <div className="mentor-request-pending">Этот запрос закрыт.</div>}
  </div>;
}

function InvitationChatDialog({
  invitationId,
  title,
  onClose,
  embedded = false,
}: {
  invitationId: string;
  title: string;
  onClose: () => void;
  embedded?: boolean;
}) {
  const [messages, setMessages] = useState<InvitationChatMessage[]>([]);
  const draftKey = `fsp-chat-draft:invitation:${invitationId}`;
  const [draft, setDraft] = useState(() => window.sessionStorage.getItem(draftKey) ?? "");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [discardConfirm, setDiscardConfirm] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const reportedReadRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    const refresh = async () => {
      try {
        const response = await apiGet<{ messages: InvitationChatMessage[]; unread_count: number }>(
          `/invitations/${invitationId}/messages`,
        );
        if (!cancelled) {
          setMessages(response.messages);
          setError("");
          if (!reportedReadRef.current) {
            reportedReadRef.current = true;
            window.dispatchEvent(new Event("fsp-invitations-updated"));
          }
        }
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : "Не удалось обновить переписку");
      } finally {
        if (!cancelled) {
          setLoading(false);
          timer = window.setTimeout(() => void refresh(), 5000);
        }
      }
    };
    void refresh();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [invitationId]);

  useEffect(() => {
    if (draft) window.sessionStorage.setItem(draftKey, draft);
    else window.sessionStorage.removeItem(draftKey);
  }, [draft, draftKey]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const sendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const sent = await apiPost<InvitationChatMessage>(`/invitations/${invitationId}/messages`, { body: text });
      setMessages((current) => [...current.filter((message) => message.id !== sent.id), sent]);
      setDraft("");
      window.sessionStorage.removeItem(draftKey);
      setError("");
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  };

  const requestClose = () => {
    if (draft.trim()) {
      setDiscardConfirm(true);
      return;
    }
    onClose();
  };

  if (discardConfirm) {
    return (
      <DiscardConfirmation
        title="Закрыть чат?"
        message="Ваше сообщение ещё не отправлено. Вернитесь к нему или закройте чат и удалите текст."
        onKeepEditing={() => setDiscardConfirm(false)}
        onDiscard={() => {
          setDraft("");
          window.sessionStorage.removeItem(draftKey);
          setDiscardConfirm(false);
          onClose();
        }}
      />
    );
  }

  const content = (
    <>
      <div className="conversation-modal__header">
        <div><span>ПРИНЯТОЕ ПРИГЛАШЕНИЕ</span><strong id="conversation-title">{title}</strong><small>Переписка сохраняется для участников приглашения</small></div>
        {embedded ? null : <button type="button" className="icon-button" aria-label="Закрыть чат" onClick={requestClose}><Icon name="close" /></button>}
      </div>
      {error && <div className="conversation-error" role="alert">{error}</div>}
      <div className="conversation-messages" aria-label="История сообщений">
        {loading ? <div className="empty-state">Загружаем историю…</div> : messages.length === 0 ? <div className="empty-state">Начните переписку — отправьте первое сообщение.</div> : messages.map((message) => (
          <article className={`conversation-message ${message.is_mine ? "conversation-message--mine" : ""}`} key={message.id}>
            <p>{message.body}</p>
            <time dateTime={message.created_at}>{new Date(message.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}</time>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>
      <form className="conversation-composer" onSubmit={(event) => void sendMessage(event)}>
        <label htmlFor="conversation-draft">Сообщение</label>
        <textarea id="conversation-draft" value={draft} maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Напишите сообщение…" rows={3} />
        <div><small>{draft.length}/4000 · обновляется автоматически</small><Button type="submit" disabled={!draft.trim() || sending}>{sending ? "Отправляем…" : "Отправить"} <Icon name="send" /></Button></div>
      </form>
    </>
  );
  return embedded
    ? <div className="conversation-panel">{content}</div>
    : <ModalFrame className="conversation-modal" labelledBy="conversation-title" onClose={requestClose}>{content}</ModalFrame>;
}

function CandidateScreen({ active, onNotify, onNavigate, demoMode }: { active: string; onNotify: (message: string, type?: "success" | "error") => void; onNavigate: (screen: string, target?: string) => void; demoMode: boolean }) {
  const [testPurpose, setTestPurpose] = useState<"grade" | "fsp-olympiad">("grade");
  const [testStarted, setTestStarted] = useState(false);
  const [question, setQuestion] = useState(0);
  const [answer, setAnswer] = useState("");
  const [selectedAnswers, setSelectedAnswers] = useState<string[]>([]);
  const [submittedAnswers, setSubmittedAnswers] = useState<Array<{ question_id: string; selected_answers: string[] }>>([]);
  const [testSession, setTestSession] = useState<TestStartData | null>(null);
  const [testResult, setTestResult] = useState<TestResultData | null>(null);
  const [radarComparison, setRadarComparison] = useState<RadarComparison | null>(null);
  const [testHistory, setTestHistory] = useState<TestHistoryData[]>([]);
  const [roadmap, setRoadmap] = useState<GradeRoadmapData | null>(null);
  const [additionalTests, setAdditionalTests] = useState<AdditionalSkillTestData[]>([]);
  const [testStarting, setTestStarting] = useState(false);
  const [testSubmitting, setTestSubmitting] = useState(false);
  const [testDone, setTestDone] = useState(false);
  const [taskDone, setTaskDone] = useState(false);
  const [taskDemoShown, setTaskDemoShown] = useState(false);
  const [demoTaskRadar, setDemoTaskRadar] = useState([6.2, 7.1, 6.8, 7.4]);
  const [saved, setSaved] = useState(false);
  const [jobVacancies, setJobVacancies] = useState<VacancyRecord[]>([]);
  const [jobApplications, setJobApplications] = useState<CandidateVacancyApplication[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobSearch, setJobSearch] = useState("");
  const [jobsTab, setJobsTab] = useState<"vacancies" | "applications">("vacancies");
  const [applyingTo, setApplyingTo] = useState<string | null>(null);
  const [profile, setProfile] = useState<CandidateProfileData | null>(null);
  const [candidateInvitations, setCandidateInvitations] = useState<Array<{ status: string }>>([]);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeDragging, setResumeDragging] = useState(false);
  const [resumeFileName, setResumeFileName] = useState("");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [fspInput, setFspInput] = useState("");
  const [diplomaStatus, setDiplomaStatus] = useState("");
  const [diplomaUploading, setDiplomaUploading] = useState(false);

  useEffect(() => {
    if (active !== "Мой грейд") return;
    apiGet<TestHistoryData[]>("/testing/history")
      .then(setTestHistory)
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить историю тестов", "error"));
  }, [active]);

  useEffect(() => {
    if (active !== "Тестирование" && active !== "Мой грейд") return;
    Promise.all([
      apiGet<GradeRoadmapData | null>("/testing/roadmap/current"),
      apiGet<AdditionalSkillTestData[]>("/testing/additional"),
    ]).then(([currentRoadmap, extra]) => {
      setRoadmap(currentRoadmap);
      setAdditionalTests(extra);
    }).catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить результаты тестов", "error"));
  }, [active]);

  useEffect(() => {
    if (active !== "Профиль" && active !== "Настройки" && active !== "Мой грейд" && active !== "Тестирование") return;
    setProfileLoading(true);
    apiGet<CandidateProfileData>("/candidate/profile")
      .then((data) => {
        setProfile(data);
        setFspInput(data.fsp_id ?? "");
      })
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить профиль", "error"))
      .finally(() => setProfileLoading(false));
  }, [active]);

  useEffect(() => {
    if (active !== "Обзор") return;
    Promise.all([
      apiGet<CandidateProfileData>("/candidate/profile"),
      apiGet<Array<{ status: string }>>("/invitations/my"),
    ])
      .then(([candidateProfile, invitations]) => {
        setProfile(candidateProfile);
        setCandidateInvitations(invitations);
      })
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить сводку", "error"));
  }, [active]);

  useEffect(() => {
    if (active !== "Вакансии") return;
    setJobsLoading(true);
    Promise.all([
      apiGet<VacancyRecord[]>("/vacancies"),
      apiGet<CandidateVacancyApplication[]>("/vacancies/applications/my"),
    ])
      .then(([available, applications]) => {
        setJobVacancies(available);
        setJobApplications(applications);
      })
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось загрузить вакансии", "error"))
      .finally(() => setJobsLoading(false));
  }, [active]);

  const applyToVacancy = async (vacancy: VacancyRecord) => {
    setApplyingTo(vacancy.id);
    try {
      const application = await apiPost<CandidateVacancyApplication>(`/vacancies/${vacancy.id}/apply`, { cover_letter: "" });
      setJobApplications((current) => [application, ...current.filter((item) => item.id !== application.id)]);
      if (demoMode) {
        onNavigate("Диалоги", `application:${application.id}`);
        onNotify(`Отклик на вакансию «${vacancy.title}» отправлен — диалог с компанией открыт`);
      } else {
        onNotify(`Отклик на вакансию «${vacancy.title}» отправлен`);
      }
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось отправить отклик", "error");
    } finally {
      setApplyingTo(null);
    }
  };

  const saveCandidateProfile = async () => {
    if (!profile) return;
    setProfileSaving(true);
    try {
      const updated = await apiPut<CandidateProfileData>("/candidate/profile", {
        first_name: profile.first_name,
        last_name: profile.last_name,
        phone: profile.phone,
        telegram: profile.telegram,
        bio: profile.bio,
        city: profile.city,
        work_format: profile.work_format,
        specialization: profile.specialization,
        programming_language: profile.programming_language,
        declared_grade: profile.declared_grade,
        salary_expectation: profile.salary_expectation ? Number(profile.salary_expectation) : null,
        salary_tax_type: profile.salary_tax_type ?? "gross",
        skills: profile.skills ?? [],
        fsp_id: profile.fsp_id,
      });
      setProfile(updated);
      onNotify("Изменения профиля сохранены");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось сохранить профиль", "error");
    } finally {
      setProfileSaving(false);
    }
  };

  const saveCandidatePrivacy = async () => {
    if (!profile) return;
    setProfileSaving(true);
    try {
      const updated = await apiPut<CandidateProfileData>("/candidate/profile", {
        agreed_publication: profile.agreed_publication,
        visibility_public: profile.visibility_public,
        mentor_available: profile.mentor_available,
      });
      setProfile(updated);
      onNotify("Настройки видимости сохранены");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось сохранить настройки", "error");
    } finally {
      setProfileSaving(false);
    }
  };

  const uploadResume = async (file?: File) => {
    if (!file) return;
    setResumeFileName(file.name);
    if (!file.name.toLowerCase().endsWith(".pdf") || file.size > 10 * 1024 * 1024) {
      onNotify("Выберите PDF-файл размером не больше 10 МБ.", "error");
      return;
    }
    const body = new FormData();
    body.append("file", file);
    setResumeUploading(true);
    try {
      const parsed = await apiRequest<ParsedResume>("/candidate/resume/upload", { method: "POST", body });
      setParsedResume(parsed);
      onNotify("Резюме распознано. Проверьте найденные поля, затем решите, какие использовать.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось распознать резюме", "error");
    } finally {
      setResumeUploading(false);
    }
  };

  const handleResumeDrop = (event: ReactDragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setResumeDragging(false);
    void uploadResume(event.dataTransfer.files[0]);
  };

  const applyParsedResume = () => {
    if (!parsedResume) return;
    setProfile((current) => current ? {
      ...current,
      first_name: parsedResume.first_name ?? current.first_name,
      last_name: parsedResume.last_name ?? current.last_name,
      phone: parsedResume.phone ?? current.phone,
      telegram: parsedResume.telegram ?? current.telegram,
      city: parsedResume.city ?? current.city,
      specialization: parsedResume.specialization ?? current.specialization,
      declared_grade: parsedResume.suggested_grade?.toLowerCase() ?? current.declared_grade,
      skills: Array.from(new Set([...(current.skills ?? []), ...parsedResume.extracted_skills])),
    } : current);
    onNotify("Данные перенесены в черновик профиля. Проверьте их и нажмите «Сохранить профиль».");
  };

  const downloadProfilePdf = async () => {
    try {
      const pdf = await apiGet<Blob>("/candidate/profile/pdf");
      const url = URL.createObjectURL(pdf);
      const link = document.createElement("a");
      link.href = url;
      link.download = "fsp_candidate_profile.pdf";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось скачать PDF-профиль", "error");
    }
  };

  const linkFspId = async () => {
    if (!fspInput.trim()) return;
    try {
      const updated = await apiPost<CandidateProfileData>("/candidate/link-fsp", { fsp_id: fspInput.trim() });
      setProfile(updated);
      onNotify(updated.fsp_verified ? "Тестовая запись ФСП найдена. Личность не проверена." : "Запись ФСП не найдена в демонстрационных данных.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось проверить ФСП ID", "error");
    }
  };

  const startAdaptiveTest = async () => {
    setTestStarting(true);
    setRadarComparison(null);
    try {
      const session = await apiPost<TestStartData>("/fsp/olympiad/start", {});
      setTestSession(session);
      setQuestion(0);
      setAnswer("");
      setSelectedAnswers([]);
      setSubmittedAnswers([]);
      setTestResult(null);
      setTestStarted(true);
      setTestDone(false);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось начать тестирование", "error");
    } finally {
      setTestStarting(false);
    }
  };

  const beginRoadmap = async (targetGrade?: string) => {
    setTestStarting(true);
    try {
      const next = await apiPost<GradeRoadmapData>("/testing/roadmap", targetGrade ? { target_grade: targetGrade } : {});
      setRoadmap(next);
      setTestDone(false);
      setTestResult(null);
      setRadarComparison(null);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось открыть набор тестов", "error");
    } finally {
      setTestStarting(false);
    }
  };

  const switchToLowerRoadmap = async () => {
    if (!roadmap?.suggested_grade) return;
    setTestStarting(true);
    try {
      if (roadmap.status === "in_progress") {
        await apiPost<GradeRoadmapData>(`/testing/roadmap/${roadmap.id}/stop`, {});
      }
      const next = await apiPost<GradeRoadmapData>("/testing/roadmap", { target_grade: roadmap.suggested_grade });
      setRoadmap(next);
      setTestDone(false);
      setTestResult(null);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось открыть набор уровнем ниже", "error");
      apiGet<GradeRoadmapData | null>("/testing/roadmap/current").then(setRoadmap).catch(() => undefined);
    } finally {
      setTestStarting(false);
    }
  };

  const startRoadmapSkill = async (skillCode: string) => {
    if (!roadmap) return;
    setTestStarting(true);
    try {
      const session = await apiPost<TestStartData>(`/testing/roadmap/${roadmap.id}/skills/${skillCode}/start`, {});
      setTestSession(session);
      setQuestion(0);
      setAnswer("");
      setSelectedAnswers([]);
      setSubmittedAnswers([]);
      setTestResult(null);
      setRadarComparison(null);
      setTestStarted(true);
      setTestDone(false);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось открыть тест навыка", "error");
    } finally {
      setTestStarting(false);
    }
  };

  const startAdditionalSkill = async (skillCode: string, targetGrade: string) => {
    setTestStarting(true);
    try {
      const session = await apiPost<TestStartData>(`/testing/additional/${skillCode}/start`, { target_grade: targetGrade });
      setTestPurpose("grade");
      setTestSession(session);
      setQuestion(0);
      setAnswer("");
      setSelectedAnswers([]);
      setSubmittedAnswers([]);
      setTestResult(null);
      setRadarComparison(null);
      setTestStarted(true);
      setTestDone(false);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось открыть тест навыка", "error");
    } finally {
      setTestStarting(false);
    }
  };

  const submitCurrentAnswer = async () => {
    if (!testSession) return;
    const currentQuestion = testSession.questions[question];
    if (!currentQuestion) return;
    const answerEntry = {
      question_id: currentQuestion.id,
      selected_answers: currentQuestion.question_type === "multiple_choice" ? selectedAnswers : answer ? [answer] : [],
    };
    if (!answerEntry.selected_answers.length) return;
    const answers = [...submittedAnswers, answerEntry];
    if (question + 1 === testSession.total_questions) {
      const previousSkills = roadmap?.skills ?? [];
      setTestSubmitting(true);
      try {
        const submitPath = testPurpose === "fsp-olympiad"
          ? `/fsp/olympiad/${testSession.session_id}/submit`
          : `/testing/${testSession.session_id}/submit`;
        const result = await apiPost<TestResultData>(submitPath, { answers });
        setTestResult(result);
        setTestDone(true);
        setTestStarted(false);
        if (testPurpose === "grade") {
          apiGet<TestHistoryData[]>("/testing/history").then(setTestHistory).catch(() => undefined);
          if (result.assessment_id) {
            try {
              const updatedRoadmap = await apiGet<GradeRoadmapData>(`/testing/roadmap/${result.assessment_id}`);
              setRoadmap(updatedRoadmap);
              const previousByCode = new Map(previousSkills.map((skill) => [skill.code, skill.level_out_of_ten]));
              setRadarComparison({
                labels: updatedRoadmap.skills.map((skill) => skill.label),
                before: updatedRoadmap.skills.map((skill) => previousByCode.get(skill.code) ?? 0),
                after: updatedRoadmap.skills.map((skill) => skill.level_out_of_ten ?? 0),
                hasPriorResults: previousSkills.some((skill) => skill.level_out_of_ten !== null),
                hasUnevaluatedBefore: updatedRoadmap.skills.some((skill) => previousByCode.get(skill.code) === null || previousByCode.get(skill.code) === undefined),
              });
            } catch (error) {
              onNotify(error instanceof Error ? `Тест сохранён, но радар не обновлён: ${error.message}` : "Тест сохранён, но не удалось обновить радар", "error");
            }
          }
          if (!result.assessment_id && result.skill_breakdown.length) {
            setRadarComparison({
              labels: result.skill_breakdown.map((skill) => skill.topic),
              before: result.skill_breakdown.map(() => 0),
              after: result.skill_breakdown.map((skill) => skill.percentage / 10),
              hasPriorResults: false,
              hasUnevaluatedBefore: true,
            });
          }
          if (result.skill_code && !result.assessment_id) apiGet<AdditionalSkillTestData[]>("/testing/additional").then(setAdditionalTests).catch(() => undefined);
          if (result.grade_confirmed) apiGet<CandidateProfileData>("/candidate/profile").then(setProfile).catch(() => undefined);
        } else if (result.skill_breakdown.length) {
          setRadarComparison({
            labels: result.skill_breakdown.map((skill) => skill.topic),
            before: result.skill_breakdown.map(() => 0),
            after: result.skill_breakdown.map((skill) => skill.percentage / 10),
            hasPriorResults: false,
            hasUnevaluatedBefore: true,
          });
        }
      } catch (error) {
        onNotify(error instanceof Error ? error.message : "Не удалось отправить ответы", "error");
      } finally {
        setTestSubmitting(false);
      }
      return;
    }
    setSubmittedAnswers(answers);
    setQuestion((current) => current + 1);
    setAnswer("");
    setSelectedAnswers([]);
  };

  const uploadFspDiploma = async (file?: File) => {
    if (!file) return;
    if (!demoMode) {
      onNotify("Загрузка дипломов в ФСП пока не поддерживается backend.", "error");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      onNotify("Размер файла не должен превышать 10 МБ.", "error");
      return;
    }
    setDiplomaUploading(true);
    const data = new FormData();
    data.append("file", file);
    try {
      const response = await apiRequest<{ status: string; file_name: string }>("/fsp/diplomas/upload", { method: "POST", body: data });
      setDiplomaStatus(response.status === "pending_review" ? `Передано на проверку: ${response.file_name}` : `Файл обработан: ${response.file_name}`);
      onNotify("Демо-диплом передан в локальный процесс ФСП.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось передать диплом", "error");
    } finally {
      setDiplomaUploading(false);
    }
  };

  if (active === "Обзор") {
    const pendingInvitations = candidateInvitations.filter((item) => item.status === "sent" || item.status === "viewed").length;
    return (
      <div className="page-content">
        <div className="candidate-welcome" data-tour="candidate-dashboard">
          <div><span>ЛИЧНЫЙ КАБИНЕТ</span><strong>{profile ? `${profile.first_name} ${profile.last_name}` : "Профиль кандидата"}</strong><p>{profile?.specialization ?? "Специализация не указана"} · заявленный уровень {profile?.declared_grade ?? "не указан"}</p></div>
        </div>
        <div className="metrics-grid">
          <MetricCard label="ПРИГЛАШЕНИЯ" value={String(candidateInvitations.length)} detail={`${pendingInvitations} ждут ответа`} accent icon="mail" />
          <MetricCard label="ЗАЯВЛЕННЫЙ УРОВЕНЬ" value={profile?.declared_grade ?? "—"} detail="Из профиля" icon="layers" />
          <MetricCard label="ПОДТВЕРЖДЁННЫЙ УРОВЕНЬ" value={profile?.verified_grade ?? "—"} detail={profile?.verified_grade ? "Тест пройден" : "Можно пройти тест"} icon="medal" />
          <MetricCard label="ФСП ID" value={profile?.fsp_verified ? "Демо-запись" : "Не привязан"} detail={profile?.fsp_id ?? ""} icon="shield" />
        </div>
        <section className="feature-card candidate-overview-radar">
          <div className="feature-head"><div><span>КАРТА НАВЫКОВ</span><strong>Профиль и ориентир уровня</strong></div><span className="task-radar-card__badge">ДЕМО-ПРИМЕР</span></div>
          {(() => {
            const sample = SPECIALTY_RADAR_SAMPLES.find((item) => item.specialization === profile?.specialization) ?? SPECIALTY_RADAR_SAMPLES[0];
            const target = sample.values.map((value) => Math.min(10, Number((value + 1.2).toFixed(1))));
            const strongestIndex = sample.values.indexOf(Math.max(...sample.values));
            const growthIndex = sample.values.indexOf(Math.min(...sample.values));
            const average = (sample.values.reduce((sum, value) => sum + value, 0) / sample.values.length).toFixed(1);
            return (
              <div className="candidate-overview-radar__body">
                <div className="candidate-overview-radar__chart">
                  <Radar values={sample.values} target={target} axisLabels={sample.labels} description={`Демонстрационное наложение радара профиля по направлению ${sample.specialization}`} />
                </div>
                <div className="candidate-overview-radar__details">
                  <div className="candidate-overview-radar__summary">
                    <span>{sample.specialization} · демонстрационная модель</span>
                    <div className="result-radar__legend">
                      <span><i className="result-radar__legend-before" />Навыки профиля</span>
                      <span><i className="result-radar__legend-after" />Ориентир уровня</span>
                    </div>
                    <div className="candidate-overview-radar__average">
                      <span>Средний показатель примера</span>
                      <strong>{average}<small> / 10</small></strong>
                    </div>
                  </div>
                  <div className="candidate-overview-radar__highlights">
                    <div>
                      <span>Сильная сторона</span>
                      <strong>{sample.labels[strongestIndex]}</strong>
                      <b>{sample.values[strongestIndex].toFixed(1)}<small> / 10</small></b>
                    </div>
                    <div>
                      <span>Точка для роста</span>
                      <strong>{sample.labels[growthIndex]}</strong>
                      <b>{sample.values[growthIndex].toFixed(1)}<small> / 10</small></b>
                    </div>
                  </div>
                  <Button variant="outline" onClick={() => onNavigate("Мой грейд")}>Все радары</Button>
                </div>
              </div>
            );
          })()}
        </section>
        <div className="dashboard-grid dashboard-grid--candidate">
          <section className="feature-card">
            <div className="feature-head"><div><span>ТЕКУЩИЙ СТАТУС</span><strong>{profile?.verified_grade ? "Уровень подтверждён" : "Уровень ожидает подтверждения"}</strong></div></div>
            <p className="feature-description feature-description--left">{profile?.specialization ?? "Специализация не указана"} · заявлено {profile?.declared_grade ?? "—"}{profile?.verified_grade ? ` · подтверждено ${profile.verified_grade}` : ""}</p>
            <Button variant="outline" onClick={() => onNavigate("Тестирование")}>Подтвердить уровень</Button>
          </section>
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ТРЕБУЕТ ВНИМАНИЯ</span><strong>Следующие действия</strong></div></div>
            <div className="action-list">
              <div><div className="action-number">01</div><div><strong>Ответьте на приглашения</strong><span>{pendingInvitations} ожидают вашего решения</span></div><Button onClick={() => onNavigate("Приглашения")}>Открыть</Button></div>
              <div><div className="action-number">02</div><div><strong>Обновите профиль</strong><span>Измените контакты, опыт и условия работы</span></div><Button variant="outline" onClick={() => onNavigate("Профиль")}>Профиль</Button></div>
            </div>
          </section>
          <section className="feature-card feature-card--fsp" data-tour="fsp-tools">
            <div className="feature-head"><div><span>ФСП · ПРАКТИЧЕСКИЙ ТРЕК</span><strong>{profile?.fsp_verified ? "Тестовые данные ФСП добавлены" : "Проверьте навыки на олимпиаде"}</strong></div><div className="fsp-symbol">◆</div></div>
            <p className="feature-description feature-description--left">Олимпиадные задачи дополняют профиль практическими результатами, но грейд не подтверждают — его подтверждает только тест. Сильные стороны по темам помогут дополнить подтверждённый профиль.</p>
            <div className="fsp-actions"><Button onClick={() => { setTestPurpose("fsp-olympiad"); onNavigate("Тестирование"); }}>Написать олимпиаду</Button><label className="button button--outline diploma-upload"><Icon name="briefcase" />{diplomaUploading ? "Передаём…" : "Догрузить диплом"}<input type="file" accept="application/pdf,image/png,image/jpeg" disabled={diplomaUploading} onChange={(event) => void uploadFspDiploma(event.target.files?.[0])} /></label><Button variant="ghost" onClick={() => onNavigate("Настройки")}>Связать ФСП ID</Button></div>
            {diplomaStatus && <div className="fsp-upload-status" role="status">{diplomaStatus}</div>}
          </section>
        </div>
      </div>
    );
  }

  if (active === "Профиль") {
    return (
      <div className="page-content">
        {profileLoading && <div className="empty-state">Загружаем профиль…</div>}
        <div className="settings-layout settings-layout--profile">
          <section className="feature-card">
            <div className="profile-edit-head"><div className="avatar avatar--xl">{`${profile?.first_name?.[0] ?? "?"}${profile?.last_name?.[0] ?? ""}`}</div><div><strong>{profile ? `${profile.first_name} ${profile.last_name}` : "Профиль кандидата"}</strong><span>{profile?.specialization ?? "Специализация не указана"} · {profile?.city ?? "Город не указан"}</span></div></div>
            <div className="field-row field-row--flush"><label className="field"><span>ИМЯ</span><input value={profile?.first_name ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, first_name: event.target.value } : current)} /></label><label className="field"><span>ФАМИЛИЯ</span><input value={profile?.last_name ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, last_name: event.target.value } : current)} /></label></div>
            <div className="field-row field-row--flush">
              <label className="field"><span>ТЕЛЕФОН</span><input type="tel" autoComplete="tel" value={profile?.phone ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, phone: event.target.value } : current)} /></label>
              <label className="field"><span>TELEGRAM</span><input value={profile?.telegram ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, telegram: event.target.value } : current)} placeholder="@username" /></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field">
                <span>СПЕЦИАЛИЗАЦИЯ</span>
                <select value={profile?.specialization ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, specialization: event.target.value || null } : current)}>
                  <option value="">Выберите специализацию</option>
                  {ALL_SPECIALIZATIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="field">
                <span>ЗАЯВЛЕННЫЙ УРОВЕНЬ</span>
                <select value={profile?.declared_grade ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, declared_grade: event.target.value || null } : current)}>
                  <option value="">Не указан</option>
                  {ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            </div>
            <label className="field field--flush"><span>О СЕБЕ</span><textarea value={profile?.bio ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, bio: event.target.value } : current)} /></label>
            <div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={profile?.city ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, city: event.target.value } : current)} /></label><label className="field"><span>ФОРМАТ РАБОТЫ</span><select value={profile?.work_format ?? "remote"} onChange={(event) => setProfile((current) => current ? { ...current, work_format: event.target.value } : current)}><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select></label></div>
            <div className="field-row field-row--flush">
              <label className="field">
                <span>ЖЕЛАЕМАЯ ЗАРПЛАТА, ₽</span>
                <input
                  inputMode="numeric"
                  placeholder="Например, 200000"
                  value={profile?.salary_expectation ?? ""}
                  onChange={(event) => {
                    const val = event.target.value.replace(/\D/g, "");
                    setProfile((current) => current ? { ...current, salary_expectation: val ? Number(val) : null } : current);
                  }}
                />
              </label>
              <label className="field">
                <span>ТИП ЗАРПЛАТЫ</span>
                <select
                  aria-label="Тип зарплаты кандидата"
                  value={profile?.salary_tax_type ?? "gross"}
                  onChange={(event) => setProfile((current) => current ? { ...current, salary_tax_type: event.target.value as "gross" | "net" } : current)}
                >
                  <option value="gross">До вычета НДФЛ</option>
                  <option value="net">На руки</option>
                </select>
              </label>
            </div>
            <label className="field field--flush">
              <span>НАВЫКИ · ЧЕРЕЗ ЗАПЯТУЮ</span>
              <input
                value={(profile?.skills ?? []).join(", ")}
                onChange={(event) => setProfile((current) => current ? {
                  ...current,
                  skills: Array.from(new Set(event.target.value.split(",").map((skill) => skill.trim()).filter(Boolean))),
                } : current)}
                placeholder="Python, PostgreSQL, Docker"
              />
            </label>
            <Button disabled={!profile || profileSaving} className={profileSaving ? "button--disabled" : ""} onClick={() => void saveCandidateProfile()}>{profileSaving ? "Сохраняем…" : "Сохранить профиль"}</Button>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>РЕЗЮМЕ</span><strong>Опыт и документы</strong></div></div>
            <div
              className={`upload-box upload-box--resume${resumeDragging ? " is-dragging" : ""}${resumeUploading ? " is-uploading" : ""}`}
              onDragOver={(event) => { event.preventDefault(); setResumeDragging(true); }}
              onDragLeave={() => setResumeDragging(false)}
              onDrop={handleResumeDrop}
            >
              <div className="upload-box__icon"><Icon name="briefcase" size={24} /></div>
              <strong>{resumeUploading ? "Распознаём резюме…" : resumeFileName || "Загрузите PDF-резюме"}</strong>
              <span>{resumeUploading ? "Извлекаем навыки и данные профиля" : "Перетащите файл сюда или выберите его на устройстве. До 10 МБ."}</span>
              <label className="button button--outline upload-box__browse" htmlFor="candidate-resume-upload">
                <Icon name="upload" size={16} />{resumeUploading ? "Обрабатываем…" : "Выбрать PDF"}
              </label>
              <input
                id="candidate-resume-upload"
                className="resume-file-input"
                type="file"
                accept="application/pdf,.pdf"
                disabled={resumeUploading}
                aria-label="Загрузить PDF-резюме"
                onChange={(event) => { void uploadResume(event.target.files?.[0]); event.currentTarget.value = ""; }}
              />
              <small>Данные сначала откроются в черновике — в профиль попадут только после вашего подтверждения.</small>
            </div>
            {parsedResume && <div className="resume-entry" role="status" aria-live="polite">
              <span>ПРЕДПРОСМОТР · ДАННЫЕ ЕЩЁ НЕ СОХРАНЕНЫ</span>
              <div className="resume-review-grid">
                {[
                  ["Имя", [parsedResume.first_name, parsedResume.last_name].filter(Boolean).join(" ")],
                  ["Email из файла · аккаунт не изменяется", parsedResume.email],
                  ["Телефон", parsedResume.phone],
                  ["Telegram", parsedResume.telegram],
                  ["Город", parsedResume.city],
                  ["Специализация", parsedResume.specialization],
                  ["Предложенный уровень", parsedResume.suggested_grade],
                ].map(([label, value]) => <div key={label}><small>{label}</small><strong>{value || "Не распознано"}</strong></div>)}
              </div>
              <strong>{parsedResume.extracted_skills.length ? parsedResume.extracted_skills.join(" · ") : "Навыки не распознаны"}</strong>
              <p>{parsedResume.text_preview.slice(0, 320) || "Текстовое превью недоступно."}</p>
              <Button variant="outline" onClick={applyParsedResume}>Перенести данные в профиль</Button>
            </div>}
            <p className="feature-description feature-description--left">PDF доступен после согласия на публикацию профиля. Контакты в PDF не входят.</p>
            <Button variant="outline" disabled={!profile?.agreed_publication} onClick={() => void downloadProfilePdf()}>Скачать PDF-профиль</Button>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Тестирование") {
    if (testDone) {
      return (
        <div className="page-content">
          <div className="test-result">
            <div className="result-check"><Icon name={testResult?.passed === null ? "chart" : testResult?.passed ? "check" : "close"} size={34} /></div>
            <span>{testPurpose === "fsp-olympiad" ? "ОЛИМПИАДА ФСП · РЕЗУЛЬТАТ" : "РЕЗУЛЬТАТ ТЕСТА"}</span>
            <strong>{testPurpose === "fsp-olympiad" ? "Проверка навыков завершена" : testResult?.grade_confirmed ? `Подтверждён ${testResult.target_grade}` : "Результат навыка сохранён"}</strong>
            <p>{testResult?.feedback}</p>
            <div className="result-score">
              <b>{testResult?.correct_count !== undefined ? `${testResult.correct_count} из ${testResult.total_questions} заданий` : `${testResult?.percentage ?? 0}%`}</b>
              <span>{testPurpose === "grade" ? `${testResult?.percentage ?? 0}% правильных ответов` : `${testResult?.score ?? 0} из ${testResult?.max_score ?? 0} баллов`}</span>
              {testPurpose === "grade" && testResult?.assessment_id && <span>Для грейда нужны все обязательные навыки: от 75% суммарно и от 50% по каждому.</span>}
              {testPurpose === "grade" && testResult?.skill_code && !testResult.assessment_id && <span>Это дополнительный навык; его баллы не входят в расчёт грейда.</span>}
            </div>
            {radarComparison && <section className="result-radar" aria-label="Изменение карты навыков после теста">
              <div className="result-radar__copy">
                <span>ОБНОВЛЕНИЕ КАРТЫ</span>
                <h2>Радар после теста</h2>
                <p>{!radarComparison.hasPriorResults ? "Показан фактический результат теста; ранее навыки не оценивались." : radarComparison.hasUnevaluatedBefore ? "Сравнение с прежними результатами. Не пройденные ранее навыки показаны от нуля." : "Сравнение результатов до и после этого этапа."}</p>
                <div className="result-radar__legend"><span><i className="result-radar__legend-before" />{radarComparison.hasPriorResults ? "До теста" : "До оценки"}</span><span><i className="result-radar__legend-after" />После теста</span></div>
              </div>
              <div className="result-radar__chart">
                <Radar key={testResult?.session_id} values={radarComparison.after} target={radarComparison.before} axisLabels={radarComparison.labels} showAxisLabels={false} className="radar--animate" description="Сравнение карты навыков до и после теста" />
              </div>
            </section>}
            {testResult?.question_review?.length ? (
              <>
                <div className="topic-summary">
                  <h3>Ответы по темам</h3>
                  {testResult.skill_breakdown.map((skill) => <div key={skill.topic}><span>{skill.topic}</span><strong>{skill.correct_count} из {skill.total_questions}</strong></div>)}
                </div>
                <div className="question-review">
                  <h3>Разбор заданий</h3>
                  {testResult.question_review.map((item, index) => <div className="question-review__item" key={item.code}>
                    <strong>{index + 1}. {item.topic} — {item.is_correct ? "верно" : "ошибка"}</strong>
                    <p>{item.question_text}</p>
                    <p>Ваш ответ: {item.selected_answers.join("; ") || "нет ответа"}</p>
                    {!item.is_correct && <p>Правильный ответ: {item.correct_answers.join("; ")}</p>}
                    <p>{item.explanation}</p>
                  </div>)}
                </div>
              </>
            ) : <div className="skill-table">{testResult?.skill_breakdown.map((skill) => <div key={skill.topic}><span>{skill.topic}</span><Progress value={skill.percentage} /><strong>{skill.percentage}%</strong></div>)}</div>}
            {testPurpose === "fsp-olympiad" && <p>Результаты тем сохранены в локальном demo-профиле.</p>}
            {testPurpose === "grade" && testResult?.suggested_grade && <p>Можно пройти полный набор на уровень {testResult.suggested_grade}.</p>}
            <Button onClick={() => { setTestDone(false); setTestResult(null); }}>К тестированию</Button>
          </div>
        </div>
      );
    }
    if (testStarted) {
      const currentQuestion = testSession?.questions[question];
      if (!currentQuestion) return <div className="page-content"><div className="empty-state">Загружаем задание…</div></div>;
      return (
        <div className="test-shell">
          <div className="test-top">
            <div>
              <span>{testPurpose === "fsp-olympiad" ? "ОЛИМПИАДА ФСП" : `${testSession?.assessment_id ? "ОБЯЗАТЕЛЬНЫЙ" : "ДОПОЛНИТЕЛЬНЫЙ"} НАВЫК: ${roadmap?.skills.find((item) => item.code === testSession?.skill_code)?.label ?? additionalTests.find((item) => item.code === testSession?.skill_code)?.label ?? testSession?.skill_code} · ${testSession?.specialization} · ${testSession?.target_grade}`}</span>
              <strong>Внимательно прочитайте задание</strong>
            </div>
            <div className="test-step" aria-label={`Задание ${question + 1} из ${testSession?.total_questions}`}>
              <strong>{String(question + 1).padStart(2, "0")}</strong>
              <span>из {testSession?.total_questions}</span>
            </div>
          </div>
          <Progress value={((question + 1) / (testSession?.total_questions ?? 1)) * 100} />
          <div className="test-content test-content--focused">
            <div className="question-card"><span>{currentQuestion.topic}</span><strong>{currentQuestion.question_text}</strong><div className="answers">{currentQuestion.options.map((option) => {
              const selected = currentQuestion.question_type === "multiple_choice" ? selectedAnswers.includes(option.id) : answer === option.id;
              return <button type="button" key={option.id} className={selected ? "selected" : ""} onClick={() => {
                if (currentQuestion.question_type === "multiple_choice") {
                  setSelectedAnswers((current) => current.includes(option.id) ? current.filter((id) => id !== option.id) : [...current, option.id]);
                } else {
                  setAnswer(option.id);
                }
              }}><i />{option.text}</button>;
            })}</div></div>
          </div>
          <div className="test-footer"><span>Ответы проверяются после завершения теста</span><Button disabled={testSubmitting || !(answer || selectedAnswers.length)} onClick={() => void submitCurrentAnswer()}>{testSubmitting ? "Проверяем…" : question + 1 === testSession?.total_questions ? "Завершить тест" : "Ответить и продолжить"} <Icon name="chevron" /></Button></div>
        </div>
      );
    }
    const lowerAfterRetake = roadmap?.target_grade === "senior" ? "middle" : roadmap?.target_grade === "middle" ? "junior" : null;
    const juniorRetryAt = roadmap?.retry_available_at ?? (roadmap?.retake_used && roadmap.expires_at ? new Date(Date.parse(roadmap.expires_at) + 7 * 24 * 60 * 60 * 1000).toISOString() : null);
    const juniorRetryLocked = juniorRetryAt !== null && Date.parse(juniorRetryAt) > Date.now();
    return (
      <div className="page-content">
        <div className="assessment-mode" role="group" aria-label="Режим проверки"><button type="button" className={testPurpose === "grade" ? "active" : ""} onClick={() => setTestPurpose("grade")}>Грейд</button><button type="button" className={testPurpose === "fsp-olympiad" ? "active" : ""} onClick={() => setTestPurpose("fsp-olympiad")}>Олимпиада ФСП</button></div>
        {testPurpose === "grade" ? <>
          <section className="assessment-roadmap">
            <div className="assessment-roadmap__head">
              <div className="assessment-roadmap__title">
                <div className="assessment-roadmap__icon"><Icon name="chart" size={22} /></div>
                <div><span>ПУТЬ К ГРЕЙДУ</span><h2>{roadmap ? `${roadmap.specialization} · ${roadmap.target_grade}` : "Подтверждение навыков"}</h2></div>
              </div>
              {roadmap && <div className={`assessment-roadmap__status assessment-roadmap__status--${roadmap.status}`}>
                <i />{roadmap.status === "completed" ? roadmap.passed ? "Грейд подтверждён" : "Набор завершён" : roadmap.status === "expired" ? "Срок истёк" : roadmap.status === "cancelled" ? "Набор прерван" : "Набор открыт"}
              </div>}
            </div>
            {roadmap ? <>
              <div className="assessment-roadmap__meta">
                <span><Icon name="school" size={15} /> {roadmap.skills.length} обязательных компетенции</span>
                <span><Icon name="clock" size={15} /> Доступен 3 дня</span>
                {roadmap.expires_at && roadmap.status === "in_progress" && <span className="assessment-roadmap__deadline">До {new Date(roadmap.expires_at).toLocaleDateString("ru-RU")}</span>}
              </div>
              <div className="skill-roadmap" aria-label="Этапы подтверждения грейда">
                {roadmap.skills.map((skill, index) => {
                  const complete = skill.status === "completed";
                  const inProgress = skill.status === "in_progress";
                  const canStart = roadmap.status === "in_progress" && !complete;
                  const statusLabel = complete ? `${skill.level_out_of_ten ?? 0} / 10` : inProgress ? "В процессе" : "Ожидает";
                  return (
                    <article className={`skill-roadmap__step${complete ? " is-complete" : ""}${inProgress ? " is-current" : ""}`} key={skill.code}>
                      <div className="skill-roadmap__marker">{complete ? <Icon name="check" size={17} /> : <span>{String(index + 1).padStart(2, "0")}</span>}</div>
                      <div className="skill-roadmap__body">
                        <div className="skill-roadmap__copy"><span>ЭТАП {String(index + 1).padStart(2, "0")}</span><strong>{skill.label}</strong></div>
                        <div className="skill-roadmap__actions">
                          <span className={`skill-roadmap__result${complete ? " is-complete" : ""}`}>{statusLabel}</span>
                          {canStart && <Button variant={inProgress ? "primary" : "outline"} disabled={testStarting} onClick={() => void startRoadmapSkill(skill.code)}>{testStarting ? "Открываем…" : inProgress ? "Продолжить" : "Начать"}</Button>}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
              {roadmap.status === "in_progress" && <div className="assessment-roadmap__progress">
                <div><span>Прогресс набора</span><strong>{roadmap.skills.filter((skill) => skill.status === "completed").length} из {roadmap.skills.length}</strong></div>
                <Progress value={(roadmap.skills.filter((skill) => skill.status === "completed").length / Math.max(roadmap.skills.length, 1)) * 100} />
              </div>}
              <details className="assessment-info">
                <summary>Как рассчитывается грейд</summary>
                <p>Нужно набрать от 75% в сумме и не менее 50% по каждой компетенции. Пороги предварительные. {TEST_AVAILABILITY_HINT}</p>
                {!roadmap.retake_used && roadmap.status === "in_progress" && <p>После прохождения всех этапов доступна одна пересдача всего набора.</p>}
              </details>
            </> : <div className="assessment-roadmap__empty">
              <div><strong>Четыре компетенции — один подтверждённый уровень</strong><span>Проходите навыки в удобном темпе в течение трёх дней.</span></div>
              <Button disabled={testStarting} onClick={() => void beginRoadmap()}>{testStarting ? "Открываем…" : "Открыть маршрут"}</Button>
            </div>}
            {roadmap && <>
              {roadmap.status === "expired" && <div className="notice-box">Срок набора истёк. Результаты остались в истории, грейд по нему не присваивается.</div>}
              {roadmap.status === "cancelled" && <div className="notice-box">Набор прерван. Пройденные шаги остались в истории.</div>}
              {roadmap.status === "in_progress" && roadmap.suggested_grade && <div className="test-choice-actions"><Button variant="outline" disabled={testStarting} onClick={() => void switchToLowerRoadmap()}>Прервать набор и попробовать {roadmap.suggested_grade}</Button></div>}
              {(roadmap.status === "expired" || roadmap.status === "cancelled") && (roadmap.retake_used ? lowerAfterRetake ? <Button disabled={testStarting} onClick={() => void beginRoadmap(lowerAfterRetake)}>Попробовать {lowerAfterRetake}</Button> : <Button disabled={testStarting || juniorRetryLocked} onClick={() => void beginRoadmap("junior")}>Новый набор Junior</Button> : <Button disabled={testStarting} onClick={() => void beginRoadmap(roadmap.target_grade)}>Открыть новый набор</Button>)}
              {roadmap.status === "completed" && <div className="notice-box">Общий результат: {roadmap.percentage}%. {roadmap.passed ? `Грейд ${roadmap.target_grade} подтверждён.` : "Грейд не подтверждён; прежний уровень не меняется."}</div>}
              {roadmap.status === "completed" && <div className="test-choice-actions">{!roadmap.retake_used && <Button variant="outline" disabled={testStarting} onClick={() => void beginRoadmap(roadmap.target_grade)}>Пересдать весь набор</Button>}{roadmap.retake_used && !roadmap.passed && roadmap.target_grade === "junior" && <><Button variant="outline" disabled={testStarting || juniorRetryLocked} onClick={() => void beginRoadmap("junior")}>Новый набор Junior</Button>{juniorRetryLocked && juniorRetryAt && <span>Повторить Junior можно с {new Date(juniorRetryAt).toLocaleDateString("ru-RU")}</span>}</>}{roadmap.suggested_grade && <Button disabled={testStarting} onClick={() => void beginRoadmap(roadmap.suggested_grade ?? undefined)}>Попробовать {roadmap.suggested_grade}</Button>}{roadmap.passed && roadmap.target_grade !== "senior" && <><Button disabled={testStarting || (roadmap.promotion_available_at !== null && Date.parse(roadmap.promotion_available_at) > Date.now())} onClick={() => void beginRoadmap(roadmap.target_grade === "junior" ? "middle" : "senior")}>Хочу поднять грейд</Button>{roadmap.promotion_available_at && Date.parse(roadmap.promotion_available_at) > Date.now() && <span>Повышение доступно с {new Date(roadmap.promotion_available_at).toLocaleDateString("ru-RU")}</span>}</>}</div>}
            </>}
          </section>
          <section className="additional-competencies">
            <div className="additional-competencies__head">
              <div className="additional-competencies__icon"><Icon name="sparkle" size={20} /></div>
              <div><span>ДОПОЛНИТЕЛЬНЫЙ ТРЕК</span><h2>Расширяйте компетенции</h2></div>
              <span className="additional-competencies__badge">В профиль · без влияния на грейд</span>
            </div>
            {additionalTests.length ? <div className="additional-competencies__grid">{additionalTests.map((skill) => (
              <article className="additional-skill-card" key={`${skill.code}-${skill.target_grade}`}>
                <div className="additional-skill-card__mark"><Icon name="sparkle" size={17} /></div>
                <div className="additional-skill-card__info"><strong>{skill.label}</strong><span>{skill.target_grade} · {skill.level_out_of_ten !== null ? `Результат ${skill.level_out_of_ten} / 10` : "Пока не проверена"}</span></div>
                {skill.latest_session_id && skill.latest_percentage !== null ? <span className="additional-skill-card__score">{skill.latest_percentage}%</span> : null}
                <Button variant="outline" disabled={testStarting} onClick={() => void startAdditionalSkill(skill.code, skill.target_grade)}>{testStarting ? "…" : skill.latest_session_id ? "Повторить" : "Начать"}</Button>
              </article>
            ))}</div> : <div className="additional-competencies__empty"><Icon name="sparkle" size={19} /><span>Новые тесты появятся здесь, когда по дополнительным навыкам будут готовы задания.</span></div>}
          </section>
        </> : <div className="test-intro"><div className="test-intro__graphic"><span>&lt;/&gt;</span><i /><b /></div><span>ОЛИМПИАДА ФСП</span><strong>Практические задачи по навыкам</strong><p>Результат олимпиады дополняет профиль, но не присваивает грейд.</p><div className="test-choice-actions"><Button disabled={testStarting} onClick={() => void startAdaptiveTest()}>{testStarting ? "Подготавливаем…" : "Начать олимпиаду"}</Button></div></div>}
      </div>
    );
  }

  if (active === "Мой грейд") {
    const gradeSkills = roadmap?.skills ?? [];
    const gradeSkillValues = gradeSkills.map((skill) => skill.level_out_of_ten ?? 0);
    const careerPaths = getCareerPathSuggestions(
      profile?.specialization,
      [...(profile?.skills ?? []), ...gradeSkills.map((skill) => skill.label)],
    );
    return (
      <div className="page-content">
        <section className="grade-hero">
          <div className="grade-hero__copy">
            <span className="grade-hero__eyebrow">КАТЕГОРИЯ И УРОВЕНЬ</span>
            <div className="grade-hero__facts">
              <div><span>СПЕЦИАЛИЗАЦИЯ</span><strong>{profile?.specialization ?? "Не указана"}</strong></div>
              <div><span>ПОДТВЕРЖДЁННЫЙ ГРЕЙД</span><strong>{profile?.verified_grade ?? "Пока не подтверждён"}</strong></div>
            </div>
            <p>{profile?.verified_grade ? "Уровень подтверждён по результатам тестирования." : `Заявленный уровень: ${profile?.declared_grade ?? "не указан"}. Подтвердите навыки тестированием.`}</p>
          </div>
          <div className="grade-stamp"><Icon name={profile?.verified_grade ? "check" : "chart"} /><span>{profile?.verified_grade ? "ГРЕЙД ПОДТВЕРЖДЁН" : "НУЖНО ПРОЙТИ ТЕСТ"}</span>{profile?.fsp_verified && <strong>ФСП ID привязан</strong>}</div>
        </section>
        <div className="grade-overview-grid">
          <section className="feature-card grade-radar-card">
            <div className="feature-head"><div><span>КАРТА КОМПЕТЕНЦИЙ</span><strong>Результаты по навыкам</strong></div></div>
            {gradeSkills.length > 0 ? <>
              <div className="grade-radar">
                <Radar values={gradeSkillValues} target={gradeSkillValues.map(() => 10)} axisLabels={gradeSkills.map((skill) => skill.label)} showAxisLabels={false} description="Карта результатов по обязательным навыкам от нуля до десяти" />
              </div>
              <div className="grade-skill-legend" aria-label="Результаты по навыкам">
                {gradeSkills.map((skill) => (
                  <div key={skill.code}>
                    <span><i />{skill.label}</span>
                    <strong>{skill.level_out_of_ten ?? 0}<small> / 10</small></strong>
                  </div>
                ))}
              </div>
            </> : <div className="grade-radar-empty"><div className="grade-radar-empty__mark"><Icon name="chart" size={28} /></div><strong>Карта появится после начала тестирования</strong><p>Откройте набор, чтобы увидеть результаты по каждому навыку.</p><Button onClick={() => onNavigate("Тестирование")}>Открыть тестирование</Button></div>}
          </section>
          <section className="feature-card grade-profile-card">
            <div className="feature-head"><div><span>ВАШ ПРОФИЛЬ</span><strong>Категория и уровень</strong></div></div>
            <div className="grade-profile-detail"><span>Специализация</span><strong>{profile?.specialization ?? "Не указана"}</strong></div>
            <div className="grade-profile-detail"><span>Язык базового теста</span><strong>{profile?.programming_language ?? "Не выбран"}</strong></div>
            <div className="grade-profile-detail"><span>Заявленный уровень</span><strong>{profile?.declared_grade ?? "Не указан"}</strong></div>
            <div className="grade-profile-detail"><span>Подтверждённый уровень</span><strong>{profile?.verified_grade ?? "Нет"}</strong></div>
            <Button variant="outline" onClick={() => onNavigate("Тестирование")}>Перейти к тестам</Button>
          </section>
        </div>
        <SpecialtyRadarGallery currentSpecialization={profile?.specialization} currentSkills={gradeSkills} />
        <section className="career-paths">
          <div className="career-paths__head">
            <div><span>РАЗВИТИЕ КАРЬЕРЫ</span><h2>Смежные направления для исследования</h2></div>
            <p>Это идеи для изучения на основе текущей специализации и навыков, а не оценка готовности или обещание новой роли.</p>
          </div>
          {!profile?.skills?.length && !gradeSkills.length && <div className="career-paths__note"><Icon name="sparkle" size={16} />Добавьте навыки в профиль или пройдите тест — тогда подсказки смогут учитывать больше ваших данных.</div>}
          <div className="career-paths__grid">
            {careerPaths.map((path) => (
              <article className="career-path-card" key={path.specialization}>
                <div className="career-path-card__top"><span><Icon name="arrowUpRight" size={16} /> МОЖНО ИССЛЕДОВАТЬ</span><strong>{path.specialization}</strong></div>
                <p>{path.description}</p>
                <div className="career-path-card__evidence">
                  <span>{path.matchedSignals.length ? "Пересекается с вашими навыками" : "Что можно попробовать изучить"}</span>
                  <div>{(path.matchedSignals.length ? path.matchedSignals : path.signals.slice(0, 3)).map((signal) => <i key={signal}>{signal}</i>)}</div>
                </div>
                <Button variant="outline" onClick={() => { onNavigate("Профиль"); onNotify(`Чтобы рассмотреть «${path.specialization}», выберите специализацию в профиле и сохраните изменения. Текущий грейд не меняется автоматически.`); }}>Рассмотреть направление</Button>
              </article>
            ))}
          </div>
          <div className="career-paths__foot"><Icon name="info" size={16} /><span>Тестирование грейда пока доступно только для Backend. Для других специализаций здесь показаны направления для самостоятельного исследования, а не результаты теста.</span></div>
        </section>
        <section className="feature-card grade-history-card">
          <div className="feature-head"><div><span>ИСТОРИЯ ТЕСТОВ</span><strong>Результаты проверок</strong></div><Button onClick={() => onNavigate("Тестирование")}>Пройти тест</Button></div>
          {testHistory.length ? <div className="history-table history-table--tests">{testHistory.map((item) => <div key={item.id}><span>{new Date(item.created_at).toLocaleDateString("ru-RU")}</span><strong>{item.skill_code ? `${roadmap?.skills.find((skill) => skill.code === item.skill_code)?.label ?? additionalTests.find((skill) => skill.code === item.skill_code)?.label ?? item.skill_code} · ${item.target_grade}` : `${item.specialization} · ${item.target_grade}`}</strong><b>{item.status === "completed" ? item.assessment_id ? "Обязательный навык" : item.skill_code ? "Дополнительный навык" : "Общий тест прежнего формата" : item.status === "expired" ? "Срок истёк" : item.status === "cancelled" ? "Прерван" : "В процессе"}</b><em>{item.status === "completed" ? `${item.percentage}%` : "—"}</em></div>)}</div> : <div className="empty-state">Истории тестирования пока нет</div>}
        </section>
        {roadmap && <section className="feature-card"><div className="feature-head"><div><span>ПОСЛЕДНИЙ БАЗОВЫЙ НАБОР</span><strong>{roadmap.specialization} · {roadmap.target_grade}</strong></div></div><div className="topic-summary">{roadmap.skills.map((skill) => <div key={skill.code}><span>{skill.label}</span><strong>{skill.status === "completed" ? `${skill.level_out_of_ten} из 10 на уровне ${roadmap.target_grade}` : "Не пройден"}</strong></div>)}</div>{roadmap.status === "completed" && <p className="feature-description feature-description--left">Итого {roadmap.percentage}% · {roadmap.passed ? "грейд подтверждён" : "грейд не подтверждён"}</p>}</section>}
        {additionalTests.some((skill) => skill.latest_session_id) && <section className="feature-card"><div className="feature-head"><div><span>ДОПОЛНИТЕЛЬНЫЕ НАВЫКИ</span><strong>Отдельные результаты</strong></div></div><div className="topic-summary">{additionalTests.filter((skill) => skill.latest_session_id).map((skill) => <div key={`${skill.code}-${skill.target_grade}`}><span>{skill.label}</span><strong>{skill.level_out_of_ten} из 10 на уровне {skill.target_grade}</strong></div>)}</div></section>}
      </div>
    );
  }

  if (active === "Задания") {
    return (
      <div className="page-content">
        <div className="task-hero"><div><span>АКТУАЛЬНОСТЬ ПРОФИЛЯ</span><strong>Профиль активен</strong><p>Последняя активность 2 дня назад. Баллы радара не затухают.</p></div><div className="recency-scale"><span className="active">Активен</span><span>Недавно активен</span><span>Устаревает</span><span>Неактивен</span></div></div>
        <div className="task-demo-note"><Icon name="sparkle" size={18} /><span>Примеры заданий и обновления радара ниже — демонстрация интерфейса, не реальные результаты.</span></div>
        <div className="task-list">
          <article className="task-card"><div className="task-card__type">&lt;/&gt;</div><div><span>ПЛАТФОРМЕННАЯ · 10–15 МИН</span><strong>Оптимизация SQL-запроса</strong><p>Найдите причину медленного выполнения запроса и предложите индексы.</p><div className="tags"><span>Базы данных</span><span>Пример обновления +0,4</span></div></div><div className="task-card__action"><span>до 24 мая</span><Button onClick={() => { setTaskDone(true); onNotify("Демо-задание открыто. Его результат не изменяет реальные данные."); }}>{taskDone ? "В работе" : "Начать"}</Button></div></article>
          <article className="task-card"><div className="task-card__type task-card__type--red"><Icon name="briefcase" /></div><div><span>ОТ NOVATECH · 10 МИН</span><strong>Code review обработчика API</strong><p>Найдите проблемы безопасности и производительности в сниппете.</p><div className="tags"><span>API</span><span>Code Quality</span></div></div><div className="task-card__action"><span>до 27 мая</span><Button variant="outline">Открыть</Button></div></article>
        </div>
        <section className="feature-card task-radar-card">
          <div className="feature-head"><div><span>ИНТЕРАКТИВНЫЙ ПРИМЕР</span><strong>Как задание может изменить карту</strong></div><span className="task-radar-card__badge">ДЕМО-ПРОФИЛЬ</span></div>
          <div className="task-radar-card__body">
            <div className="task-radar-card__chart"><Radar key={taskDemoShown ? "task-after" : "task-before"} values={demoTaskRadar} target={taskDemoShown ? [6.2, 7.1, 6.8, 7.4] : demoTaskRadar} axisLabels={["Язык и runtime", "API", "Базы данных", "Надёжность"]} showAxisLabels={false} className={taskDemoShown ? "radar--animate" : ""} description="Демонстрационная карта компетенций до и после задания" /></div>
            <div className="task-radar-card__copy"><p>После завершения задания приложение сможет показать измеренную динамику по связанному навыку. Здесь — только пример анимации.</p><div className="result-radar__legend"><span><i className="result-radar__legend-before" />До задания</span><span><i className="result-radar__legend-after" />После · пример</span></div><Button variant="outline" disabled={taskDemoShown} onClick={() => { setDemoTaskRadar((values) => values.map((value, index) => index === 2 ? Math.min(10, Number((value + 0.4).toFixed(1))) : value)); setTaskDemoShown(true); }}>{taskDemoShown ? "Демо обновление показано" : "Показать пример обновления"}</Button></div>
          </div>
        </section>
        <section className="feature-card"><div className="feature-head"><div><span>ИСТОРИЯ</span><strong>Решённые задания</strong></div></div><div className="history-table"><div><span>12 мая</span><strong>Debug-кейс: очередь сообщений</strong><b>+0.3 API</b><em>9/10</em></div><div><span>28 апреля</span><strong>Архитектурное эссе</strong><b>+0.4 Architecture</b><em>8/10</em></div></div></section>
      </div>
    );
  }

  if (active === "Приглашения") return <Invitations onNotify={onNotify} onNavigate={onNavigate} />;

  if (active === "Вакансии") {
    const normalizedJobSearch = jobSearch.trim().toLowerCase();
    const visibleVacancies = jobVacancies.filter((vacancy) =>
      !normalizedJobSearch || `${vacancy.title} ${vacancy.company?.company_name ?? ""} ${vacancy.required_skills.join(" ")}`.toLowerCase().includes(normalizedJobSearch),
    );
    const visibleApplications = jobApplications.filter((application) =>
      !normalizedJobSearch || `${application.vacancy_title} ${application.company_name}`.toLowerCase().includes(normalizedJobSearch),
    );
    const applicationStatusLabel = (status: string) => ({
      pending: "Ожидает ответа",
      reviewed: "Рассматривается",
      accepted: "Отклик принят",
      rejected: "Отказ",
    }[status] ?? status);
    return (
      <div className="page-content">
        <div className="vacancy-head"><div><strong>Вакансии</strong><span>Предложения работодателей и ваши отклики</span></div></div>
        <div className="vacancy-tabs" role="tablist" aria-label="Раздел вакансий">
          <button type="button" className={jobsTab === "vacancies" ? "active" : ""} onClick={() => setJobsTab("vacancies")}>Все вакансии · {jobVacancies.length}</button>
          <button type="button" className={jobsTab === "applications" ? "active" : ""} onClick={() => setJobsTab("applications")}>Мои отклики · {jobApplications.length}</button>
        </div>
        <div className="bank-toolbar"><div className="search-field search-field--wide"><Icon name="search" /><input value={jobSearch} onChange={(event) => setJobSearch(event.target.value)} placeholder="Название, компания или технология" aria-label="Поиск вакансий" /></div></div>
        {jobsLoading ? <div className="empty-state">Загружаем вакансии…</div> : null}
        {jobApplications.length > 0 && jobsTab === "applications" && <div className="application-status"><Icon name="check" /><div><strong>Ваши отклики</strong><span>Статус обновляется работодателем после рассмотрения заявки.</span></div></div>}
        <div className="jobs-grid">
          {jobsTab === "vacancies" && visibleVacancies.map((vacancy) => {
            const application = jobApplications.find((item) => item.vacancy_id === vacancy.id);
            const companyName = vacancy.company?.company_name ?? "Компания";
            const salary = `${new Intl.NumberFormat("ru-RU").format(vacancy.salary_min)}–${new Intl.NumberFormat("ru-RU").format(vacancy.salary_max)} ₽ ${vacancy.salary_tax_type === "net" ? "на руки" : "до вычета НДФЛ"}`;
            return <article className="job-card" key={vacancy.id}>
              <div className="job-card__top"><div className="invitation-logo">{companyName.slice(0, 2).toUpperCase()}</div><div><strong>{vacancy.title}</strong><span>{companyName}</span></div>{application && <b className="job-card__status">{applicationStatusLabel(application.status)}</b>}</div>
              <div className="job-salary">{salary}</div>
              <p>{vacancy.description || "Работодатель пока не добавил описание вакансии."}</p>
              <div className="tags">{vacancy.required_skills.map((tag) => <span key={tag}>{tag}</span>)}</div>
              <div className="job-card__footer"><span>{vacancy.specialization} · {vacancy.required_grade} · {vacancy.work_format === "remote" ? "Удалённо" : vacancy.work_format === "hybrid" ? "Гибрид" : "Офис"}{vacancy.city ? ` · ${vacancy.city}` : ""}</span><Button variant={application ? "outline" : "primary"} disabled={Boolean(application) || applyingTo === vacancy.id} onClick={() => void applyToVacancy(vacancy)}>{application ? applicationStatusLabel(application.status) : applyingTo === vacancy.id ? "Отправляем…" : "Откликнуться"}</Button></div>
            </article>;
          })}
          {jobsTab === "applications" && visibleApplications.map((application) => (
            <article className="job-card" key={application.id}>
              <div className="job-card__top"><div className="invitation-logo">{application.company_name.slice(0, 2).toUpperCase()}</div><div><strong>{application.vacancy_title}</strong><span>{application.company_name}</span></div><b className="job-card__status">{applicationStatusLabel(application.status)}</b></div>
              <div className="job-salary">{new Intl.NumberFormat("ru-RU").format(application.salary_min)}–{new Intl.NumberFormat("ru-RU").format(application.salary_max)} ₽ {application.salary_tax_type === "net" ? "на руки" : "до вычета НДФЛ"}</div>
              <p>{application.status === "pending" ? "Отклик отправлен. Работодатель ещё не ответил." : application.status === "reviewed" ? "Работодатель рассматривает отклик." : application.status === "accepted" ? "Работодатель принял отклик." : "Работодатель отклонил отклик."}</p>
            </article>
          ))}
          {!jobsLoading && (jobsTab === "applications" ? visibleApplications.length === 0 : visibleVacancies.length === 0) && <div className="empty-state">{jobsTab === "applications" ? "Откликов по этому запросу нет" : "Подходящих опубликованных вакансий пока нет"}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="settings-layout">
        <section className="feature-card"><div className="feature-head"><div><span>ПРИВАТНОСТЬ</span><strong>Кому виден профиль</strong></div></div><div className="profile-status-row"><span>Согласие на обработку данных</span><strong>{profile?.agreed_152_fz ? "Сохранено" : "Не предоставлено"}</strong></div><div className="profile-status-row"><span>Согласие на OSINT-проверку</span><strong>{profile?.agreed_osint ? "Сохранено" : "Не предоставлено"}</strong></div><label className="consent-large"><input type="checkbox" checked={profile?.agreed_publication ?? false} onChange={(event) => setProfile((current) => current ? { ...current, agreed_publication: event.target.checked, visibility_public: event.target.checked ? current.visibility_public : false } : current)} /><span>Разрешаю показывать мой профиль работодателям</span></label><label className="consent-large"><input type="checkbox" checked={profile?.visibility_public ?? false} disabled={!profile?.agreed_publication} onChange={(event) => setProfile((current) => current ? { ...current, visibility_public: event.target.checked } : current)} /><span>Показывать профиль в поиске и подборке</span></label><label className="consent-large consent-large--mentor"><input type="checkbox" checked={profile?.mentor_available ?? false} disabled={!profile?.verified_grade} onChange={(event) => setProfile((current) => current ? { ...current, mentor_available: event.target.checked } : current)} /><span><strong>Готов(а) быть наставником</strong><small>Другие кандидаты смогут найти вас по навыкам и подтверждённому грейду. Контакты останутся скрыты до принятия запроса.</small></span></label><p className="feature-description feature-description--left">Для поиска ментора нужен подтверждённый грейд. Видимость профиля работодателям и участие в наставничестве настраиваются отдельно.</p><Button disabled={!profile || profileSaving} onClick={() => void saveCandidatePrivacy()}>{profileSaving ? "Сохраняем…" : "Сохранить настройки"}</Button></section>
        <section className="feature-card"><div className="feature-head"><div><span>ИНТЕГРАЦИИ</span><strong>Данные ФСП</strong></div></div><p className="feature-description feature-description--left">Пока доступны только тестовые записи. Совпадение ID не подтверждает личность и не влияет на грейд.</p><label className="field field--flush"><span>ФСП ID</span><input value={fspInput} onChange={(event) => setFspInput(event.target.value)} placeholder="Например, FSP-77-001" /></label><div className="integration-card"><div className="fsp-symbol">◆</div><div><strong>{profile?.fsp_verified ? "Тестовая запись найдена" : "Запись не найдена"}</strong><span>{profile?.fsp_id ?? "Не привязан"}</span></div><Button variant="outline" disabled={!fspInput.trim()} onClick={() => void linkFspId()}>Найти</Button></div></section>
      </div>
    </div>
  );
}

function ResumeModal({
  candidate,
  onClose,
  onInvite,
}: {
  candidate: Candidate;
  onClose: () => void;
  onInvite: () => void;
}) {
  const [version, setVersion] = useState(candidate.resumeVersions?.[0]?.id ?? "current");
  const selectedVersion = candidate.resumeVersions?.find((item) => item.id === version);
  const versionNote = selectedVersion?.summary ?? (version === "current"
    ? candidate.about
    : version === "2024"
      ? `${candidate.about} Версия сохранена до последнего обновления опыта.`
      : "Ранняя версия профиля: меньше подтверждённых навыков и опыта, указано первое место работы.");
  const trustFlag = candidate.trust < 0.78
    ? "Есть расхождение в длительности одного из мест работы. Опыт мог быть завышен."
    : candidate.trust < 0.88
      ? "Часть опыта требует дополнительного подтверждения документами."
      : "Критичных расхождений в истории резюме не обнаружено.";

  if (candidate.backendId) {
    return (
      <ModalFrame className="resume-modal" labelledBy="resume-dialog-title" onClose={onClose}>
          <div className="resume-modal__top"><div><span>ПРОФИЛЬ ИЗ БАНКА КАНДИДАТОВ</span><strong id="resume-dialog-title">Профиль кандидата</strong></div><button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть профиль"><Icon name="close" /></button></div>
          <div className="resume-cover">
            <div className="resume-avatar">{candidate.initials}</div>
            <div className="resume-cover__main"><div className="resume-name">{candidate.name}</div><strong>{candidate.role} · {candidate.level}</strong><span>{candidate.location} · {candidate.format} · Ожидания: {candidate.salary}</span><span>Готов выйти: {candidate.availableFrom ? new Date(`${candidate.availableFrom}T00:00:00`).toLocaleDateString("ru-RU") : "дата не указана"}</span></div>
            <div className="resume-match"><span>Балл подбора</span><strong>{candidate.score}</strong></div>
          </div>
          <div className="resume-versions resume-versions--backend">
            <span>ВЕРСИИ РЕЗЮМЕ</span>
            {candidate.resumeVersions?.length ? candidate.resumeVersions.map((item) => <button type="button" key={item.id} className={version === item.id ? "active" : ""} onClick={() => setVersion(item.id)}>{item.label} · {new Date(`${item.date}T00:00:00`).toLocaleDateString("ru-RU")}</button>) : <small>История версий пока не передаётся backend.</small>}
            <p>{versionNote}</p>
          </div>
          <div className="resume-layout">
            <div className="resume-main">
              <section className="resume-section"><span>ПОЧЕМУ В ПОДБОРКЕ</span><p>{candidate.summary}</p></section>
              <section className="resume-section"><span>ЗАРПЛАТНЫЕ ОЖИДАНИЯ</span><p>{candidate.salary}</p></section>
              <section className="resume-section"><span>СТЕК</span><div className="tags tags--large">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></section>
              <section className="resume-section"><span>СОПОСТАВЛЕНИЕ НАВЫКОВ</span><SkillComparison matched={candidate.matchedSkills ?? []} notListed={candidate.missingSkills ?? []} /></section>
              {candidate.requestedSkillTests?.length ? <section className="resume-section"><span>ТЕСТЫ ПО НАВЫКАМ ПОТРЕБНОСТИ</span><RequestedSkillRadar skills={candidate.requestedSkillTests} /></section> : null}
            </div>
            <aside className="resume-side">
              <section className="resume-section true-score-panel">
                <span>TRUE SCORE · ПРОВЕРКА РЕЗЮМЕ</span>
                {candidate.trueScore != null ? <><strong>{candidate.trueScore.toFixed(2).replace(".", ",")} из 1,00</strong><p>Сводный сигнал доверия, не вероятность достоверности.</p>{candidate.trueScoreFlags?.map((flag) => <div className={`true-score-flag true-score-flag--${flag.status}`} key={flag.label}><i /><div><strong>{flag.label}</strong><span>{flag.detail}</span></div></div>)}</> : <p>True Score не передаётся matching API. Не интерпретируйте отсутствие значения как подозрение.</p>}
              </section>
              <section className="resume-section"><span>ФСП</span><p>{candidate.fspVerified ? `Профиль подтверждён, достижений: ${candidate.achievementsCount ?? 0}` : "Подтверждённых достижений нет"}</p></section>
              <Button onClick={onInvite}>Пригласить кандидата <Icon name="send" /></Button>
            </aside>
          </div>
      </ModalFrame>
    );
  }

  return (
    <ModalFrame className="resume-modal" labelledBy="resume-dialog-title" onClose={onClose}>
        <div className="resume-modal__top">
          <div><span>ПОЛНОЕ РЕЗЮМЕ</span><strong id="resume-dialog-title">Профиль кандидата</strong></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть резюме"><Icon name="close" /></button>
        </div>
        <div className="resume-cover">
          <div className="resume-avatar">{candidate.initials}</div>
          <div className="resume-cover__main">
            <div className="resume-name">{candidate.name}<span className="verified"><Icon name="check" size={12} /></span></div>
            <strong>{candidate.role} · уровень {candidate.level}</strong>
            <span>{candidate.location} · {candidate.format} · опыт {candidate.experience}</span>
          </div>
          <div className="resume-match"><span>Балл подбора</span><strong>{candidate.score}</strong></div>
        </div>
        <div className="resume-versions">
          <span>ВЕРСИЯ РЕЗЮМЕ</span>
          <button type="button" className={version === "current" ? "active" : ""} onClick={() => setVersion("current")}>Текущая</button>
          <button type="button" className={version === "2024" ? "active" : ""} onClick={() => setVersion("2024")}>2024</button>
          <button type="button" className={version === "2023" ? "active" : ""} onClick={() => setVersion("2023")}>2023</button>
          <small>Можно сравнить, как менялись опыт и навыки</small>
        </div>

        <div className="resume-layout">
          <div className="resume-main">
            <section className="resume-section">
              <span>О КАНДИДАТЕ</span>
              <p>{versionNote}</p>
            </section>
            <section className="resume-section">
              <span>ОПЫТ РАБОТЫ</span>
              <div className="experience-timeline">
                {candidate.experienceItems.map((item) => (
                  <article key={item.period + item.company}>
                    <i />
                    <div><span>{item.period}</span><strong>{item.position} · {item.company}</strong><p>{item.description}</p></div>
                  </article>
                ))}
              </div>
            </section>
            <section className="resume-section">
              <span>ОБРАЗОВАНИЕ</span>
              <div className="education-row"><Icon name="briefcase" /><strong>{candidate.education}</strong></div>
            </section>
            <section className="resume-section">
              <span>ТЕХНОЛОГИИ</span>
              <div className="tags tags--large">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
            </section>
            {candidate.achievements.length > 0 && (
              <section className="resume-section">
                <span>ДОСТИЖЕНИЯ</span>
                <div className="resume-achievements">{candidate.achievements.map((item) => <div key={item}>◆ <strong>{item}</strong></div>)}</div>
              </section>
            )}
          </div>
          <aside className="resume-side">
            <section className="resume-section">
              <span>{candidate.backendId ? "ДЕМО · КАРТА НАВЫКОВ" : "КАРТА НАВЫКОВ"}</span>
              {candidate.radar.length ? <Radar values={candidate.radar} target={candidate.jobRadar} /> : <div className="swipe-skill-match"><strong>Профиль навыков</strong><p>Радар появится, когда будут доступны подтверждённые данные по компетенциям.</p></div>}
            </section>
            <section className="resume-section">
              <span>УСЛОВИЯ</span>
              <div className="resume-facts">
                <div><span>Зарплата</span><strong>{candidate.salary}</strong></div>
                <div><span>Формат</span><strong>{candidate.format}</strong></div>
                <div><span>Оценка доверия</span><strong className="green">{candidate.trust.toFixed(2).replace(".", ",")}</strong></div>
                <div><span>Профиль обновлён</span><strong>{candidate.updated}</strong></div>
              </div>
            </section>
            <section className="resume-section contact-locked">
              <span>КОНТАКТЫ</span>
              <div><strong>{candidate.email.replace(/(^.).+(@.*$)/, "$1••••$2")}</strong><strong>{candidate.telegram.slice(0, 3)}••••••</strong></div>
              <p>Полные контакты откроются после принятия приглашения кандидатом.</p>
            </section>
            <section className={`resume-section trust-flags ${candidate.trust < 0.78 ? "trust-flags--warning" : ""}`}>
              <span>TRUE SCORE · ПРОВЕРКА РЕЗЮМЕ</span>
              <strong>{candidate.trust.toFixed(2).replace(".", ",")} из 1,00</strong>
              <p>{trustFlag}</p>
              <div><i /> История должностей</div>
              <div><i /> Даты работы</div>
              <div><i /> Подтверждение навыками</div>
            </section>
          </aside>
        </div>
        <div className="resume-modal__actions">
          <Button variant="outline">Скачать PDF</Button>
          <Button onClick={onInvite}>Пригласить кандидата <Icon name="send" /></Button>
        </div>
    </ModalFrame>
  );
}

function DemoTour({
  role,
  onFinish,
}: {
  role: "employer" | "candidate";
  onFinish: () => void;
}) {
  const [step, setStep] = useState(0);
  const [targetTop, setTargetTop] = useState<number | null>(null);
  const tourRef = useRef<HTMLElement>(null);
  const steps = role === "employer" ? [
    { target: "demo-navigation", title: "Рабочие разделы", text: "Переключайтесь между подборкой, потребностями, банком профилей и приглашениями." },
    { target: "active-need", title: "Потребность команды", text: "Здесь видны критерии и бюджет текущей роли. Нажмите карточку, чтобы открыть подбор." },
    { target: "candidate-filters", title: "Быстрый поиск", text: "Ищите по имени и навыкам, включайте фильтр достижений ФСП и выбирайте вид списка." },
    { target: "candidate-profile", title: "Профиль и оффер", text: "Проверьте объяснение совпадения, сравните навыки и отправьте демо-приглашение." },
  ] : [
    { target: "candidate-dashboard", title: "Ваш кабинет", text: "Здесь собраны статус профиля и приглашения, которым нужен ваш ответ." },
    { target: "fsp-tools", title: "Путь через ФСП", text: "В демо можно пройти олимпиаду по навыкам и передать диплом в локальную очередь проверки." },
    { target: "demo-navigation", title: "Дальнейшие действия", text: "Откройте профиль, тест уровня, историю результатов и входящие приглашения." },
  ];
  const item = steps[step];
  useDialogA11y(tourRef, onFinish);

  useEffect(() => {
    let measureTimer = 0;
    const update = () => {
      const target = document.querySelector<HTMLElement>(`[data-tour="${item.target}"]`);
      if (!target) {
        setTargetTop(null);
        return;
      }
      setTargetTop(target.getBoundingClientRect().top);
    };
    document.querySelector(`[data-tour="${item.target}"]`)?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
    measureTimer = window.setTimeout(update, 180);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.clearTimeout(measureTimer);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [item.target]);

  const isLastStep = step === steps.length - 1;
  const cardAtBottom = targetTop !== null ? targetTop < window.innerHeight * 0.48 : true;
  return (
    <>
      <div className="tour-shade tour-shade--full" />
      <section ref={tourRef} className={`demo-tour-card ${cardAtBottom ? "demo-tour-card--bottom" : "demo-tour-card--top"}`} role="dialog" aria-modal="true" aria-labelledby="demo-tour-title" tabIndex={-1}>
        <div className="guide-progress">{steps.map((_, index) => <i key={index} className={index <= step ? "active" : ""} />)}</div>
        <span>{role === "employer" ? "ДЕМО · КОМПАНИЯ" : "ДЕМО · КАНДИДАТ"} · {step + 1}/{steps.length}</span>
        <strong id="demo-tour-title">{item.title}</strong>
        <p>{item.text}</p>
        <div className="guide-actions"><Button variant="ghost" onClick={onFinish}>Пропустить</Button><Button onClick={() => isLastStep ? onFinish() : setStep((current) => current + 1)}>{isLastStep ? "Начать работу" : "Далее"} <Icon name="chevron" /></Button></div>
      </section>
    </>
  );
}

function AuthScreen({
  onLogin,
  onRegister,
  onVerify,
  onDemoLogin,
}: {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, role: "employer" | "candidate") => Promise<string | undefined>;
  onVerify: (email: string, code: string) => Promise<void>;
  onDemoLogin: (role: "candidate" | "employer") => Promise<void>;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [selectedRole, setSelectedRole] = useState<"employer" | "candidate">("candidate");
  const [email, setEmail] = useState<string>(DEMO_ACCOUNTS.candidate);
  const [password, setPassword] = useState<string>(DEMO_PASSWORD);
  const [confirmed, setConfirmed] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [code, setCode] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submitCredentials = async () => {
    if (!email || !password || (mode === "register" && !confirmed)) return;
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        setDemoCode((await onRegister(email, password, selectedRole)) ?? "");
        setEmailSent(true);
      } else {
        await onLogin(email, password);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось выполнить запрос");
    } finally {
      setBusy(false);
    }
  };

  const verifyEmail = async () => {
    setBusy(true);
    setError("");
    try {
      await onVerify(email, code);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось подтвердить email");
    } finally {
      setBusy(false);
    }
  };

  const signInToDemo = async (role: "candidate" | "employer") => {
    setBusy(true);
    setError("");
    try {
      await onDemoLogin(role);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось войти в демо-аккаунт");
    } finally {
      setBusy(false);
    }
  };

  const fillDemoCredentials = (role: "candidate" | "employer") => {
    setEmail(DEMO_ACCOUNTS[role]);
    setPassword(DEMO_PASSWORD);
    setMode("login");
    setEmailSent(false);
    setError("");
  };

  return (
    <div className="auth-page">
      <div className="auth-brand">
        <Logo />
        <span>КАРЬЕРА С ПОДТВЕРЖДЁННЫМИ НАВЫКАМИ</span>
        <strong>Работа, где сначала смотрят на то, что вы умеете</strong>
        <p>Подтвердите грейд тестом, дополните профиль достижениями ФСП и получайте предложения с зарплатой.</p>
        <div className="auth-benefits">
          <div><Icon name="check" /><span>Объективная оценка навыков</span></div>
          <div><Icon name="check" /><span>Зарплата известна до общения</span></div>
          <div><Icon name="check" /><span>Контакты под вашим контролем</span></div>
        </div>
      </div>
      <div className="auth-card">
        <div className="auth-tabs"><button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setEmailSent(false); }}>Вход</button><button type="button" className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setEmailSent(false); }}>Регистрация</button></div>
        <span>{mode === "login" ? "ДОБРО ПОЖАЛОВАТЬ" : "СОЗДАЙТЕ АККАУНТ"}</span>
        <strong>{mode === "login" ? "Войдите в ФСП Карьеру" : "Начните карьерный профиль"}</strong>
        <p>{mode === "login" ? "Войдите с email и паролем, указанными при регистрации." : "Выберите роль для нового аккаунта."}</p>
        {mode === "register" && <div className="auth-role">
          <button type="button" className={selectedRole === "candidate" ? "active" : ""} onClick={() => setSelectedRole("candidate")}><Icon name="users" /><strong>Кандидат</strong><span>Ищу предложения</span></button>
          <button type="button" className={selectedRole === "employer" ? "active" : ""} onClick={() => setSelectedRole("employer")}><Icon name="briefcase" /><strong>Компания</strong><span>Ищу специалистов</span></button>
        </div>}
        {!emailSent ? (
          <>
            <label className="field field--flush"><span>EMAIL</span><input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="username" /></label>
            <label className="field field--flush"><span>ПАРОЛЬ</span><input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
            {mode === "register" && <label className="auth-consent"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>Согласен на обработку персональных данных по 152-ФЗ</span></label>}
            <Button className={busy || !email || !password || (mode === "register" && !confirmed) ? "button--disabled" : ""} onClick={submitCredentials}>
              {busy ? "Подождите…" : mode === "login" ? "Войти в кабинет" : "Создать аккаунт"} <Icon name="chevron" />
            </Button>
          </>
        ) : (
          <div className="email-confirm">
            <div className="result-check"><Icon name="send" /></div>
            <strong>Письмо отправлено</strong>
            <p>Введите код подтверждения для {email}.</p>
            {demoCode && <div className="verification-code">Код для локального демо: <strong>{demoCode}</strong></div>}
            <label className="field field--flush"><span>КОД ПОДТВЕРЖДЕНИЯ</span><input value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" inputMode="numeric" /></label>
            <Button className={busy || code.length < 4 ? "button--disabled" : ""} onClick={verifyEmail}>{busy ? "Проверяем…" : "Подтвердить и продолжить"}</Button>
            <button type="button" className="manual-link" onClick={() => setEmailSent(false)}>Изменить email</button>
          </div>
        )}
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="demo-access">
          <div className="demo-access__intro"><span>ДЕМО-ДОСТУП</span><small>Тестовый логин и пароль уже заполнены для кандидата.</small></div>
          <div className="demo-access__fill">
            <button type="button" onClick={() => fillDemoCredentials("candidate")}>Данные кандидата</button>
            <button type="button" onClick={() => fillDemoCredentials("employer")}>Данные компании</button>
          </div>
          <div>
            <Button variant="outline" disabled={busy} onClick={() => void signInToDemo("candidate")}><Icon name="users" /> {busy ? "Подключаем…" : "Войти как кандидат"}</Button>
            <Button variant="outline" disabled={busy} onClick={() => void signInToDemo("employer")}><Icon name="briefcase" /> {busy ? "Подключаем…" : "Войти как компания"}</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CandidateOnboarding({ onComplete }: { onComplete: (payload: {
  first_name: string;
  last_name: string;
  specialization: string;
  programming_language: string | null;
  declared_grade: string;
  work_format: string;
  city: string;
  fsp_id: string | null;
  agreed_152_fz: boolean;
  agreed_publication: boolean;
  visibility_public: boolean;
  agreed_osint: boolean;
}) => Promise<void> }) {
  const [step, setStep] = useState(0);
  const [consent, setConsent] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [specialization, setSpecialization] = useState("Backend");
  const [grade, setGrade] = useState("middle");
  const [city, setCity] = useState("Москва");
  const [format, setFormat] = useState("Удалённо");
  const [fspId, setFspId] = useState("");
  const [osint, setOsint] = useState(false);
  const [publication, setPublication] = useState(false);
  const [saving, setSaving] = useState(false);
  const steps = ["Профиль", "Специализация", "Формат работы", "Резюме", "ФСП и проверка"];
  const canContinue = step !== 0 || (consent && firstName.trim().length > 0 && lastName.trim().length > 0);
  const complete = async () => {
    setSaving(true);
    try {
      await onComplete({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        specialization,
        programming_language: specialization === "Backend" ? "Python" : null,
        declared_grade: grade,
        work_format: format === "Удалённо" ? "remote" : format === "Гибрид" ? "hybrid" : "office",
        city: city.trim(),
        fsp_id: fspId.trim() || null,
        agreed_152_fz: consent,
        agreed_publication: publication,
        visibility_public: publication,
        agreed_osint: osint,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <Logo />
        <div className="onboarding-progress">{steps.map((item, index) => <div key={item} className={index <= step ? "active" : ""}><b>{index + 1}</b><span>{item}</span></div>)}</div>
        <div className="onboarding-content">
          {step === 0 && <><span>ШАГ 1</span><strong>Заполните профиль</strong><p>Укажите имя и подтвердите согласие на обработку данных перед созданием профиля.</p><div className="field-row field-row--flush"><label className="field"><span>ИМЯ</span><input value={firstName} onChange={(event) => setFirstName(event.target.value)} autoComplete="given-name" /></label><label className="field"><span>ФАМИЛИЯ</span><input value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" /></label></div><label className="consent-large"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>Согласен на обработку персональных данных по 152-ФЗ.</span></label></>}
          {step === 1 && <><span>ШАГ 2</span><strong>Выберите направление и уровень</strong><p>Грейд подтверждает только тест. Достижения ФСП влияют на порядок в подборке, но грейд не подтверждают. {TEST_AVAILABILITY_HINT}</p><div className="field-row field-row--flush"><label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={specialization} onChange={(event) => setSpecialization(event.target.value)}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label><label className="field"><span>ПРЕДПОЛАГАЕМЫЙ УРОВЕНЬ</span><select value={grade} onChange={(event) => setGrade(event.target.value)}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></div>{specialization === "Backend" && <label className="field field--flush"><span>ЯЗЫК БАЗОВОГО ТЕСТА</span><select value="Python" disabled><option value="Python">Python</option></select><small>Сейчас для Backend подготовлен только Python. Другие языки добавим отдельными наборами.</small></label>}{!isTestablePair(specialization, grade) && <p className="feature-description feature-description--left">Для пары «{specialization} · {grade}» теста пока нет — профиль сохранить можно, но сквозной сценарий с подтверждённым грейдом сейчас проходится на Backend Junior / Middle / Senior. <Button variant="outline" onClick={() => { setSpecialization("Backend"); setGrade("middle"); }}>Выбрать Backend · Middle для теста</Button></p>}</>}
          {step === 2 && <><span>ШАГ 3</span><strong>Где и как вы хотите работать</strong><div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={city} onChange={(event) => setCity(event.target.value)} /></label><label className="field"><span>ФОРМАТ</span><select value={format} onChange={(event) => setFormat(event.target.value)}><option>Удалённо</option><option>Гибрид</option><option>Офис</option></select></label></div><ToggleRow title="Готов к переезду" detail="Работодатели смогут учитывать это при подборе" /></>}
          {step === 3 && <><span>ШАГ 4</span><strong>Резюме и опыт</strong><p>После завершения настройки откройте раздел «Профиль», чтобы загрузить PDF. Распознанные данные можно проверить и исправить перед сохранением.</p><div className="notice-box">Для продолжения загрузка резюме не обязательна.</div></>}
          {step === 4 && <><span>ШАГ 5</span><strong>Публикация и данные ФСП</strong><p>Профиль можно сохранить скрытым и открыть для работодателей позже в настройках.</p><label className="consent-large"><input type="checkbox" checked={publication} onChange={(event) => setPublication(event.target.checked)} /><span>Разрешаю показывать мой профиль работодателям в поиске и подборке</span></label><label className="field field--flush"><span>ФСП ID · НЕОБЯЗАТЕЛЬНО</span><input value={fspId} onChange={(event) => setFspId(event.target.value)} placeholder="Например, FSP-2025-00142" /></label><label className="consent-large"><input type="checkbox" checked={osint} onChange={(event) => setOsint(event.target.checked)} /><span>Разрешаю проверку истории резюме для расчёта оценки доверия. Без согласия будет установлено нейтральное значение 0,50.</span></label></>}
        </div>
        <div className="onboarding-actions"><Button variant="ghost" onClick={() => setStep(Math.max(0, step - 1))}>{step === 0 ? "Вернуться ко входу" : "Назад"}</Button><Button className={!canContinue || saving ? "button--disabled" : ""} onClick={() => { if (!canContinue || saving) return; if (step === steps.length - 1) void complete(); else setStep(step + 1); }}>{saving ? "Сохраняем…" : step === steps.length - 1 ? "Завершить настройку" : "Далее"} <Icon name="chevron" /></Button></div>
      </div>
    </div>
  );
}

function SwipeDeck({
  items,
  onOpen,
  onSelect,
  onNotify,
}: {
  items: Candidate[];
  onOpen: (candidate: Candidate) => void;
  onSelect: (candidate: Candidate) => void;
  onNotify: (message: string) => void;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState(0);
  const [direction, setDirection] = useState<"left" | "right" | null>(null);
  const [entering, setEntering] = useState(false);
  const candidate = items[activeIndex];
  const nextCandidate = items[activeIndex + 1];
  const itemIds = items.map(({ id }) => id).join(",");

  useEffect(() => {
    setActiveIndex(0);
    setDragStart(null);
    setDragOffset(0);
    setDirection(null);
  }, [itemIds]);

  const move = (nextDirection: "left" | "right") => {
    if (direction || !candidate) return;
    setDirection(nextDirection);
    setDragStart(null);
    setDragOffset(0);
    window.setTimeout(() => {
      if (nextDirection === "right") {
        onSelect(candidate);
        onNotify(`${candidate.name} добавлен в список сравнения`);
      }
      setActiveIndex((current) => current + 1);
      setDirection(null);
      setEntering(true);
      window.setTimeout(() => setEntering(false), 400);
    }, 340);
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLElement>) => {
    if ((event.target as HTMLElement).closest("button")) return;
    setDragStart(event.clientX);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLElement>) => {
    if (dragStart === null || direction) return;
    setDragOffset(event.clientX - dragStart);
  };

  const handlePointerUp = () => {
    if (dragStart === null) return;
    if (dragOffset > 90) move("right");
    else if (dragOffset < -90) move("left");
    else {
      setDragStart(null);
      setDragOffset(0);
    }
  };

  const handlePointerCancel = () => {
    setDragStart(null);
    setDragOffset(0);
  };

  if (!candidate) {
    return (
      <div className="swipe-workspace">
        <div className="swipe-complete">
          <div className="swipe-complete__icon"><Icon name="check" size={28} /></div>
          <span>ПРОСМОТР ЗАВЕРШЁН</span>
          <strong>Вы просмотрели всех кандидатов</strong>
          <p>Вернитесь к списку и измените фильтры, чтобы увидеть другие профили.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="swipe-workspace">
      <div className="swipe-help"><Icon name="sparkle" /><div><strong>Найдите подходящего человека</strong><span>Свайпните карточку или используйте кнопки: влево — пропустить, вправо — добавить в сравнение.</span></div></div>
      <div className="swipe-deck">
        {nextCandidate && <article className="swipe-card swipe-card--under" aria-hidden="true"><span>СЛЕДУЮЩИЙ ПРОФИЛЬ</span><strong>{nextCandidate.name}</strong><small>{nextCandidate.role} · {nextCandidate.level} · {nextCandidate.score} баллов</small></article>}
        <article
          className={`swipe-card ${direction ? `swipe-card--leaving-${direction}` : entering ? "swipe-card--entering" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerCancel}
          style={dragStart !== null && !direction ? { transform: `translateX(${dragOffset}px) rotate(${dragOffset / 18}deg)` } : undefined}
        >
          {dragOffset < -36 && <div className="swipe-stamp swipe-stamp--skip">ПРОПУСТИТЬ</div>}
          {dragOffset > 36 && <div className="swipe-stamp swipe-stamp--like">ИНТЕРЕСЕН</div>}
          <div className="swipe-card__cover">
            <div className="resume-avatar">{candidate.initials}</div>
            <div><span>ПОДТВЕРЖДЁННЫЙ ПРОФИЛЬ</span><strong>{candidate.name}</strong><p>{candidate.role} · уровень {candidate.level}</p></div>
            <div className="resume-match"><span>Балл подбора</span><strong>{candidate.score}</strong></div>
          </div>
          <div className="swipe-card__body">
            {candidate.requestedSkillTests?.length ? <RequestedSkillRadar skills={candidate.requestedSkillTests} /> : candidate.radar.length ? <Radar values={candidate.radar} target={candidate.jobRadar} /> : <div className="swipe-skill-match"><strong>Совпадение по навыкам</strong><div><span>Совпало</span><b>{candidate.matchedSkills?.join(" · ") || "Нет данных"}</b></div><div><span>Проверить</span><b>{candidate.missingSkills?.join(" · ") || "Нет данных"}</b></div></div>}
            <div className="swipe-details">
              <p>{candidate.summary}</p>
              <div className="compare-facts">
                <div><span><Icon name="clock" size={15} /> Опыт</span><strong>{candidate.experience}</strong></div>
                <div><span><Icon name="money" size={15} /> Ожидания</span><strong>{candidate.salary}</strong></div>
                <div><span><Icon name="pin" size={15} /> Город</span><strong>{candidate.location}</strong></div>
                <div><span><Icon name="building" size={15} /> Формат</span><strong>{candidate.format}</strong></div>
              </div>
              <div className="tags">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
              {candidate.achievements[0] && <div className="swipe-achievement"><Icon name="medal" size={17} /> {candidate.achievements[0]}</div>}
              <Button variant="ghost" onClick={() => onOpen(candidate)}>Открыть полное резюме <Icon name="arrowUpRight" size={16} /></Button>
            </div>
          </div>
        </article>
        <div className="swipe-actions">
          <button type="button" className="swipe-action swipe-action--skip" onClick={() => move("left")} aria-label="Пропустить кандидата"><Icon name="close" /><span>Пропустить</span></button>
          <button type="button" className="swipe-action swipe-action--open" onClick={() => onOpen(candidate)} aria-label="Открыть резюме"><Icon name="users" /><span>Резюме</span></button>
          <button type="button" className="swipe-action swipe-action--save" onClick={() => move("right")} aria-label="Добавить кандидата в сравнение"><Icon name="check" /><span>Интересен</span></button>
        </div>
        <div className="swipe-counter">{activeIndex + 1} из {items.length} · перетащите карточку влево или вправо</div>
      </div>
    </div>
  );
}

function CompareModal({
  items,
  onClose,
  onOpen,
}: {
  items: Candidate[];
  onClose: () => void;
  onOpen: (candidate: Candidate) => void;
}) {
  const factIcons: Record<string, string> = {
    Уровень: "school",
    Опыт: "clock",
    Зарплата: "money",
    Доверие: "shield",
    Город: "pin",
    Формат: "building",
  };
  return (
    <ModalFrame className="compare-modal" labelledBy="compare-title" onClose={onClose}>
        <div className="resume-modal__top compare-modal__top">
          <div><span>СРАВНЕНИЕ РЕЗЮМЕ</span><strong id="compare-title">Сравните кандидатов рядом</strong><small>В сравнении: {items.length} · выберите сильнейшее совпадение для команды</small></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть сравнение"><Icon name="close" /></button>
        </div>
        <div className="compare-grid">
          {items.map((candidate, index) => (
            <article className="compare-column" key={candidate.id}>
              <div className="compare-person">
                <div className="avatar avatar--large">{candidate.initials}</div>
                <div><span className="compare-candidate-index">КАНДИДАТ {String(index + 1).padStart(2, "0")}</span><strong>{candidate.name}</strong><span>{candidate.role}</span></div>
              </div>
              <div className="compare-score">
                <div><span>СОВПАДЕНИЕ С ПОТРЕБНОСТЬЮ</span><small>Балл подбора</small></div>
                <strong>{candidate.score}<small> / 100</small></strong>
              </div>
              <div className="compare-match-details">
                <SkillComparison matched={candidate.matchedSkills ?? []} notListed={candidate.missingSkills ?? []} />
              </div>
              {candidate.requestedSkillTests?.length ? <div className="compare-radar"><RequestedSkillRadar skills={candidate.requestedSkillTests} compact /></div> : candidate.radar.length > 0 && <div className="compare-radar"><Radar values={candidate.radar} target={candidate.jobRadar} compact /></div>}
              <div className="compare-facts">
                {[
                  ["Уровень", candidate.level],
                  ["Опыт", candidate.backendId ? "Нет данных" : candidate.experience],
                  ["Зарплата", candidate.backendId ? "Нет данных" : candidate.salary],
                  ["Доверие", candidate.backendId ? "Нет данных" : candidate.trust.toFixed(2).replace(".", ",")],
                  ["Город", candidate.location],
                  ["Формат", candidate.format],
                ].map(([label, value]) => (
                  <div key={label}><span><Icon name={factIcons[label]} size={15} />{label}</span><strong>{value}</strong></div>
                ))}
              </div>
              <div className="compare-skills"><span>ТЕХНОЛОГИИ</span><div className="tags">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></div>
              <div className="compare-summary"><span><Icon name="sparkle" size={15} /> ПОЧЕМУ В ПОДБОРКЕ</span><p>{candidate.summary}</p></div>
              <Button variant="outline" onClick={() => onOpen(candidate)}><Icon name="arrowUpRight" size={16} /> Открыть профиль</Button>
            </article>
          ))}
        </div>
      </ModalFrame>
  );
}

function SkillComparison({ matched, notListed }: { matched: string[]; notListed: string[] }) {
  if (!matched.length && !notListed.length) {
    return <p className="compare-skill-note">Подробное сопоставление навыков не передано API.</p>;
  }
  return (
    <div className="skill-comparison">
      <div>
        <strong><Icon name="check" size={15} /> Найдены в профиле</strong>
        {matched.length ? <ul>{matched.map((skill) => <li key={skill}>{skill}</li>)}</ul> : <span>Совпадения не указаны</span>}
      </div>
      <div>
        <strong><Icon name="arrowUpRight" size={15} /> Не указаны в профиле</strong>
        {notListed.length ? <ul>{notListed.map((skill) => <li key={skill}>{skill}</li>)}</ul> : <span>Не найдено</span>}
      </div>
      <p>Список показывает наличие упоминаний в данных профиля, а не оценку уровня владения или процент совместимости.</p>
    </div>
  );
}

function RequestedSkillRadar({ skills, compact = false }: { skills: RequestedSkillTest[]; compact?: boolean }) {
  if (skills.length === 0) return null;
  const measured = skills.filter((skill) => skill.percentage !== null).length;
  return <div className={`requested-skill-radar ${compact ? "requested-skill-radar--compact" : ""}`}>
    {skills.length >= 3 && measured > 0 ? <Radar
      values={skills.map((skill) => skill.percentage === null ? null : Math.max(0, Math.min(10, skill.percentage / 10)))}
      target={skills.map(() => 10)}
      axisLabels={skills.map((skill) => skill.name)}
      compact={compact}
      showAxisLabels={!compact && skills.length <= 6}
      description={`Результаты тестов по запрошенным навыкам: ${skills.map((skill) => `${skill.name} — ${skill.percentage === null ? "нет результата" : `${skill.percentage}%`}`).join(", ")}`}
    /> : null}
    {compact ? <>
      <small>{measured === 0 ? "Нет результатов тестов по этим навыкам" : `${measured} из ${skills.length} навыков оценены тестом`}</small>
      {measured > 0 && <div className="requested-skill-radar__mini-results">
        {skills.slice(0, 6).map((skill) => <span key={skill.name}>{skill.name}: {skill.percentage === null ? "нет результата" : `${skill.percentage}%`}</span>)}
        {skills.length > 6 && <span>Ещё {skills.length - 6} — в профиле</span>}
      </div>}
    </> : <>
      <div className="requested-skill-radar__results">
        {skills.map((skill) => <div key={skill.name}>
          <span>{skill.name}</span>
          <strong>{skill.percentage === null ? "Нет результата теста" : `${skill.percentage}% на уровне ${skill.test_grade}`}</strong>
          {skill.test_kind === "additional" && <small>Дополнительный тест</small>}
        </div>)}
      </div>
      <p>{skills.length > 6 && "Навыки расположены по часовой стрелке от верхней оси; их названия и результаты указаны выше. "}{measured === 0
        ? "По этим требованиям пока нет результатов тестов. Это не оценка знаний кандидата."
        : measured === skills.length
        ? "Каждая вершина показывает долю баллов за тест на подтверждённом грейде; внешний контур соответствует 100%."
        : "Закрашены участки по навыкам с результатами тестов на подтверждённом грейде. Пустая ось означает, что результата пока нет, а не нулевой уровень навыка."}</p>
    </>}
  </div>;
}

function App() {
  const [offlineDemo, setOfflineDemo] = useState(() => window.localStorage.getItem("fsp-offline-demo") === "true");
  const [authenticated, setAuthenticated] = useState(() => Boolean(window.localStorage.getItem("fsp-access-token")) || window.localStorage.getItem("fsp-offline-demo") === "true");
  const [authLoading, setAuthLoading] = useState(() => Boolean(window.localStorage.getItem("fsp-access-token")) || window.localStorage.getItem("fsp-offline-demo") === "true");
  const [demoTourOpen, setDemoTourOpen] = useState(() => window.localStorage.getItem("fsp-offline-demo") === "true" && window.localStorage.getItem("fsp-demo-tour-complete") !== "true");
  const [onboarding, setOnboarding] = useState(false);
  const [role, setRole] = useState<"employer" | "candidate">(() =>
    window.localStorage.getItem("fsp-role") === "employer" ? "employer" : "candidate",
  );
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.localStorage.getItem("fsp-theme") === "dark" ? "dark" : "light",
  );
  const [active, setActive] = useState(() =>
    window.localStorage.getItem("fsp-role") === "employer" ? "Подборка" : "Обзор",
  );
  const [selectedDialogueTarget, setSelectedDialogueTarget] = useState<string | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(1);
  const [query, setQuery] = useState("");
  const [onlyFsp, setOnlyFsp] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterFormat, setFilterFormat] = useState("");
  const [filterCity, setFilterCity] = useState("");
  const [compare, setCompare] = useState<number[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteDirty, setInviteDirty] = useState(false);
  const [inviteDiscardConfirm, setInviteDiscardConfirm] = useState(false);
  const [sent, setSent] = useState(false);
  const [offerDescription, setOfferDescription] = useState("Приглашаем в продуктовую команду. Будем рады обсудить задачи и ваш опыт.");
  const [inviteSalaryMin, setInviteSalaryMin] = useState("");
  const [inviteSalaryMax, setInviteSalaryMax] = useState("");
  const [inviteSalaryType, setInviteSalaryType] = useState<"gross" | "net">("gross");
  const [inviteContact, setInviteContact] = useState("");
  const [notice, setNotice] = useState("");
  const [resumeCandidate, setResumeCandidate] = useState<Candidate | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "swipe">("list");
  const [backendCandidates, setBackendCandidates] = useState<Candidate[]>([]);
  const [employerNeeds, setEmployerNeeds] = useState<EmployerNeedRecord[]>([]);
  const [activeNeedId, setActiveNeedId] = useState<string | null>(null);
  const [sidebarIdentity, setSidebarIdentity] = useState({ name: "", email: "" });
  const [sidebarPendingInvitations, setSidebarPendingInvitations] = useState(0);
  const [noticeType, setNoticeType] = useState<"success" | "error">("success");
  const [noticeTimer, setNoticeTimer] = useState<number | undefined>();

  useEffect(() => {
    window.localStorage.setItem("fsp-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!authenticated) {
      setAuthLoading(false);
      return;
    }
    setAuthLoading(true);
    apiGet<{ role: "candidate" | "employer"; onboarding_completed: boolean }>("/auth/me")
      .then((user) => {
        setRole(user.role);
        window.localStorage.setItem("fsp-role", user.role);
        setActive((current) => pageForRole(current, user.role));
        setOnboarding(user.role === "candidate" && !user.onboarding_completed);
        if (user.role === "employer" && !user.onboarding_completed) setActive("Настройки");
      })
      .catch(() => {
        clearSession();
        setAuthenticated(false);
      })
      .finally(() => {
        setAuthLoading(false);
      });
  }, [authenticated, offlineDemo]);

  useEffect(() => {
    setActive((current) => pageForRole(current, role));
  }, [role]);

  useEffect(() => {
    if (!authenticated || authLoading || role !== "employer") {
      setBackendCandidates([]);
      setEmployerNeeds([]);
      setActiveNeedId(null);
      return;
    }
    let cancelled = false;
    apiGet<EmployerNeedRecord[]>("/needs")
      .then(async (items) => {
        if (cancelled) return;
        setEmployerNeeds(items);
        const currentNeed = items.find((need) => need.is_active);
        setActiveNeedId(currentNeed?.id ?? null);
        if (!currentNeed) return [];
        return apiGet<{ candidates: MatchingCandidate[] }>(`/matching/for-need/${currentNeed.id}`)
          .then((response) => response.candidates);
      })
      .then((items) => {
        if (!cancelled && items) {
          setBackendCandidates(items.map((item, index) => mapMatchToCandidate(item, index, offlineDemo)));
          setSelectedCandidate(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setBackendCandidates([]);
          showNotice(error instanceof Error ? error.message : "Не удалось загрузить подбор", "error");
        }
      });
    return () => { cancelled = true; };
  }, [authenticated, authLoading, role, offlineDemo]);

  useEffect(() => {
    if (!authenticated || authLoading || onboarding) return;
    let cancelled = false;
    const refreshSidebar = () => {
      const profileRequest = role === "employer"
        ? apiGet<EmployerProfileData>("/employer/profile").then((data) => ({
            name: data.company_name || "Компания", email: data.email,
          }))
        : apiGet<CandidateProfileData>("/candidate/profile").then((data) => ({
            name: `${data.first_name} ${data.last_name}`.trim() || "Кандидат", email: data.email,
          }));
      profileRequest.then((identity) => {
        if (!cancelled) setSidebarIdentity(identity);
      }).catch(() => {
        if (!cancelled) setSidebarIdentity({ name: "", email: "" });
      });
      apiGet<Array<{ status: string }>>(role === "employer" ? "/invitations/sent" : "/invitations/my")
        .then((items) => {
          if (!cancelled) setSidebarPendingInvitations(items.filter((item) =>
            item.status === "sent" || item.status === "viewed",
          ).length);
        })
        .catch(() => { if (!cancelled) setSidebarPendingInvitations(0); });
    };
    refreshSidebar();
    window.addEventListener("fsp-invitations-updated", refreshSidebar);
    return () => {
      cancelled = true;
      window.removeEventListener("fsp-invitations-updated", refreshSidebar);
    };
  }, [authenticated, authLoading, onboarding, role, active]);

  const availableCities = useMemo(
    () => [...new Set(backendCandidates.map((candidate) => candidate.location)
      .filter((city) => city && city !== "Не указан"))].sort((left, right) => left.localeCompare(right, "ru")),
    [backendCandidates],
  );
  const activeFilterCount = Number(Boolean(filterFormat)) + Number(Boolean(filterCity));
  const filtered = useMemo(
    () => backendCandidates.filter((candidate) =>
      (!onlyFsp || candidate.fspVerified) &&
      (!filterFormat || candidate.format === filterFormat) &&
      (!filterCity || candidate.location === filterCity) &&
      `${candidate.name} ${candidate.skills.join(" ")}`.toLowerCase().includes(query.toLowerCase()),
    ),
    [backendCandidates, onlyFsp, filterFormat, filterCity, query],
  );
  const selected =
    filtered.find((candidate) => candidate.backendId === selectedCandidate?.backendId) ??
    filtered.find((candidate) => candidate.id === selectedId) ?? filtered[0] ?? candidates[0];
  const activeNeed = employerNeeds.find((need) => need.id === activeNeedId);
  const openInvite = () => {
    setOfferDescription("Приглашаем в продуктовую команду. Будем рады обсудить задачи и ваш опыт.");
    setInviteSalaryMin(activeNeed ? String(activeNeed.salary_min) : "");
    setInviteSalaryMax(activeNeed ? String(activeNeed.salary_max) : "");
    setInviteSalaryType(activeNeed?.salary_tax_type ?? "gross");
    setInviteContact("");
    setInviteDirty(false);
    setInviteDiscardConfirm(false);
    setInviteOpen(true);
  };
  const requestCloseInvite = () => {
    if (inviteDirty) {
      setInviteDiscardConfirm(true);
      return;
    }
    setInviteOpen(false);
  };
  const discardInvite = () => {
    setInviteOpen(false);
    setInviteDirty(false);
    setInviteDiscardConfirm(false);
  };

  const nav =
    role === "employer"
      ? [
          ["grid", "Обзор"],
          ["users", "Подборка"],
          ["search", "Банк кандидатов"],
          ["briefcase", "Потребности"],
          ["chat", "Диалоги"],
          ["mail", "Приглашения"],
          ["briefcase", "Вакансии компании"],
          ["chart", "Аналитика"],
          ["settings", "Настройки"],
        ]
      : [
          ["grid", "Обзор"],
          ["users", "Профиль"],
          ["chart", "Тестирование"],
          ["compare", "Мой грейд"],
          ["briefcase", "Задания"],
          ["chat", "Диалоги"],
          ["mail", "Приглашения"],
          ["search", "Вакансии"],
          ["settings", "Настройки"],
        ];
  const currentCopy = pageCopy[active] ?? pageCopy["Обзор"];
  const groupLabels: Record<string, string> =
    role === "employer"
      ? { Обзор: "ГЛАВНОЕ", Потребности: "ПОДБОР", Диалоги: "ОБЩЕНИЕ", Приглашения: "РАБОТА", Аналитика: "ДАННЫЕ" }
      : { Обзор: "ГЛАВНОЕ", Профиль: "ПРОФИЛЬ", Тестирование: "ОЦЕНКА", Диалоги: "ОБЩЕНИЕ", Приглашения: "РАБОТА" };

  const showNotice = (message: string, type: "success" | "error" = "success") => {
    setNotice(message);
    setNoticeType(type);
    if (noticeTimer) window.clearTimeout(noticeTimer);
    setNoticeTimer(window.setTimeout(() => setNotice(""), 4200));
  };

  const navigateTo = (screen: string, target?: string) => {
    if (screen === "Диалоги") setSelectedDialogueTarget(target ?? null);
    setActive(screen);
    setMobileNavOpen(false);
  };

  const enterWithSession = (response: AuthResponse) => {
    saveSession(response);
    setAuthenticated(true);
    setRole(response.role);
    setActive(response.role === "employer" ? response.onboarding_completed ? "Подборка" : "Настройки" : "Обзор");
    setOnboarding(response.role === "candidate" && !response.onboarding_completed);
  };

  const login = async (email: string, password: string) => {
    enterWithSession(await apiPost<AuthResponse>("/auth/login", { email, password }));
  };

  const register = async (email: string, password: string, selectedRole: "employer" | "candidate") => {
    const result = await apiPost<{ verification_code?: string }>("/auth/register", {
      email,
      password,
      role: selectedRole,
    });
    return result.verification_code;
  };

  const verifyEmail = async (email: string, code: string) => {
    enterWithSession(await apiPost<AuthResponse>("/auth/verify-email", { email, code }));
  };

  const demoLogin = async (demoRole: "candidate" | "employer") => {
    try {
      await apiPost("/system/seed");
      const response = await apiPost<AuthResponse>("/auth/login", {
        email: DEMO_ACCOUNTS[demoRole],
        password: DEMO_PASSWORD,
      });
      if (response.role !== demoRole) throw new Error("Backend вернул аккаунт с другой ролью");
      enterWithSession(response);
      setDemoTourOpen(window.localStorage.getItem("fsp-demo-tour-complete") !== "true");
    } catch (error) {
      if (error instanceof Error && !("status" in error)) {
        window.localStorage.setItem("fsp-offline-demo", "true");
        window.localStorage.setItem("fsp-role", demoRole);
        setOfflineDemo(true);
        setAuthenticated(true);
        setRole(demoRole);
        setActive(demoRole === "employer" ? "Обзор" : "Обзор");
        setDemoTourOpen(window.localStorage.getItem("fsp-demo-tour-complete") !== "true");
        return;
      }
      throw error;
    }
  };

  const logout = async () => {
    const refreshToken = window.localStorage.getItem("fsp-refresh-token");
    try {
      if (refreshToken && !offlineDemo) await apiPost("/auth/logout", { refresh_token: refreshToken });
    } catch {
    } finally {
      Object.keys(window.sessionStorage)
        .filter((key) => key.startsWith("fsp-chat-draft:"))
        .forEach((key) => window.sessionStorage.removeItem(key));
      clearSession();
      window.localStorage.removeItem("fsp-offline-demo");
      setOfflineDemo(false);
      setAuthenticated(false);
      setOnboarding(false);
    }
  };

  const toggleCompare = (id: number) => {
    setCompare((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length < 3
          ? [...current, id]
          : current,
    );
  };

  const submitInvite = async () => {
    const salaryMin = Number(inviteSalaryMin.replace(/\D/g, ""));
    const salaryMax = Number(inviteSalaryMax.replace(/\D/g, ""));
    if (!selected.backendId) {
      showNotice("Выберите кандидата из результатов подбора", "error");
      return;
    }
    if (!inviteContact.trim() || salaryMin <= 0 || salaryMax < salaryMin) {
      showNotice("Укажите контакт и корректный диапазон зарплаты", "error");
      return;
    }
    setSent(true);
    try {
      await apiPost("/invitations", {
        candidate_id: selected.backendId,
        need_id: activeNeedId,
        offer_description: offerDescription,
        contact_method: inviteContact.trim(),
        salary_min: salaryMin,
        salary_max: salaryMax,
        salary_tax_type: inviteSalaryType,
        currency: "RUB",
      });
      setInviteOpen(false);
      setInviteDirty(false);
      setInviteDiscardConfirm(false);
      window.dispatchEvent(new Event("fsp-invitations-updated"));
      showNotice(`Приглашение для ${selected.name} отправлено`);
    } catch (requestError) {
      showNotice(requestError instanceof Error ? requestError.message : "Не удалось отправить приглашение", "error");
    } finally {
      setSent(false);
    }
  };

  if (!authenticated) {
    return <AuthScreen onLogin={login} onRegister={register} onVerify={verifyEmail} onDemoLogin={demoLogin} />;
  }

  if (authLoading) {
    return <div className="auth-loading" role="status"><span className="auth-loading__mark" /><strong>Проверяем доступ</strong><span>Подготавливаем ваш кабинет</span></div>;
  }

  if (onboarding) {
    return <CandidateOnboarding onComplete={async (payload) => {
      try {
        await apiPost("/candidates/onboarding", payload);
        window.localStorage.setItem("fsp-onboarding-completed", "true");
        setOnboarding(false);
        showNotice("Профиль создан. Теперь можно подтвердить навыки.");
      } catch (requestError) {
        showNotice(requestError instanceof Error ? requestError.message : "Не удалось сохранить профиль", "error");
      }
    }} />;
  }

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className={`sidebar ${mobileNavOpen ? "sidebar--mobile-open" : ""}`} data-tour="demo-navigation">
        <Logo />
        <div className="workspace-label">{role === "employer" ? "РАБОТОДАТЕЛЬ" : "СОИСКАТЕЛЬ"}</div>
        <nav className="nav" id="mobile-section-menu">
          {nav.map(([icon, item]) => (
            <div className="nav-group-wrap" key={item}>
              {groupLabels[item] && <div className="nav-group-label">{groupLabels[item]}</div>}
              <button
                type="button"
                aria-label={item}
                className={`nav__item ${active === item ? "nav__item--active" : ""}`}
                onClick={() => navigateTo(item)}
              >
                <Icon name={icon} />
                <span>{item}</span>
                {item === "Приглашения" && sidebarPendingInvitations > 0 && <b>{sidebarPendingInvitations}</b>}
              </button>
            </div>
          ))}
        </nav>
        <div className="mobile-nav-shortcuts" aria-label="Быстрая навигация">
          {["Обзор", "Диалоги", "Настройки"].map((item) => {
            const itemIcon = item === "Обзор" ? "grid" : item === "Диалоги" ? "chat" : "settings";
            return <button key={item} type="button" className={active === item ? "active" : ""} onClick={() => navigateTo(item)}><Icon name={itemIcon} size={17} /><span>{item}</span></button>;
          })}
          <button type="button" className={mobileNavOpen ? "active" : ""} aria-expanded={mobileNavOpen} aria-controls="mobile-section-menu" onClick={() => setMobileNavOpen((value) => !value)}><Icon name={mobileNavOpen ? "close" : "menu"} size={17} /><span>{mobileNavOpen ? "Закрыть" : "Разделы"}</span></button>
        </div>
        <div className="sidebar__bottom">
          <div className="company">
            <div className="company__avatar">{sidebarIdentity.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() || (role === "employer" ? "К" : "С")}</div>
            <div>
              <strong>{sidebarIdentity.name || (role === "employer" ? "Компания" : "Кандидат")}</strong>
              <span>{sidebarIdentity.email}</span>
            </div>
            <Icon name="chevron" size={15} />
          </div>
          <button type="button" className="logout-button" onClick={logout}><Icon name="logout" size={16} /><span>Выйти</span></button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar__heading">
            <div className="eyebrow">{currentCopy.eyebrow}</div>
            <div className="page-title">{currentCopy.title}</div>
          </div>
          <div className="topbar__actions">
            {offlineDemo && <span className="demo-mode-badge">ДЕМО · ЛОКАЛЬНЫЕ ДАННЫЕ</span>}
            <div className={`role-switch role-switch--static${offlineDemo ? " role-switch--interactive" : ""}`} data-role={role} role="group" aria-label="Тип аккаунта">
              {offlineDemo ? <>
                <span className="role-switch__thumb" aria-hidden="true" />
                <button type="button" aria-pressed={role === "candidate"} className={role === "candidate" ? "active" : ""} onClick={() => { setRole("candidate"); setActive("Обзор"); window.localStorage.setItem("fsp-role", "candidate"); }}><Icon name="users" size={16} /><span>Кандидат</span></button>
                <button type="button" aria-pressed={role === "employer"} className={role === "employer" ? "active" : ""} onClick={() => { setRole("employer"); setActive("Обзор"); window.localStorage.setItem("fsp-role", "employer"); }}><Icon name="briefcase" size={16} /><span>Компания</span></button>
              </> : <span className="role-switch__identity"><Icon name={role === "employer" ? "briefcase" : "users"} size={16} />{role === "employer" ? "Компания" : "Кандидат"}</span>}
            </div>
            <button
              type="button"
              className="theme-switch"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              aria-label={theme === "light" ? "Включить тёмную тему" : "Включить светлую тему"}
            >
              <span><Icon name={theme === "light" ? "moon" : "sun"} size={16} /></span>
              {theme === "light" ? "Тёмная" : "Светлая"}
            </button>
            <button type="button" className="icon-button" aria-label="Открыть диалоги" onClick={() => navigateTo("Диалоги")}>
              <Icon name="bell" />
            </button>
            {role === "employer" ? (
              <Button variant="outline" onClick={() => setActive("Потребности")}>
                <span className="button-plus">+</span> Новая потребность
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setActive("Профиль")}>Редактировать профиль</Button>
            )}
          </div>
        </header>

        {active === "Диалоги" ? (
          <DialogsScreen
            employer={role === "employer"}
            demoMode={offlineDemo}
            initialTarget={selectedDialogueTarget}
            onClearInitialTarget={() => setSelectedDialogueTarget(null)}
            onNotify={showNotice}
          />
        ) : role === "employer" && active === "Подборка" ? (
          <>
        <section className="need-summary" data-tour="active-need">
          <div className="need-summary__icon">
            <Icon name="briefcase" size={21} />
          </div>
          <div className="need-summary__main">
            <div className="need-summary__top">
              <div>
                <span className="muted-label">АКТИВНАЯ ПОТРЕБНОСТЬ</span>
                <strong>{activeNeed ? `${activeNeed.title} · ${activeNeed.required_grade}` : "Подборка по подтверждённым профилям"}</strong>
              </div>
              {activeNeed ? <span className="status"><i /> Подбор активен</span> : <span className="muted-label">Нет активной потребности</span>}
            </div>
            <div className="need-summary__meta">
              {activeNeed ? (
                <>
                  <span>{activeNeed.specialization}</span>
                  <span>
                    {new Intl.NumberFormat("ru-RU").format(activeNeed.salary_min)}–{new Intl.NumberFormat("ru-RU").format(activeNeed.salary_max)} ₽ ({activeNeed.salary_tax_type === "net" ? "на руки" : "до вычета"})
                  </span>
                  <span>{activeNeed.work_format === "remote" ? "Удалённо" : activeNeed.work_format}</span>
                </>
              ) : (
                <span>Создайте потребность, чтобы получить адресный подбор</span>
              )}
            </div>
          </div>
          <Button variant="ghost" onClick={() => setActive("Потребности")}>Изменить</Button>
        </section>

        <section className="toolbar" data-tour="candidate-filters">
          <div className="search-field">
            <Icon name="search" />
            <input
              aria-label="Поиск по навыкам или имени"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Навык или имя кандидата"
            />
            <kbd>⌘ K</kbd>
          </div>
          <Button
            variant={onlyFsp ? "primary" : "outline"}
            onClick={() => setOnlyFsp((value) => !value)}
          >
            <Icon name="filter" /> Достижения ФСП
          </Button>
          <Button variant="outline" onClick={() => setFiltersOpen((value) => !value)}>
            Фильтры{activeFilterCount > 0 && <> · <span className="filter-count">{activeFilterCount}</span></>}
          </Button>
          <div className="view-switch">
            <button type="button" className={viewMode === "list" ? "active" : ""} onClick={() => setViewMode("list")}><Icon name="grid" /> База</button>
            <button type="button" className={viewMode === "swipe" ? "active" : ""} onClick={() => setViewMode("swipe")}><Icon name="users" /> Свайп</button>
          </div>
          <div className="toolbar__result">
            Найдено <strong>{filtered.length}</strong>
          </div>
        </section>

        {filtersOpen && <section className="matching-filter-panel" aria-label="Фильтры подборки">
          <label>
            <span>Формат работы</span>
            <select className="bank-select" value={filterFormat} onChange={(event) => setFilterFormat(event.target.value)}>
              <option value="">Любой формат</option>
              <option value="Удалённо">Удалённо</option>
              <option value="Гибрид">Гибрид</option>
              <option value="Офис">Офис</option>
            </select>
          </label>
          <label>
            <span>Город</span>
            <select className="bank-select" value={filterCity} onChange={(event) => setFilterCity(event.target.value)}>
              <option value="">Любой город</option>
              {availableCities.map((city) => <option key={city} value={city}>{city}</option>)}
            </select>
          </label>
          {activeFilterCount > 0 && <Button variant="ghost" onClick={() => { setFilterFormat(""); setFilterCity(""); }}>Сбросить</Button>}
        </section>}

        {viewMode === "swipe" && filtered.length > 0 ? (
          <SwipeDeck
            items={filtered}
            onOpen={setResumeCandidate}
            onSelect={(candidate) => {
              if (!compare.includes(candidate.id)) setCompare((current) => [...current.slice(-2), candidate.id]);
            }}
            onNotify={showNotice}
          />
        ) : (
        <div className="content-grid">
          <section className="candidates-list" data-tour="candidate-list">
            <div className="list-head">
              <div>КАНДИДАТЫ ПО РЕЛЕВАНТНОСТИ</div>
              <button type="button">Сначала высокий балл <span>↕</span></button>
            </div>
            {filtered.map((candidate) => (
              <article
                key={candidate.id}
                className={`candidate-card ${
                  selected.id === candidate.id ? "candidate-card--active" : ""
                }`}
                onClick={() => {
                  setSelectedId(candidate.id);
                  setSelectedCandidate(candidate);
                }}
              >
                <div className="candidate-card__top">
                  <div className="avatar">{candidate.initials}</div>
                  <div className="candidate-card__identity">
                    <div className="candidate-card__name">
                      {candidate.name}
                      <span className="verified" title="Профиль подтверждён">
                        <Icon name="check" size={11} />
                      </span>
                    </div>
                    <div>{candidate.role} · {candidate.level}{candidate.verifiedGrade ? " · подтверждён" : " · заявлен"}</div>
                  </div>
                  <div className="match">
                    <strong>{candidate.score} баллов</strong>
                    <span>БАЛЛ ПОДБОРА</span>
                  </div>
                </div>
                <div className="candidate-card__middle">
                  {candidate.backendId && candidate.requestedSkillTests?.length
                    ? <div className="candidate-card__radar-preview"><RequestedSkillRadar skills={candidate.requestedSkillTests} compact /></div>
                    : candidate.backendId && !(offlineDemo && candidate.radar.length)
                    ? <div className="match-explanation">{candidate.summary}</div>
                    : candidate.radar.length > 0
                      ? <div className="candidate-card__radar-preview"><Radar values={candidate.radar} target={candidate.jobRadar} compact description={`Демонстрационное сравнение навыков ${candidate.name} с профилем вакансии`} />{candidate.backendId && <small>ДЕМО-КАРТА · НЕ РЕЗУЛЬТАТ ТЕСТА</small>}</div>
                      : <div className="match-explanation">{candidate.summary}</div>}
                  <div className="candidate-card__facts">
                    <div><span>Опыт</span><strong>{candidate.experience}</strong></div>
                    <div><span>Ожидания</span><strong>{candidate.salary}</strong></div>
                    <div><span>Формат</span><strong>{candidate.format}</strong></div>
                    <div><span>Доверие</span><strong>{candidate.backendId ? "Нет данных" : candidate.trust.toFixed(2).replace(".", ",")}</strong></div>
                  </div>
                </div>
                <div className="tags">
                  {candidate.skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}
                  <span>+{Math.max(0, candidate.skills.length - 4)}</span>
                </div>
                <div className="candidate-card__footer">
                  <span>Обновлён {candidate.updated}</span>
                  {candidate.backendId && candidate.achievementsCount && candidate.achievementsCount > 0 && (
                    <span className="fsp-badge">◆ Демо-данные ФСП: {candidate.achievementsCount}</span>
                  )}
                  <button
                    type="button"
                    className={compare.includes(candidate.id) ? "compare-active" : ""}
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleCompare(candidate.id);
                    }}
                  >
                    <Icon name="compare" size={15} />
                    {compare.includes(candidate.id) ? "Добавлен" : "Сравнить"}
                  </button>
                </div>
              </article>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">{!activeNeed
                ? "Создайте потребность, чтобы увидеть кандидатов в подборке"
                : backendCandidates.length === 0
                ? "Пока нет кандидатов с подтверждённой категорией для этой потребности"
                : "По выбранным параметрам кандидаты не найдены"}</div>
            )}
          </section>

          {filtered.length > 0 && <aside className="profile-panel" data-tour="candidate-profile">
            <div className="profile-panel__head">
              <span>ПРОФИЛЬ КАНДИДАТА</span>
              <button type="button" aria-label="Закрыть профиль"><Icon name="close" /></button>
            </div>
            <div className="profile-hero">
              <div className="avatar avatar--large">{selected.initials}</div>
              <div>
                <div className="profile-hero__name">{selected.name}</div>
                <div>{selected.role}</div>
                <span>{selected.location} · {selected.format}</span>
              </div>
            </div>
            <div className="grade-line">
              <div>
                <span>{selected.verifiedGrade ? "ПОДТВЕРЖДЁННЫЙ УРОВЕНЬ" : "ЗАЯВЛЕННЫЙ УРОВЕНЬ"}</span>
                <strong>{selected.level}</strong>
              </div>
              <div className="grade-line__score">{selected.backendId ? `${selected.score} баллов в подборе` : "06.001 / ур. 6"}</div>
            </div>
            <div className="panel-section">
              <div className="section-title">
                <span>ТЕСТЫ ПО НАВЫКАМ ПОТРЕБНОСТИ</span>
              </div>
              {selected.requestedSkillTests?.length ? <RequestedSkillRadar skills={selected.requestedSkillTests} /> : <p className="feature-description feature-description--left">В потребности не указаны навыки для сравнения.</p>}
            </div>
            <div className="explain-card">
              <div className="explain-card__icon">i</div>
              <div>
                <strong>Почему этот кандидат в подборке</strong>
                <p>{selected.summary}</p>
                <span>{selected.backendId ? "Не указано в профиле" : "Зона роста"}: {selected.gap}</span>
              </div>
            </div>
            <div className="panel-section">
              <div className="section-title">
                <span>УКАЗАННЫЙ СТЕК</span>
              </div>
              <div className="tags tags--large">
                {selected.skills.map((skill) => <span key={skill}>{skill}</span>)}
              </div>
            </div>
            <div className="profile-metrics">
              <div><span>ОЦЕНКА ДОВЕРИЯ</span><strong>Нет данных</strong><small>Не предоставляется matching API</small></div>
              <div><span>ФСП</span><strong>{selected.achievementsCount || "—"}</strong><small>{selected.fspVerified ? "тестовая запись; личность не проверена" : "Нет записи"}</small></div>
              <div><span>АКТУАЛЬНОСТЬ</span><strong>—</strong><small>Нет данных</small></div>
            </div>
            <div className="profile-panel__actions">
              <Button variant="outline" onClick={() => toggleCompare(selected.id)}>
                <Icon name="compare" /> Сравнить
              </Button>
              <Button onClick={openInvite}>
                Пригласить <Icon name="send" />
              </Button>
            </div>
            <div className="privacy-note">
              Контакты кандидата будут доступны после принятия приглашения
            </div>
          </aside>}
        </div>
        )}
          </>
        ) : role === "employer" ? (
          <EmployerScreen
            active={active}
            demoMode={offlineDemo}
            onOpenCandidates={() => navigateTo("Подборка")}
            onOpenResume={setResumeCandidate}
            onNotify={showNotice}
            onNavigate={navigateTo}
            onNeedCreated={(need) => {
              setEmployerNeeds((current) =>
                current.some((item) => item.id === need.id)
                  ? current.map((item) => (item.id === need.id ? need : item))
                  : [need, ...current],
              );
              setActiveNeedId(need.id);
              setSelectedCandidate(null);
              setQuery("");
              setOnlyFsp(false);
              setFilterFormat("");
              setFilterCity("");
              navigateTo("Подборка");
              apiGet<{ candidates: MatchingCandidate[] }>(`/matching/for-need/${need.id}`)
                .then((response) => setBackendCandidates(response.candidates.map((item, index) => mapMatchToCandidate(item, index, offlineDemo))))
                .catch((error: unknown) => showNotice(error instanceof Error ? error.message : "Не удалось сформировать подборку", "error"));
            }}
          />
        ) : (
          <CandidateScreen active={active} onNotify={showNotice} onNavigate={navigateTo} demoMode={offlineDemo} />
        )}
      </main>

      {role === "employer" && active === "Подборка" && compare.length > 0 && (
        <div className="compare-bar">
          <div className="compare-bar__avatars">
            {compare.map((id) => {
              const candidate = backendCandidates.find((item) => item.id === id);
              if (!candidate) return null;
              return <span key={id}>{candidate.initials}</span>;
            })}
          </div>
          <div>
            <strong>{compare.length} из 3 кандидатов</strong>
            <span>Сравните баллы и объяснения совпадений</span>
          </div>
          <Button variant="ghost" onClick={() => setCompare([])}>Очистить</Button>
          <Button
            className={compare.length < 2 ? "button--disabled" : ""}
            onClick={() => compare.length >= 2 && setCompareOpen(true)}
          >
            Сравнить профили
          </Button>
        </div>
      )}

      {role === "employer" && inviteOpen && (
        inviteDiscardConfirm ? (
          <DiscardConfirmation
            title="Закрыть приглашение?"
            message="Черновик предложения не сохранён. Вернитесь к форме или закройте её без отправки."
            onKeepEditing={() => setInviteDiscardConfirm(false)}
            onDiscard={discardInvite}
          />
        ) : <ModalFrame className="modal" labelledBy="invite-dialog-title" onClose={requestCloseInvite}>
            <div className="modal__head">
              <div>
                <span>НОВОЕ ПРИГЛАШЕНИЕ</span>
                <strong id="invite-dialog-title">Пригласить {selected.name}</strong>
              </div>
              <button type="button" aria-label="Закрыть приглашение" onClick={requestCloseInvite}><Icon name="close" /></button>
            </div>
            <div className="invite-person">
              <div className="avatar">{selected.initials}</div>
              <div><strong>{selected.role} · {selected.level}</strong><span>{selected.score} баллов в подборе под потребность</span></div>
            </div>
            <label className="field">
              <span>ОПИСАНИЕ ПРЕДЛОЖЕНИЯ</span>
              <textarea value={offerDescription} onChange={(event) => { setOfferDescription(event.target.value); setInviteDirty(true); }} />
            </label>
            <div className="field-row">
              <label className="field">
                <span>ЗАРПЛАТА ОТ, ₽</span>
                <input inputMode="numeric" value={inviteSalaryMin} onChange={(event) => { setInviteSalaryMin(event.target.value); setInviteDirty(true); }} />
              </label>
              <label className="field">
                <span>ЗАРПЛАТА ДО, ₽</span>
                <input inputMode="numeric" value={inviteSalaryMax} onChange={(event) => { setInviteSalaryMax(event.target.value); setInviteDirty(true); }} />
              </label>
            </div>
            <label className="field">
              <span>КАК УКАЗАНА ЗАРПЛАТА</span>
              <select value={inviteSalaryType} onChange={(event) => { setInviteSalaryType(event.target.value as "gross" | "net"); setInviteDirty(true); }}>
                <option value="gross">До вычета НДФЛ</option>
                <option value="net">На руки</option>
              </select>
            </label>
            <label className="field">
              <span>СПОСОБ СВЯЗИ</span>
              <input value={inviteContact} onChange={(event) => { setInviteContact(event.target.value); setInviteDirty(true); }} placeholder="Email или Telegram" />
            </label>
            <div className="salary-note">
              Зарплатный диапазон и способ расчёта будут показаны кандидату до принятия приглашения.
            </div>
            <div className="modal__actions">
              <Button variant="ghost" onClick={requestCloseInvite}>Отмена</Button>
              <Button disabled={sent} onClick={submitInvite}>
                {sent ? "Отправляем…" : "Отправить приглашение"} <Icon name="send" />
              </Button>
            </div>
          </ModalFrame>
      )}

      {role === "employer" && resumeCandidate && (
        <ResumeModal
          candidate={resumeCandidate}
          onClose={() => setResumeCandidate(null)}
          onInvite={() => {
            setSelectedId(resumeCandidate.id);
            setSelectedCandidate(resumeCandidate);
            setResumeCandidate(null);
            openInvite();
          }}
        />
      )}

      {role === "employer" && compareOpen && (
        <CompareModal
          items={compare
            .map((id) => backendCandidates.find((candidate) => candidate.id === id))
            .filter((candidate): candidate is Candidate => Boolean(candidate))}
          onClose={() => setCompareOpen(false)}
          onOpen={(candidate) => {
            setCompareOpen(false);
            setSelectedId(candidate.id);
            setSelectedCandidate(candidate);
          }}
        />
      )}

      {notice && (
        <div className={`toast toast--${noticeType}`} role={noticeType === "error" ? "alert" : "status"} aria-live={noticeType === "error" ? "assertive" : "polite"}>
          <span className="toast__icon"><Icon name={noticeType === "error" ? "close" : "check"} size={17} /></span>
          <span className="toast__message">{notice}</span>
          <button type="button" className="toast__close" aria-label="Закрыть уведомление" onClick={() => setNotice("")}><Icon name="close" size={15} /></button>
        </div>
      )}
      {demoTourOpen && <DemoTour role={role} onFinish={() => { setDemoTourOpen(false); window.localStorage.setItem("fsp-demo-tour-complete", "true"); }} />}
    </div>
  );
}

export default App;
