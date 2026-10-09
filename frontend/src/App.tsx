import { useEffect, useMemo, useState, type ReactNode } from "react";
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
    radar: [8, 8, 7, 8, 7, 6],
    jobRadar: [8, 8, 8, 7, 7, 7],
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

type MatchingCandidate = {
  candidate_id: string;
  first_name: string;
  last_name: string;
  specialization: string | null;
  verified_grade: string | null;
  declared_grade: string | null;
  city: string | null;
  work_format: string | null;
  fsp_verified: boolean;
  available_from?: string | null;
  trust_score?: number | null;
  trust_flags?: Array<{ label: string; status: "verified" | "review" | "warning"; detail: string }>;
  resume_versions?: Array<{ id: string; label: string; date: string; summary: string }>;
  achievements_count: number;
  skills: string[];
  match_score: number;
  match_explanation: { summary: string; matched_skills: string[]; missing_skills: string[] };
};

type EmployerNeedRecord = {
  id: string;
  title: string;
  specialization: string;
  required_grade: string;
  salary_min: number;
  salary_max: number;
  currency: string;
  work_format: string;
  city: string | null;
  is_active: boolean;
};

type BankFilters = {
  query: string;
  specialization: string;
  grade: string;
  format: string;
  city: string;
  fspOnly: boolean;
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
  declared_grade: string | null;
  verified_grade: string | null;
  work_format: string | null;
  fsp_id: string | null;
  fsp_verified: boolean;
  agreed_152_fz: boolean;
  agreed_publication: boolean;
  visibility_public: boolean;
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
};

type TestResultData = {
  session_id: string;
  specialization: string;
  target_grade: string;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  verified_grade: string | null;
  skill_breakdown: Array<{ topic: string; score: number; max_score: number; percentage: number }>;
  feedback: string;
  suggested_grade: string | null;
};

type TestHistoryData = {
  id: string;
  specialization: string;
  target_grade: string;
  percentage: number;
  passed: boolean;
  status: string;
  created_at: string;
  completed_at: string | null;
};

function mapMatchToCandidate(item: MatchingCandidate, index: number): Candidate {
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
    initials: `${item.first_name[0] ?? "?"}${item.last_name[0] ?? ""}`.toUpperCase(),
    name: `${item.first_name} ${item.last_name}`.trim(),
    role: item.specialization ?? "Специализация не указана",
    level: item.verified_grade ?? item.declared_grade ?? "Не указан",
    score: Math.round(item.match_score),
    salary: "Не указана",
    location: item.city ?? "Не указан",
    format: item.work_format === "remote" ? "Удалённо" : item.work_format === "hybrid" ? "Гибрид" : item.work_format === "office" ? "Офис" : "Не указан",
    experience: "Не указан",
    updated: "Не указано",
    trust: 0,
    skills: item.skills,
    radar: [],
    jobRadar: [],
    achievements: [],
    summary: item.match_explanation.summary,
    gap: item.match_explanation.missing_skills.length
      ? item.match_explanation.missing_skills.join(", ")
      : "Нет данных о пробелах",
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

function Button({
  children,
  variant = "primary",
  onClick,
  className = "",
  type = "button",
  disabled = false,
}: {
  children: ReactNode;
  variant?: "primary" | "ghost" | "outline" | "danger";
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
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
}: {
  values: number[];
  target: number[];
  compact?: boolean;
}) {
  const center = 110;
  const maxR = compact ? 72 : 76;
  const point = (value: number, i: number) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * i) / values.length;
    const radius = (value / 10) * maxR;
    return `${center + Math.cos(angle) * radius},${center + Math.sin(angle) * radius}`;
  };
  const ring = (level: number) =>
    values.map((_, i) => point(level, i)).join(" ");
  const labelPoint = (i: number) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * i) / values.length;
    return {
      x: center + Math.cos(angle) * (maxR + 23),
      y: center + Math.sin(angle) * (maxR + 23),
    };
  };

  return (
    <svg
      className={`radar ${compact ? "radar--compact" : ""}`}
      viewBox="0 0 220 220"
      role="img"
      aria-label="Сравнение компетенций кандидата и вакансии"
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
        points={target.map((v, i) => point(v, i)).join(" ")}
        className="radar__target"
      />
      <polygon
        points={values.map((v, i) => point(v, i)).join(" ")}
        className="radar__value"
      />
      {!compact &&
        labels.map((label, i) => {
          const pos = labelPoint(i);
          return (
            <text
              key={label}
              x={pos.x}
              y={pos.y}
              textAnchor={pos.x < center - 5 ? "end" : pos.x > center + 5 ? "start" : "middle"}
              dominantBaseline="middle"
              className="radar__label"
            >
              {label}
            </text>
          );
        })}
    </svg>
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
  Аналитика: { eyebrow: "КАЧЕСТВО ПОДБОРА", title: "Аналитика" },
  Настройки: { eyebrow: "УПРАВЛЕНИЕ АККАУНТОМ", title: "Настройки" },
  Профиль: { eyebrow: "ЛИЧНЫЙ КАБИНЕТ", title: "Профиль и резюме" },
  Тестирование: { eyebrow: "АДАПТИВНЫЙ ТЕСТ", title: "Тестирование" },
  "Мой грейд": { eyebrow: "ПОДТВЕРЖДЁННЫЕ КОМПЕТЕНЦИИ", title: "Категория и уровень" },
  Задания: { eyebrow: "АКТУАЛЬНОСТЬ ПРОФИЛЯ", title: "Регулярные задания" },
  Вакансии: { eyebrow: "ОТКРЫТЫЕ ПОЗИЦИИ", title: "Вакансии" },
  "Вакансии компании": { eyebrow: "ПУБЛИКАЦИЯ И ОТКЛИКИ", title: "Вакансии компании" },
};

const navHints: Record<string, string> = {
  Обзор: "Сводка по задачам, приглашениям и текущему статусу профиля.",
  Подборка: "Кандидаты, ранжированные по соответствию активной потребности компании.",
  "Банк кандидатов": "Поиск по подтверждённым профилям с фильтрами по навыкам и достижениям.",
  Потребности: "Опишите команду и критерии, по которым система подберёт специалистов.",
  Приглашения: "Отслеживайте предложения и отвечайте на них, не раскрывая контакты заранее.",
  "Вакансии компании": "Управляйте опубликованными позициями и входящими откликами.",
  Аналитика: "Оценивайте качество подбора и динамику ответов по приглашениям.",
  Настройки: "Управляйте профилем компании, приватностью и параметрами аккаунта.",
  Профиль: "Обновляйте опыт и условия работы, которые увидят работодатели.",
  Тестирование: "Подтвердите заявленный уровень адаптивным набором заданий.",
  "Мой грейд": "Смотрите подтверждённый уровень, результаты тестов и карту навыков.",
  Задания: "Решайте короткие кейсы, чтобы поддерживать актуальность навыков.",
  Вакансии: "Ищите позиции с открытой зарплатой и отслеживайте свои отклики.",
};

function MetricCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: boolean;
}) {
  return (
    <div className={`metric-card ${accent ? "metric-card--accent" : ""}`}>
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
  onNavigate: (screen: string) => void;
  demoMode: boolean;
}) {
  const [saved, setSaved] = useState(false);
  const [vacancyEditor, setVacancyEditor] = useState(false);
  const [needs, setNeeds] = useState<EmployerNeedRecord[]>([]);
  const [needTitle, setNeedTitle] = useState("Backend-разработчик");
  const [needSpecialization, setNeedSpecialization] = useState("Backend");
  const [needGrade, setNeedGrade] = useState("middle");
  const [needDescription, setNeedDescription] = useState("");
  const [needSalaryMin, setNeedSalaryMin] = useState("220000");
  const [needSalaryMax, setNeedSalaryMax] = useState("280000");
  const [needCity, setNeedCity] = useState("");
  const [needWorkFormat, setNeedWorkFormat] = useState("remote");
  const [skillWeights, setSkillWeights] = useState<Record<string, number>>({
    "API и интеграции": 5,
    "Базы данных": 5,
    "Язык программирования": 4,
    "CI/CD": 3,
    Тестирование: 3,
    Алгоритмы: 2,
  });
  const [needSaving, setNeedSaving] = useState(false);
  const [companyProfile, setCompanyProfile] = useState<EmployerProfileData | null>(null);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [bankItems, setBankItems] = useState<Candidate[]>([]);
  const [bankFilters, setBankFilters] = useState<BankFilters>(() => {
    const defaults = { query: "", specialization: "", grade: "", format: "", city: "", fspOnly: false };
    try {
      const savedFilters = window.localStorage.getItem("fsp-bank-filters");
      return savedFilters ? { ...defaults, ...JSON.parse(savedFilters) } : defaults;
    } catch {
      return defaults;
    }
  });
  const [bankLoading, setBankLoading] = useState(false);
  const [sentInvitations, setSentInvitations] = useState<Array<{ status: string }>>([]);
  const { query: bankQuery, specialization: bankSpecialization, grade: bankGrade, format: bankFormat, city: bankCity, fspOnly: bankFspOnly } = bankFilters;

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
    if (bankFormat) params.set("work_format", bankFormat);
    if (bankCity.trim()) params.set("city", bankCity.trim());
    if (bankQuery.trim()) params.set("stack", bankQuery.trim());
    setBankLoading(true);
    apiGet<MatchingCandidate[]>(`/matching/search?${params}`)
      .then((items) => setBankItems(items.map(mapMatchToCandidate)))
      .catch((error: unknown) => onNotify(error instanceof Error ? error.message : "Не удалось выполнить поиск", "error"))
      .finally(() => setBankLoading(false));
  }, [active, bankSpecialization, bankGrade, bankFormat, bankCity, bankFspOnly, bankQuery]);

  const visibleBankItems = bankItems.filter((candidate) =>
    `${candidate.name} ${candidate.skills.join(" ")}`.toLowerCase().includes(bankQuery.toLowerCase()),
  );

  const createNeed = async () => {
    const salaryMin = Number(needSalaryMin.replace(/\D/g, ""));
    const salaryMax = Number(needSalaryMax.replace(/\D/g, ""));
    if (salaryMin <= 0 || salaryMax < salaryMin) {
      onNotify("Проверьте зарплатный диапазон", "error");
      return;
    }
    setNeedSaving(true);
    try {
      const created = await apiPost<EmployerNeedRecord>("/needs", {
        title: needTitle,
        specialization: needSpecialization,
        required_grade: needGrade,
        required_skills: [
          ["REST", skillWeights["API и интеграции"]],
          ["PostgreSQL", skillWeights["Базы данных"]],
          ["Python", skillWeights["Язык программирования"]],
          ["Docker", skillWeights["CI/CD"]],
        ].map(([name, weight]) => ({ name: String(name), weight: Number(weight) / 5, required: true })),
        salary_min: salaryMin,
        salary_max: salaryMax,
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
      <div className="page-content">
        <div className="metrics-grid">
          <MetricCard label="АКТИВНЫЕ ПОТРЕБНОСТИ" value={String(needs.filter((need) => need.is_active).length)} detail="По данным компании" accent />
          <MetricCard label="ОТПРАВЛЕНО ПРИГЛАШЕНИЙ" value={String(sentInvitations.length)} detail="По данным API" />
          <MetricCard label="ОЖИДАЮТ ОТВЕТА" value={String(waitingInvitations)} detail={`${acceptedInvitations} принято`} />
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
                <div><strong>{need.title}</strong><span>{need.specialization} · {need.required_grade}</span></div>
                <div><span>Зарплата</span><strong>{new Intl.NumberFormat("ru-RU").format(need.salary_min)}–{new Intl.NumberFormat("ru-RU").format(need.salary_max)} ₽</strong></div>
                <div><span>Формат</span><strong>{need.work_format === "remote" ? "Удалённо" : need.work_format}</strong></div>
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
          <div className="search-field search-field--wide"><Icon name="search" /><input value={bankQuery} onChange={(event) => setBankFilters((current) => ({ ...current, query: event.target.value }))} placeholder="Имя или технология" /></div>
          <select className="bank-select" aria-label="Фильтр специализации" value={bankSpecialization} onChange={(event) => setBankFilters((current) => ({ ...current, specialization: event.target.value }))}><option value="">Все специализации</option>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select>
          <select className="bank-select" aria-label="Фильтр грейда" value={bankGrade} onChange={(event) => setBankFilters((current) => ({ ...current, grade: event.target.value }))}><option value="">Любой грейд</option>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
          <select className="bank-select" aria-label="Фильтр формата работы" value={bankFormat} onChange={(event) => setBankFilters((current) => ({ ...current, format: event.target.value }))}><option value="">Любой формат</option><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select>
          <input className="bank-select" aria-label="Фильтр города" value={bankCity} onChange={(event) => setBankFilters((current) => ({ ...current, city: event.target.value }))} placeholder="Город" />
          <Button variant={bankFspOnly ? "primary" : "outline"} onClick={() => setBankFilters((current) => ({ ...current, fspOnly: !current.fspOnly }))}><Icon name="filter" /> Достижения ФСП</Button>
        </div>
        <div className="table-card">
          <div className="table-summary"><strong>{bankLoading ? "Загрузка кандидатов…" : `${visibleBankItems.length} профилей по фильтрам`}</strong><span>Контакты скрыты до принятия приглашения</span></div>
          <div className="data-table data-table--candidates">
            <div className="data-row data-row--head"><span>КАНДИДАТ</span><span>КАТЕГОРИЯ</span><span>СТЕК</span><span>СОВПАДЕНИЕ</span><span>ФСП</span><span /></div>
            {visibleBankItems.map((candidate) => (
              <div className="data-row" key={candidate.id}>
                <div className="table-person"><div className="avatar">{candidate.initials}</div><div><strong>{candidate.name}</strong><span>{candidate.location}</span></div></div>
                <div><strong>{candidate.role}</strong><span>{candidate.level} · {candidate.verifiedGrade ? "подтверждён" : "заявлен"}</span></div>
                <div className="mini-tags">{candidate.skills.slice(0, 3).map((skill) => <span key={skill}>{skill}</span>)}</div>
                <strong className="green">{candidate.score}%</strong>
                <div><strong>{candidate.fspVerified ? "Проверен" : "Нет"}</strong><span>{candidate.achievementsCount ?? 0} достижений</span></div>
                <Button variant="outline" onClick={() => onOpenResume(candidate)}>Открыть профиль</Button>
              </div>
            ))}
            {!bankLoading && visibleBankItems.length === 0 && <div className="empty-state">По выбранным параметрам кандидаты не найдены</div>}
          </div>
        </div>
      </div>
    );
  }

  if (active === "Потребности") {
    return (
      <div className="page-content">
        <section className="existing-needs" aria-label="Сохранённые потребности">
          {needs.map((need) => <article key={need.id}><div><strong>{need.title}</strong><span>{need.specialization} · {need.required_grade} · {new Intl.NumberFormat("ru-RU").format(need.salary_min)}–{new Intl.NumberFormat("ru-RU").format(need.salary_max)} ₽</span></div><Button variant="outline" onClick={() => onNeedCreated(need)}>Открыть подбор</Button></article>)}
          {needs.length === 0 && <span>Пока нет сохранённых потребностей. Создайте первую, чтобы запустить подбор.</span>}
        </section>
        <div className="steps">
          <div className="active"><b>1</b><span>Описание</span></div>
          <div><b>2</b><span>Оценка важности</span></div>
          <div><b>3</b><span>Публикация</span></div>
        </div>
        <div className="split-layout">
          <section className="feature-card">
            <div className="feature-head"><div><span>ШАГ 1 ИЗ 3</span><strong>Опишите специалиста</strong></div></div>
            <label className="field field--flush"><span>ОПИСАНИЕ ПОТРЕБНОСТИ</span><textarea value={needDescription} onChange={(event) => setNeedDescription(event.target.value)} placeholder="Опишите задачи команды, стек и приоритеты роли." /></label>
            <div className="field-row field-row--flush">
              <label className="field"><span>НАЗВАНИЕ РОЛИ</span><input value={needTitle} onChange={(event) => setNeedTitle(event.target.value)} /></label>
              <label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={needSpecialization} onChange={(event) => setNeedSpecialization(event.target.value)}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            </div>
            <label className="field field--flush"><span>ТРЕБУЕМЫЙ УРОВЕНЬ</span><select value={needGrade} onChange={(event) => setNeedGrade(event.target.value)}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <div className="field-row field-row--flush">
              <label className="field"><span>ЗАРПЛАТА ОТ, ₽</span><input inputMode="numeric" value={needSalaryMin} onChange={(event) => setNeedSalaryMin(event.target.value)} /></label>
              <label className="field"><span>ЗАРПЛАТА ДО, ₽</span><input inputMode="numeric" value={needSalaryMax} onChange={(event) => setNeedSalaryMax(event.target.value)} /></label>
            </div>
            <div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={needCity} onChange={(event) => setNeedCity(event.target.value)} placeholder="Любой город" /></label><label className="field"><span>ФОРМАТ</span><select value={needWorkFormat} onChange={(event) => setNeedWorkFormat(event.target.value)}><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select></label></div>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>ТРЕБОВАНИЯ ДЛЯ ПОДБОРА</span><strong>Важность навыков — от 1 до 5</strong></div></div>
                <p className="feature-description feature-description--left">Чем выше значение, тем сильнее этот навык влияет на позицию кандидата в подборке.</p>
                <div className="skill-weights">
                  {[
                    ["API и интеграции", 5],
                    ["Базы данных", 5],
                    ["Язык программирования", 4],
                    ["CI/CD", 3],
                    ["Тестирование", 3],
                    ["Алгоритмы", 2],
                  ].map(([skill]) => (
                    <div key={String(skill)}><span>{skill}</span><input aria-label={`Вес ${skill}`} type="range" min="1" max="5" value={skillWeights[String(skill)]} onChange={(event) => setSkillWeights((current) => ({ ...current, [String(skill)]: Number(event.target.value) }))} /><strong>{skillWeights[String(skill)]}/5</strong></div>
                  ))}
                </div>
                <p className="feature-description feature-description--left">Требования и веса будут сохранены в потребности; подбор покажет кандидатов с объяснением совпадений.</p>
                <Button disabled={needSaving} className={needSaving ? "button--disabled" : ""} onClick={() => void createNeed()}>{needSaving ? "Сохраняем…" : "Сохранить и запустить подбор"} <Icon name="chevron" /></Button>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Приглашения") {
    return <Invitations employer />;
  }

  if (!demoMode && active === "Вакансии компании") {
    return <div className="page-content"><section className="feature-card"><div className="feature-head"><div><span>ВАКАНСИИ</span><strong>Публикация пока недоступна</strong></div></div><p className="feature-description feature-description--left">В backend нет API для публикации вакансий и обработки откликов. Для адресного подбора создайте потребность и отправьте кандидату приглашение.</p><Button onClick={() => onNavigate("Потребности")}>Открыть потребности</Button></section></div>;
  }

  if (!demoMode && active === "Аналитика") {
    return <div className="page-content"><section className="feature-card"><div className="feature-head"><div><span>АНАЛИТИКА</span><strong>Метрики ещё не подключены</strong></div></div><p className="feature-description feature-description--left">Backend не предоставляет endpoint аналитики. Числа по конверсии, качеству Top-3 и динамике приглашений пока не рассчитываются.</p></section></div>;
  }

  if (active === "Аналитика" && demoMode) {
    const scheduled = bankItems.filter((candidate) => candidate.availableFrom).sort((left, right) => (left.availableFrom ?? "").localeCompare(right.availableFrom ?? ""));
    const averageScore = bankItems.length ? Math.round(bankItems.reduce((total, candidate) => total + candidate.score, 0) / bankItems.length) : 0;
    const confirmedDates = scheduled.length;
    return (
      <div className="page-content">
        <div className="demo-banner">Сроки выхода и совпадения рассчитаны на локальных demo-профилях. У production API нет поля available_from.</div>
        <div className="metrics-grid"><MetricCard label="КАНДИДАТОВ В ПОДБОРКЕ" value={String(bankItems.length)} detail="Текущий demo-набор" accent /><MetricCard label="СРЕДНЕЕ СОВПАДЕНИЕ" value={`${averageScore}%`} detail="Среднее по текущим профилям" /><MetricCard label="ДАТА ВЫХОДА УКАЗАНА" value={`${confirmedDates} / ${bankItems.length}`} detail="Из локального demo-набора" /></div>
        <section className="feature-card feature-card--wide">
          <div className="feature-head"><div><span>ДОСТУПНОСТЬ КАНДИДАТОВ</span><strong>Планируемые даты выхода</strong></div><Button variant="outline" onClick={() => onNavigate("Подборка")}>Открыть подборку</Button></div>
          <div className="start-dates">{scheduled.map((candidate, index) => <div key={candidate.backendId}><b>{new Date(`${candidate.availableFrom}T00:00:00`).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}</b><i className={index === 0 ? "active" : ""} /><div><strong>{candidate.name}</strong><span>{candidate.role} · {candidate.level} · совпадение {candidate.score}%</span></div><em>{candidate.availableFrom ? "Готов к выходу" : "Дата не указана"}</em></div>)}</div>
          {!scheduled.length && <div className="empty-state">В профилях пока нет дат готовности</div>}
        </section>
      </div>
    );
  }

  if (active === "Вакансии компании") {
    return (
      <div className="page-content">
        <div className="vacancy-head"><div><strong>Вакансии NovaTech</strong><span>Зарплатный диапазон обязателен для публикации</span></div><Button onClick={() => setVacancyEditor(!vacancyEditor)}><span className="button-plus">+</span> Создать вакансию</Button></div>
        {vacancyEditor && (
          <section className="feature-card vacancy-editor">
            <div className="feature-head"><div><span>НОВАЯ ВАКАНСИЯ</span><strong>Основные условия</strong></div><Button variant="ghost" onClick={() => setVacancyEditor(false)}>Закрыть</Button></div>
            <div className="field-row field-row--flush"><label className="field"><span>НАЗВАНИЕ *</span><input defaultValue="Backend-разработчик" /></label><label className="field"><span>СПЕЦИАЛИЗАЦИЯ *</span><select>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label></div>
            <div className="field-row field-row--flush"><label className="field"><span>УРОВЕНЬ *</span><select><option>Middle</option><option>Senior</option></select></label><label className="field"><span>ФОРМАТ *</span><select><option>Удалённо</option><option>Гибрид</option><option>Офис</option></select></label></div>
            <div className="field-row field-row--flush"><label className="field"><span>ЗАРПЛАТА ОТ, ₽ *</span><input defaultValue="220 000" /></label><label className="field"><span>ЗАРПЛАТА ДО, ₽ *</span><input defaultValue="280 000" /></label></div>
            <label className="field field--flush"><span>ОПИСАНИЕ *</span><textarea defaultValue="Разработка API финансовой платформы, работа с PostgreSQL и сервисами обработки событий." /></label>
            <div className="parsed-tags"><span>СТЕК</span><b>Python</b><b>FastAPI</b><b>PostgreSQL</b><b>Docker</b></div>
            <div className="modal__actions"><Button variant="outline">Сохранить черновик</Button><Button onClick={() => setVacancyEditor(false)}>Опубликовать вакансию</Button></div>
          </section>
        )}
        <div className="vacancy-tabs"><button type="button" className="active">Опубликованы · 3</button><button type="button">Черновики · 1</button><button type="button">Все отклики · 14</button></div>
        <div className="vacancy-management">
          {[
            ["Backend-разработчик", "Middle", "220–280 тыс. ₽", "8 откликов", "Опубликована"],
            ["DevOps-инженер", "Middle", "230–300 тыс. ₽", "4 отклика", "Опубликована"],
            ["Frontend-разработчик", "Senior", "260–340 тыс. ₽", "2 отклика", "Приостановлена"],
          ].map((item) => <article key={item[0]}><div className="need-row__icon"><Icon name="briefcase" /></div><div><strong>{item[0]}</strong><span>{item[1]} · {item[2]}</span></div><b>{item[3]}</b><em>{item[4]}</em><Button variant="outline">Редактировать</Button><Button variant="ghost">Отклики</Button></article>)}
        </div>
        <section className="feature-card employer-task-create"><div><span>РЕГУЛЯРНАЯ ЗАДАЧА</span><strong>Проверьте кандидатов на реальном кейсе</strong><p>Создайте короткую задачу — результат будет виден только вашей компании и добавит свежий сигнал в профиль.</p></div><Button variant="outline">Создать задачу</Button></section>
      </div>
    );
  }

  if (active === "Аналитика") {
    return (
      <div className="page-content">
        <div className="metrics-grid">
          <MetricCard label="ТОЧНОСТЬ TOP-3" value="87%" detail="Цель ≥ 80%" accent />
          <MetricCard label="СРЕДНЕЕ СОВПАДЕНИЕ" value="82%" detail="+6% за месяц" />
          <MetricCard label="ДО ОТВЕТА КАНДИДАТА" value="18 ч" detail="-4 часа за месяц" />
          <MetricCard label="ПРИНЯТЫЕ ПРИГЛАШЕНИЯ" value="50%" detail="8 из 16" />
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

function Invitations({ employer = false, onNotify }: { employer?: boolean; onNotify?: (message: string, type?: "success" | "error") => void }) {
  const [items, setItems] = useState<Array<{
    id: string;
    company_name: string;
    candidate_name: string;
    need_title: string | null;
    offer_description: string;
    contact_method: string;
    salary_min: number;
    salary_max: number;
    currency: string;
    status: string;
    candidate_reply: string | null;
    candidate_contacts: { email: string; phone: string | null; telegram: string | null } | null;
  }>>([]);
  const [filter, setFilter] = useState("Все");
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    apiGet<typeof items>(employer ? "/invitations/sent" : "/invitations/my")
      .then(setItems)
      .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить приглашения"))
      .finally(() => setLoading(false));
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
            <article className="invitation-card" key={item.id}>
              <div className="invitation-logo">{(employer ? item.candidate_name : item.company_name).slice(0, 2).toUpperCase()}</div>
              <div className="invitation-main">
                <span>{employer ? "КАНДИДАТ" : "ПРИГЛАШЕНИЕ ОТ КОМПАНИИ"}</span>
                <strong>{employer ? item.candidate_name : item.company_name}</strong>
                <p>{item.need_title ?? "Предложение о работе"}</p>
                <p className="invitation-description">{item.offer_description}</p>
                <div className="tags"><span>{money(item.salary_min)}–{money(item.salary_max)} ₽</span><span>Связь: {item.contact_method}</span></div>
                {item.candidate_reply && <p className="invitation-description">Ответ: {item.candidate_reply}</p>}
              </div>
              <div className="invitation-status"><span className={`status-pill status-pill--${item.status === "accepted" ? "green" : "violet"}`}>{statusLabels[item.status] ?? item.status}</span></div>
              {!employer && ["sent", "viewed"].includes(item.status) && <div className="invitation-actions"><Button variant="ghost" disabled={pendingId === item.id} onClick={() => actOnInvitation(item.id, "reject")}>Отклонить</Button><Button disabled={pendingId === item.id} onClick={() => actOnInvitation(item.id, "accept")}>{pendingId === item.id ? "Сохраняем…" : "Принять"}</Button></div>}
              {employer && item.candidate_contacts && <div className="contact-box"><span>КОНТАКТ КАНДИДАТА</span><strong>{item.candidate_contacts.email}</strong>{item.candidate_contacts.telegram && <small>{item.candidate_contacts.telegram}</small>}{item.candidate_contacts.phone && <small>{item.candidate_contacts.phone}</small>}</div>}
              {!employer && item.status === "accepted" && <div className="contact-box"><span>КОНТАКТ КОМПАНИИ</span><strong>{item.contact_method}</strong></div>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function CandidateScreen({ active, onNotify, onNavigate, demoMode }: { active: string; onNotify: (message: string, type?: "success" | "error") => void; onNavigate: (screen: string) => void; demoMode: boolean }) {
  const [testPurpose, setTestPurpose] = useState<"grade" | "fsp-olympiad">("grade");
  const [testStarted, setTestStarted] = useState(false);
  const [question, setQuestion] = useState(0);
  const [answer, setAnswer] = useState("");
  const [selectedAnswers, setSelectedAnswers] = useState<string[]>([]);
  const [submittedAnswers, setSubmittedAnswers] = useState<Array<{ question_id: string; selected_answers: string[] }>>([]);
  const [testSession, setTestSession] = useState<TestStartData | null>(null);
  const [testResult, setTestResult] = useState<TestResultData | null>(null);
  const [testHistory, setTestHistory] = useState<TestHistoryData[]>([]);
  const [testStarting, setTestStarting] = useState(false);
  const [testSubmitting, setTestSubmitting] = useState(false);
  const [testDone, setTestDone] = useState(false);
  const [taskDone, setTaskDone] = useState(false);
  const [saved, setSaved] = useState(false);
  const [applied, setApplied] = useState<number[]>([]);
  const [profile, setProfile] = useState<CandidateProfileData | null>(null);
  const [candidateInvitations, setCandidateInvitations] = useState<Array<{ status: string }>>([]);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
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
    if (active !== "Профиль" && active !== "Настройки" && active !== "Мой грейд") return;
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
        declared_grade: profile.declared_grade,
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
    if (!file.name.toLowerCase().endsWith(".pdf") || file.size > 10 * 1024 * 1024) {
      onNotify("Выберите PDF-файл размером не больше 10 МБ");
      return;
    }
    const body = new FormData();
    body.append("file", file);
    try {
      const parsed = await apiRequest<ParsedResume>("/candidate/resume/upload", { method: "POST", body });
      setParsedResume(parsed);
      setProfile((current) => current ? {
        ...current,
        first_name: parsed.first_name ?? current.first_name,
        last_name: parsed.last_name ?? current.last_name,
        phone: parsed.phone ?? current.phone,
        telegram: parsed.telegram ?? current.telegram,
        city: parsed.city ?? current.city,
        specialization: parsed.specialization ?? current.specialization,
        declared_grade: parsed.suggested_grade?.toLowerCase() ?? current.declared_grade,
      } : current);
      onNotify("Резюме распознано. Проверьте поля и сохраните профиль.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось распознать резюме", "error");
    }
  };

  const downloadProfilePdf = async () => {
    try {
      const pdf = await apiGet<Blob>("/candidate/profile/pdf");
      const url = URL.createObjectURL(pdf);
      const link = document.createElement("a");
      link.href = url;
      link.download = "fsp_candidate_profile.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось скачать PDF-профиль", "error");
    }
  };

  const linkFspId = async () => {
    if (!fspInput.trim()) return;
    try {
      const updated = await apiPost<CandidateProfileData>("/candidate/link-fsp", { fsp_id: fspInput.trim() });
      setProfile(updated);
      onNotify(updated.fsp_verified ? "ФСП ID подтверждён" : "ФСП ID не найден. Проверьте номер и попробуйте ещё раз.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось проверить ФСП ID", "error");
    }
  };

  const startAdaptiveTest = async () => {
    setTestStarting(true);
    try {
      const session = await apiPost<TestStartData>(testPurpose === "fsp-olympiad" ? "/fsp/olympiad/start" : "/testing/start", {});
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
      setTestSubmitting(true);
      try {
        const submitPath = testPurpose === "fsp-olympiad"
          ? `/fsp/olympiad/${testSession.session_id}/submit`
          : `/testing/${testSession.session_id}/submit`;
        const result = await apiPost<TestResultData>(submitPath, { answers });
        setTestResult(result);
        setTestDone(true);
        setTestStarted(false);
        if (testPurpose === "grade") apiGet<TestHistoryData[]>("/testing/history").then(setTestHistory).catch(() => undefined);
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
          <MetricCard label="ПРИГЛАШЕНИЯ" value={String(candidateInvitations.length)} detail={`${pendingInvitations} ждут ответа`} accent />
          <MetricCard label="ЗАЯВЛЕННЫЙ УРОВЕНЬ" value={profile?.declared_grade ?? "—"} detail="Из профиля" />
          <MetricCard label="ПОДТВЕРЖДЁННЫЙ УРОВЕНЬ" value={profile?.verified_grade ?? "—"} detail={profile?.verified_grade ? "Тест пройден" : "Можно пройти тест"} />
          <MetricCard label="ФСП ID" value={profile?.fsp_verified ? "Проверен" : "Не привязан"} detail={profile?.fsp_id ?? ""} />
        </div>
        <div className="dashboard-grid">
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
            <div className="feature-head"><div><span>ФСП · ПРАКТИЧЕСКИЙ ТРЕК</span><strong>{profile?.fsp_verified ? "Участник подтверждён" : "Проверьте навыки на олимпиаде"}</strong></div><div className="fsp-symbol">◆</div></div>
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
            <label className="field field--flush"><span>О СЕБЕ</span><textarea value={profile?.bio ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, bio: event.target.value } : current)} /></label>
            <div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={profile?.city ?? ""} onChange={(event) => setProfile((current) => current ? { ...current, city: event.target.value } : current)} /></label><label className="field"><span>ФОРМАТ РАБОТЫ</span><select value={profile?.work_format ?? "remote"} onChange={(event) => setProfile((current) => current ? { ...current, work_format: event.target.value } : current)}><option value="remote">Удалённо</option><option value="hybrid">Гибрид</option><option value="office">Офис</option></select></label></div>
            <Button disabled={!profile || profileSaving} className={profileSaving ? "button--disabled" : ""} onClick={() => void saveCandidateProfile()}>{profileSaving ? "Сохраняем…" : "Сохранить профиль"}</Button>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>РЕЗЮМЕ</span><strong>Опыт и документы</strong></div></div>
            <div className="upload-box"><Icon name="briefcase" size={26} /><strong>Загрузить PDF-резюме</strong><span>До 10 МБ. Распознанные значения можно проверить перед сохранением.</span><input className="resume-file-input" type="file" accept="application/pdf,.pdf" onChange={(event) => void uploadResume(event.target.files?.[0])} /></div>
            {parsedResume && <div className="resume-entry"><span>РАСПОЗНАННЫЕ ДАННЫЕ · ПРОВЕРЬТЕ ПЕРЕД СОХРАНЕНИЕМ</span><strong>{parsedResume.extracted_skills.length ? parsedResume.extracted_skills.join(" · ") : "Навыки не распознаны"}</strong><p>{parsedResume.text_preview.slice(0, 320) || "Текстовое превью недоступно."}</p></div>}
            <Button variant="outline" onClick={() => void downloadProfilePdf()}>Скачать PDF-профиль</Button>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Тестирование") {
    if (testDone) {
      return <div className="page-content"><div className="test-result"><div className="result-check"><Icon name={testResult?.passed ? "check" : "close"} size={34} /></div><span>{testPurpose === "fsp-olympiad" ? "ОЛИМПИАДА ФСП · РЕЗУЛЬТАТ" : "РЕЗУЛЬТАТ ТЕСТА"}</span><strong>{testPurpose === "fsp-olympiad" ? "Проверка навыков завершена" : testResult?.passed ? `Подтверждён ${testResult.verified_grade ?? testResult.target_grade}` : "Уровень не подтверждён"}</strong><p>{testResult?.feedback}</p><div className="result-score"><b>{testResult?.percentage ?? 0}%</b><span>{testResult?.score ?? 0} из {testResult?.max_score ?? 0} баллов</span></div><div className="skill-table">{testResult?.skill_breakdown.map((skill) => <div key={skill.topic}><span>{skill.topic}</span><Progress value={skill.percentage} /><strong>{skill.percentage}%</strong></div>)}</div>{testPurpose === "fsp-olympiad" && <p>Результаты тем сохранены в локальном demo-профиле.</p>}{testResult?.suggested_grade && <p>Рекомендуемый следующий уровень: {testResult.suggested_grade}</p>}<Button onClick={() => { setTestDone(false); setTestResult(null); }}>К тестированию</Button></div></div>;
    }
    if (testStarted) {
      const currentQuestion = testSession?.questions[question];
      if (!currentQuestion) return <div className="page-content"><div className="empty-state">Загружаем задание…</div></div>;
      return (
        <div className="test-shell">
          <div className="test-top"><div><span>{testPurpose === "fsp-olympiad" ? "ОЛИМПИАДА ФСП" : "ПОДТВЕРЖДЕНИЕ ГРЕЙДА"} · {testSession?.specialization} · {testSession?.target_grade}</span><strong>Задание {question + 1} из {testSession?.total_questions}</strong></div></div>
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
    return (
      <div className="page-content">
        <div className="test-intro">
          <div className="test-intro__graphic"><span>&lt;/&gt;</span><i /><b /></div>
          <span>{testPurpose === "fsp-olympiad" ? "ОЛИМПИАДА ФСП" : "ПОДТВЕРЖДЕНИЕ УРОВНЯ"}</span><strong>{testPurpose === "fsp-olympiad" ? "Практические задачи по навыкам" : "Тест по данным вашего профиля"}</strong><p>{testPurpose === "fsp-olympiad" ? "Проверьте практические навыки в задачах по темам. В локальном demo результат сохранится в текущей сессии." : "Набор заданий и целевой уровень будут сформированы сервером. Результат появится здесь после отправки ответов."}</p>
          <div className="notice-box">Для подтверждения категории необходимо набрать проходной балл. Неудачная попытка не понижает заявленный уровень. {TEST_AVAILABILITY_HINT} Если пара «специализация + грейд» не поддерживается, сервер вернёт явную ошибку — вопросы другого направления не подставляются.</div>
          <div className="assessment-mode" role="group" aria-label="Режим проверки"><button type="button" className={testPurpose === "grade" ? "active" : ""} onClick={() => setTestPurpose("grade")}>Тест уровня</button><button type="button" className={testPurpose === "fsp-olympiad" ? "active" : ""} onClick={() => setTestPurpose("fsp-olympiad")}>Олимпиада ФСП</button></div>
          <div className="test-choice-actions"><Button disabled={testStarting} onClick={() => void startAdaptiveTest()}>{testStarting ? "Подготавливаем…" : testPurpose === "fsp-olympiad" ? "Начать олимпиаду" : "Начать тестирование"} <Icon name="chevron" /></Button><span>Достижения ФСП можно связать в настройках, дипломы передать через локальный demo-процесс.</span></div>
        </div>
      </div>
    );
  }

  if (active === "Мой грейд") {
    return (
      <div className="page-content">
        <div className="grade-hero"><div><span>{profile?.specialization ?? "ПРОФИЛЬ КАНДИДАТА"}</span><strong>{profile?.verified_grade ? `Подтверждён ${profile.verified_grade}` : "Уровень не подтверждён"}</strong><p>Заявленный уровень: {profile?.declared_grade ?? "не указан"}</p></div><div className="grade-stamp"><Icon name={profile?.verified_grade ? "check" : "chart"} /><span>{profile?.verified_grade ? "ПОДТВЕРЖДЁН" : "НУЖЕН ТЕСТ"}</span><strong>{profile?.fsp_verified ? "ФСП проверен" : ""}</strong></div></div>
        <div className="dashboard-grid">
          <section className="feature-card feature-card--wide"><div className="feature-head"><div><span>ИСТОРИЯ ТЕСТОВ</span><strong>Результаты подтверждения</strong></div><Button onClick={() => onNavigate("Тестирование")}>Пройти тест</Button></div>{testHistory.length ? <div className="history-table history-table--tests">{testHistory.map((item) => <div key={item.id}><span>{new Date(item.created_at).toLocaleDateString("ru-RU")}</span><strong>{item.specialization} · {item.target_grade}</strong><b>{item.passed ? "Подтверждён" : item.status === "completed" ? "Не пройден" : "В процессе"}</b><em>{item.percentage}%</em></div>)}</div> : <div className="empty-state">Истории тестирования пока нет</div>}</section>
          <section className="feature-card"><div className="feature-head"><div><span>ПРОФИЛЬ</span><strong>Текущая категория</strong></div></div><div className="profile-status-row"><span>Специализация</span><strong>{profile?.specialization ?? "Не указана"}</strong></div><div className="profile-status-row"><span>Заявленный уровень</span><strong>{profile?.declared_grade ?? "Не указан"}</strong></div><div className="profile-status-row"><span>Подтверждённый уровень</span><strong>{profile?.verified_grade ?? "Нет"}</strong></div></section>
        </div>
      </div>
    );
  }

  if (!demoMode && active === "Задания") {
    return (
      <div className="page-content">
        <div className="task-hero"><div><span>АКТУАЛЬНОСТЬ ПРОФИЛЯ</span><strong>Профиль активен</strong><p>Последняя активность 2 дня назад. Баллы радара не затухают.</p></div><div className="recency-scale"><span className="active">Активен</span><span>Недавно активен</span><span>Устаревает</span><span>Неактивен</span></div></div>
        <div className="task-list">
          <article className="task-card"><div className="task-card__type">&lt;/&gt;</div><div><span>ПЛАТФОРМЕННАЯ · 10–15 МИН</span><strong>Оптимизация SQL-запроса</strong><p>Найдите причину медленного выполнения запроса и предложите индексы.</p><div className="tags"><span>Базы данных</span><span>+0,4 к карте навыков</span></div></div><div className="task-card__action"><span>до 24 мая</span><Button onClick={() => { setTaskDone(true); onNotify("Задание открыто — таймер начнётся после подтверждения"); }}>{taskDone ? "Выполнено" : "Начать"}</Button></div></article>
          <article className="task-card"><div className="task-card__type task-card__type--red"><Icon name="briefcase" /></div><div><span>ОТ NOVATECH · 10 МИН</span><strong>Code review обработчика API</strong><p>Найдите проблемы безопасности и производительности в сниппете.</p><div className="tags"><span>API</span><span>Code Quality</span></div></div><div className="task-card__action"><span>до 27 мая</span><Button variant="outline">Открыть</Button></div></article>
        </div>
        <section className="feature-card"><div className="feature-head"><div><span>ИСТОРИЯ</span><strong>Решённые задания</strong></div></div><div className="history-table"><div><span>12 мая</span><strong>Debug-кейс: очередь сообщений</strong><b>+0.3 API</b><em>9/10</em></div><div><span>28 апреля</span><strong>Архитектурное эссе</strong><b>+0.4 Architecture</b><em>8/10</em></div></div></section>
      </div>
    );
  }

  if (active === "Приглашения") return <Invitations onNotify={onNotify} />;

  if (!demoMode && active === "Вакансии") {
    return <div className="page-content"><section className="feature-card"><div className="feature-head"><div><span>ВАКАНСИИ</span><strong>Каталог пока недоступен</strong></div></div><p className="feature-description feature-description--left">Backend пока не предоставляет каталог вакансий или API откликов. Приглашения от компаний доступны в соответствующем разделе.</p><Button variant="outline" onClick={() => onNavigate("Приглашения")}>Открыть приглашения</Button></section></div>;
  }

  if (active === "Задания") {
    return <div className="page-content"><section className="feature-card"><div className="feature-head"><div><span>ЗАДАНИЯ</span><strong>Короткие кейсы ещё не подключены</strong></div></div><p className="feature-description feature-description--left">Backend пока не предоставляет выдачу или сдачу регулярных заданий. Подтвердить категорию можно через тестирование.</p><Button onClick={() => onNavigate("Тестирование")}>Перейти к тестированию</Button></section></div>;
  }

  if (active === "Вакансии") {
    return (
      <div className="page-content">
        <div className="tab-row"><button type="button" className="active">Все вакансии</button><button type="button">Мои отклики <span>{applied.length}</span></button><button type="button">Просмотрены</button><button type="button">Приняты</button></div>
        {applied.length > 0 && <div className="application-status"><Icon name="check" /><div><strong>Последний отклик отправлен</strong><span>Статус: отправлен · работодатель ещё не просмотрел профиль</span></div><Button variant="ghost">Все статусы</Button></div>}
        <div className="bank-toolbar"><div className="search-field search-field--wide"><Icon name="search" /><input placeholder="Название, компания или технология" /></div><Button variant="outline"><Icon name="filter" /> Фильтры</Button></div>
        <div className="jobs-grid">
          {[
            ["Backend-разработчик", "NovaTech", "220–280 тыс. ₽", "94%", ["Python", "FastAPI", "PostgreSQL"]],
            ["Python Developer", "Ozon Tech", "240–310 тыс. ₽", "89%", ["Python", "Kafka", "Kubernetes"]],
            ["Software Engineer", "Яндекс", "250–330 тыс. ₽", "86%", ["Go", "gRPC", "PostgreSQL"]],
            ["Backend Engineer", "Т-Банк", "230–300 тыс. ₽", "83%", ["Java", "Kafka", "Kubernetes"]],
          ].map((job, index) => (
            <article className="job-card" key={String(job[0]) + index}><div className="job-card__top"><div className="invitation-logo">{String(job[1]).slice(0,2).toUpperCase()}</div><div><strong>{job[0]}</strong><span>{job[1]}</span></div><b>Совпадение {job[3]}</b></div><div className="job-salary">{job[2]}</div><p>{["Развитие API финансовой платформы и сервисов обработки транзакций.", "Разработка систем логистики и обработки событий для миллионов заказов.", "Создание сервисов поиска и рекомендаций в распределённой инфраструктуре.", "Развитие банковской платформы и интеграций с внутренними продуктами."][index]}</p><div className="tags">{(job[4] as string[]).map((tag) => <span key={tag}>{tag}</span>)}</div><div className="job-card__footer"><span>Уровень Middle · Москва</span><Button variant={applied.includes(index) ? "outline" : "primary"} onClick={() => { if (!applied.includes(index)) { setApplied([...applied, index]); onNotify(`Отклик в ${job[1]} отправлен`); } }}>{applied.includes(index) ? "Отклик отправлен" : "Откликнуться"}</Button></div></article>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="settings-layout">
        <section className="feature-card"><div className="feature-head"><div><span>ПРИВАТНОСТЬ</span><strong>Кому виден профиль</strong></div></div><div className="profile-status-row"><span>Согласие на обработку данных</span><strong>{profile?.agreed_152_fz ? "Сохранено" : "Не предоставлено"}</strong></div><div className="profile-status-row"><span>Согласие на OSINT-проверку</span><strong>{profile?.agreed_osint ? "Сохранено" : "Не предоставлено"}</strong></div><label className="consent-large"><input type="checkbox" checked={profile?.agreed_publication ?? false} onChange={(event) => setProfile((current) => current ? { ...current, agreed_publication: event.target.checked, visibility_public: event.target.checked ? current.visibility_public : false } : current)} /><span>Разрешаю показывать мой профиль работодателям</span></label><label className="consent-large"><input type="checkbox" checked={profile?.visibility_public ?? false} disabled={!profile?.agreed_publication} onChange={(event) => setProfile((current) => current ? { ...current, visibility_public: event.target.checked } : current)} /><span>Показывать профиль в поиске и подборке</span></label><p className="feature-description feature-description--left">Без согласия на публикацию профиль остаётся скрытым. Видимость можно выключить в любой момент.</p><Button disabled={!profile || profileSaving} onClick={() => void saveCandidatePrivacy()}>{profileSaving ? "Сохраняем…" : "Сохранить настройки"}</Button></section>
        <section className="feature-card"><div className="feature-head"><div><span>ИНТЕГРАЦИИ</span><strong>Данные ФСП</strong></div></div><label className="field field--flush"><span>ФСП ID</span><input value={fspInput} onChange={(event) => setFspInput(event.target.value)} placeholder="Например, FSP-77-001" /></label><div className="integration-card"><div className="fsp-symbol">◆</div><div><strong>{profile?.fsp_verified ? "ID подтверждён" : "ID не подтверждён"}</strong><span>{profile?.fsp_id ?? "Не привязан"}</span></div><Button variant="outline" disabled={!fspInput.trim()} onClick={() => void linkFspId()}>Проверить</Button></div></section>
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
      <div className="modal-backdrop" onMouseDown={onClose}>
        <div className="resume-modal" onMouseDown={(event) => event.stopPropagation()}>
          <div className="resume-modal__top"><span>ПРОФИЛЬ ИЗ БАНКА КАНДИДАТОВ</span><button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть профиль"><Icon name="close" /></button></div>
          <div className="resume-cover">
            <div className="resume-avatar">{candidate.initials}</div>
            <div className="resume-cover__main"><div className="resume-name">{candidate.name}</div><strong>{candidate.role} · {candidate.level}</strong><span>{candidate.location} · {candidate.format}</span><span>Готов выйти: {candidate.availableFrom ? new Date(`${candidate.availableFrom}T00:00:00`).toLocaleDateString("ru-RU") : "дата не указана"}</span></div>
            <div className="resume-match"><span>Совпадение</span><strong>{candidate.score}%</strong></div>
          </div>
          <div className="resume-versions resume-versions--backend">
            <span>ВЕРСИИ РЕЗЮМЕ</span>
            {candidate.resumeVersions?.length ? candidate.resumeVersions.map((item) => <button type="button" key={item.id} className={version === item.id ? "active" : ""} onClick={() => setVersion(item.id)}>{item.label} · {new Date(`${item.date}T00:00:00`).toLocaleDateString("ru-RU")}</button>) : <small>История версий пока не передаётся backend.</small>}
            <p>{versionNote}</p>
          </div>
          <div className="resume-layout">
            <div className="resume-main">
              <section className="resume-section"><span>ПОЧЕМУ В ПОДБОРКЕ</span><p>{candidate.summary}</p></section>
              <section className="resume-section"><span>СТЕК</span><div className="tags tags--large">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></section>
              <section className="resume-section"><span>СОВПАВШИЕ НАВЫКИ</span><p>{candidate.matchedSkills?.join(", ") || "Нет данных"}</p></section>
              <section className="resume-section"><span>ТРЕБУЮТ УТОЧНЕНИЯ</span><p>{candidate.missingSkills?.join(", ") || "Нет данных"}</p></section>
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
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="resume-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="resume-modal__top">
          <span>ПОЛНОЕ РЕЗЮМЕ</span>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть резюме"><Icon name="close" /></button>
        </div>
        <div className="resume-cover">
          <div className="resume-avatar">{candidate.initials}</div>
          <div className="resume-cover__main">
            <div className="resume-name">{candidate.name}<span className="verified"><Icon name="check" size={12} /></span></div>
            <strong>{candidate.role} · уровень {candidate.level}</strong>
            <span>{candidate.location} · {candidate.format} · опыт {candidate.experience}</span>
          </div>
          <div className="resume-match"><span>Совпадение</span><strong>{candidate.score}%</strong></div>
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
              <span>КАРТА НАВЫКОВ</span>
              <Radar values={candidate.radar} target={candidate.jobRadar} />
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
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="compare-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="resume-modal__top">
          <div><span>СРАВНЕНИЕ РЕЗЮМЕ</span><strong>{items.length} кандидата рядом</strong></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть сравнение"><Icon name="close" /></button>
        </div>
        <div className="compare-grid" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(16rem, 1fr))` }}>
          {items.map((candidate) => (
            <article className="compare-column" key={candidate.id}>
              <div className="compare-person">
                <div className="avatar avatar--large">{candidate.initials}</div>
                <div><strong>{candidate.name}</strong><span>{candidate.role}</span></div>
              </div>
              <div className="compare-score"><span>Совпадение</span><strong>{candidate.score}%</strong></div>
              {candidate.backendId ? (
                <div className="compare-match-details">
                  <div><span>СОВПАЛО</span><strong>{candidate.matchedSkills?.join(", ") || "Нет данных"}</strong></div>
                  <div><span>НЕ СОВПАЛО</span><strong>{candidate.missingSkills?.join(", ") || "Не указано"}</strong></div>
                </div>
              ) : <Radar values={candidate.radar} target={candidate.jobRadar} compact />}
              <div className="compare-facts">
                <div><span>Уровень</span><strong>{candidate.level}</strong></div>
                <div><span>Опыт</span><strong>{candidate.backendId ? "Нет данных" : candidate.experience}</strong></div>
                <div><span>Зарплата</span><strong>{candidate.backendId ? "Нет данных" : candidate.salary}</strong></div>
                <div><span>Доверие</span><strong>{candidate.backendId ? "Нет данных" : candidate.trust.toFixed(2).replace(".", ",")}</strong></div>
                <div><span>Город</span><strong>{candidate.location}</strong></div>
                <div><span>Формат</span><strong>{candidate.format}</strong></div>
              </div>
              <div className="tags">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
              <div className="compare-summary"><span>ПОЧЕМУ В ПОДБОРКЕ</span><p>{candidate.summary}</p><b>{candidate.gap}</b></div>
              <Button variant="outline" onClick={() => onOpen(candidate)}>{candidate.backendId ? "Выбрать кандидата" : "Открыть полное резюме"}</Button>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function DemoSpotlightTour({
  role,
  onFinish,
}: {
  role: "employer" | "candidate";
  onFinish: () => void;
}) {
  const [step, setStep] = useState(0);
  const [spotlight, setSpotlight] = useState<{ top: number; left: number; width: number; height: number } | null>(null);
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

  useEffect(() => {
    let measureTimer = 0;
    const update = () => {
      const target = document.querySelector<HTMLElement>(`[data-tour="${item.target}"]`);
      if (!target) {
        setSpotlight(null);
        return;
      }
      const bounds = target.getBoundingClientRect();
      const padding = 8;
      setSpotlight({
        top: Math.max(8, bounds.top - padding),
        left: Math.max(8, bounds.left - padding),
        width: Math.min(window.innerWidth - 16, bounds.width + padding * 2),
        height: Math.min(window.innerHeight - 16, bounds.height + padding * 2),
      });
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
  const cardAtBottom = spotlight ? spotlight.top < window.innerHeight * 0.48 : true;
  return (
    <>
      {spotlight && <>
        <div className="tour-shade" style={{ top: 0, left: 0, right: 0, height: spotlight.top }} />
        <div className="tour-shade" style={{ top: spotlight.top + spotlight.height, left: 0, right: 0, bottom: 0 }} />
        <div className="tour-shade" style={{ top: spotlight.top, left: 0, width: spotlight.left, height: spotlight.height }} />
        <div className="tour-shade" style={{ top: spotlight.top, left: spotlight.left + spotlight.width, right: 0, height: spotlight.height }} />
        <div className="tour-spotlight" style={spotlight} />
      </>}
      <section className={`demo-tour-card ${cardAtBottom ? "demo-tour-card--bottom" : "demo-tour-card--top"}`} role="dialog" aria-modal="true" aria-labelledby="demo-tour-title">
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
  onFspLogin,
  onDemoLogin,
}: {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, role: "employer" | "candidate") => Promise<string | undefined>;
  onVerify: (email: string, code: string) => Promise<void>;
  onFspLogin: (fspId: string) => Promise<void>;
  onDemoLogin: (role: "candidate" | "employer") => Promise<void>;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [selectedRole, setSelectedRole] = useState<"employer" | "candidate">("candidate");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [code, setCode] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fspLoginOpen, setFspLoginOpen] = useState(false);
  const [fspId, setFspId] = useState("");

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

  const signInWithFsp = async () => {
    if (!fspId.trim()) return;
    setBusy(true);
    setError("");
    try {
      await onFspLogin(fspId.trim());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось войти через ФСП ID");
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
            <label className="field field--flush"><span>EMAIL</span><input value={email} onChange={(event) => setEmail(event.target.value)} type="email" /></label>
            <label className="field field--flush"><span>ПАРОЛЬ</span><input value={password} onChange={(event) => setPassword(event.target.value)} type="password" /></label>
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
        <div className="auth-sso"><span>или</span>{fspLoginOpen ? <><label className="field field--flush"><span>ФСП ID</span><input value={fspId} onChange={(event) => setFspId(event.target.value)} placeholder="FSP-77-001" /></label><Button variant="outline" disabled={busy || !fspId.trim()} onClick={() => void signInWithFsp()}>{busy ? "Проверяем…" : "Войти по ФСП ID"}</Button></> : <Button variant="outline" onClick={() => setFspLoginOpen(true)}>Продолжить через ФСП ID</Button>}<small>Вход через реестр ФСП</small></div>
        <div className="demo-access">
          <span>ДЕМО-ДОСТУП</span>
          <div>
            <Button variant="outline" disabled={busy} onClick={() => void signInToDemo("candidate")}><Icon name="users" /> {busy ? "Подключаем…" : "Кандидат"}</Button>
            <Button variant="outline" disabled={busy} onClick={() => void signInToDemo("employer")}><Icon name="briefcase" /> {busy ? "Подключаем…" : "Компания"}</Button>
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
          {step === 1 && <><span>ШАГ 2</span><strong>Выберите направление и уровень</strong><p>Грейд подтверждает только тест. Достижения ФСП влияют на порядок в подборке, но грейд не подтверждают. {TEST_AVAILABILITY_HINT}</p><div className="field-row field-row--flush"><label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={specialization} onChange={(event) => setSpecialization(event.target.value)}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label><label className="field"><span>ПРЕДПОЛАГАЕМЫЙ УРОВЕНЬ</span><select value={grade} onChange={(event) => setGrade(event.target.value)}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></div>{!isTestablePair(specialization, grade) && <p className="feature-description feature-description--left">Для пары «{specialization} · {grade}» теста пока нет — профиль сохранить можно, но сквозной сценарий (тест → подборка → приглашение) сейчас проходится только на Backend Junior / Middle / Senior. <Button variant="outline" onClick={() => { setSpecialization("Backend"); setGrade("middle"); }}>Выбрать Backend · Middle для теста</Button></p>}</>}
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
  onInvite,
  onNotify,
}: {
  items: Candidate[];
  onOpen: (candidate: Candidate) => void;
  onInvite: (candidate: Candidate) => void;
  onNotify: (message: string) => void;
}) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<"left" | "right" | null>(null);
  const [entering, setEntering] = useState(false);
  const candidate = items[index % items.length];
  const nextCandidate = items[(index + 1) % items.length];

  const move = (nextDirection: "left" | "right") => {
    if (direction) return;
    setDirection(nextDirection);
    window.setTimeout(() => {
      if (nextDirection === "right") onNotify(`${candidate.name} добавлен в список интересных`);
      setIndex((current) => current + 1);
      setDirection(null);
      setEntering(true);
      window.setTimeout(() => setEntering(false), 400);
    }, 340);
  };

  return (
    <div className="swipe-workspace">
      <div className="swipe-help"><Icon name="users" /><div><strong>Быстрый просмотр</strong><span>Смахните влево, чтобы пропустить, вправо — чтобы сохранить кандидата.</span></div></div>
      <div className="swipe-deck">
        <article className="swipe-card swipe-card--under" aria-hidden="true"><span>СЛЕДУЮЩИЙ ПРОФИЛЬ</span><strong>{nextCandidate.name}</strong><small>{nextCandidate.role} · {nextCandidate.level} · совпадение {nextCandidate.score}%</small></article>
        <article className={`swipe-card ${direction ? `swipe-card--leaving-${direction}` : entering ? "swipe-card--entering" : ""}`}>
          <div className="swipe-card__cover">
            <div className="resume-avatar">{candidate.initials}</div>
            <div><span>ПОДТВЕРЖДЁННЫЙ ПРОФИЛЬ</span><strong>{candidate.name}</strong><p>{candidate.role} · уровень {candidate.level}</p></div>
            <div className="resume-match"><span>Совпадение</span><strong>{candidate.score}%</strong></div>
          </div>
          <div className="swipe-card__body">
            {candidate.radar.length ? <Radar values={candidate.radar} target={candidate.jobRadar} /> : <div className="swipe-skill-match"><strong>Совпадение по навыкам</strong><div><span>Совпало</span><b>{candidate.matchedSkills?.join(" · ") || "Нет данных"}</b></div><div><span>Проверить</span><b>{candidate.missingSkills?.join(" · ") || "Нет данных"}</b></div></div>}
            <div className="swipe-details">
              <p>{candidate.summary}</p>
              <div className="compare-facts">
                <div><span>Опыт</span><strong>{candidate.experience}</strong></div>
                <div><span>Ожидания</span><strong>{candidate.salary}</strong></div>
                <div><span>Город</span><strong>{candidate.location}</strong></div>
                <div><span>Формат</span><strong>{candidate.format}</strong></div>
              </div>
              <div className="tags">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
              {candidate.achievements[0] && <div className="swipe-achievement">◆ {candidate.achievements[0]}</div>}
              <Button variant="ghost" onClick={() => onOpen(candidate)}>Открыть полное резюме</Button>
            </div>
          </div>
        </article>
        <div className="swipe-actions">
          <button type="button" className="swipe-action swipe-action--skip" onClick={() => move("left")}><Icon name="close" /><span>Пропустить</span></button>
          <button type="button" className="swipe-action swipe-action--open" onClick={() => onOpen(candidate)}><Icon name="users" /><span>Резюме</span></button>
          <button type="button" className="swipe-action swipe-action--save" onClick={() => { move("right"); onInvite(candidate); }}><Icon name="check" /><span>Интересен</span></button>
        </div>
        <div className="swipe-counter">{index + 1} из {items.length} · следующий профиль после действия</div>
      </div>
    </div>
  );
}

function App() {
  const [offlineDemo, setOfflineDemo] = useState(() => window.localStorage.getItem("fsp-offline-demo") === "true");
  const [authenticated, setAuthenticated] = useState(() => Boolean(window.localStorage.getItem("fsp-access-token")) || window.localStorage.getItem("fsp-offline-demo") === "true");
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
  const [selectedId, setSelectedId] = useState(1);
  const [query, setQuery] = useState("");
  const [onlyFsp, setOnlyFsp] = useState(false);
  const [compare, setCompare] = useState<number[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [offerDescription, setOfferDescription] = useState("Приглашаем в продуктовую команду. Будем рады обсудить задачи и ваш опыт.");
  const [inviteSalaryMin, setInviteSalaryMin] = useState("220000");
  const [inviteSalaryMax, setInviteSalaryMax] = useState("280000");
  const [inviteContact, setInviteContact] = useState("");
  const [notice, setNotice] = useState("");
  const [resumeCandidate, setResumeCandidate] = useState<Candidate | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "swipe">("list");
  const [backendCandidates, setBackendCandidates] = useState<Candidate[]>([]);
  const [employerNeeds, setEmployerNeeds] = useState<EmployerNeedRecord[]>([]);
  const [activeNeedId, setActiveNeedId] = useState<string | null>(null);
  const [noticeType, setNoticeType] = useState<"success" | "error">("success");
  const [noticeTimer, setNoticeTimer] = useState<number | undefined>();

  useEffect(() => {
    window.localStorage.setItem("fsp-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!authenticated) return;
    apiGet<{ role: "candidate" | "employer"; onboarding_completed: boolean }>("/auth/me")
      .then((user) => {
        setRole(user.role);
        window.localStorage.setItem("fsp-role", user.role);
        setOnboarding(user.role === "candidate" && !user.onboarding_completed);
        if (user.role === "employer" && !user.onboarding_completed) setActive("Настройки");
      })
      .catch(() => {
        clearSession();
        setAuthenticated(false);
      });
  }, [authenticated, offlineDemo]);

  useEffect(() => {
    if (!authenticated || role !== "employer") {
      setBackendCandidates([]);
      setEmployerNeeds([]);
      setActiveNeedId(null);
      return;
    }
    let cancelled = false;
    const loadSearch = () => {
      const params = new URLSearchParams({ fsp_only: String(onlyFsp) });
      return apiGet<MatchingCandidate[]>(`/matching/search?${params}`);
    };
    apiGet<EmployerNeedRecord[]>("/needs")
      .then(async (items) => {
        if (cancelled) return;
        setEmployerNeeds(items);
        const currentNeed = items.find((need) => need.is_active);
        setActiveNeedId(currentNeed?.id ?? null);
        if (!currentNeed) return loadSearch();
        return apiGet<{ candidates: MatchingCandidate[] }>(`/matching/for-need/${currentNeed.id}`)
          .then((response) => response.candidates);
      })
      .then((items) => {
        if (!cancelled && items) {
          setBackendCandidates(items.map(mapMatchToCandidate));
          setSelectedCandidate(null);
        }
      })
      .catch(async (error: unknown) => {
        try {
          const items = await loadSearch();
          if (!cancelled) setBackendCandidates(items.map(mapMatchToCandidate));
        } catch {
          if (!cancelled) {
            setBackendCandidates([]);
            showNotice(error instanceof Error ? error.message : "Не удалось загрузить подбор", "error");
          }
        }
      });
    return () => { cancelled = true; };
  }, [authenticated, role, onlyFsp, offlineDemo]);

  const filtered = useMemo(
    () => backendCandidates.filter((candidate) =>
      (!onlyFsp || candidate.fspVerified) &&
      `${candidate.name} ${candidate.skills.join(" ")}`.toLowerCase().includes(query.toLowerCase()),
    ),
    [backendCandidates, onlyFsp, query],
  );
  const selected =
    selectedCandidate ?? backendCandidates.find((candidate) => candidate.id === selectedId) ?? backendCandidates[0] ?? candidates[0];
  const activeNeed = employerNeeds.find((need) => need.id === activeNeedId);

  const nav =
    role === "employer"
      ? [
          ["grid", "Обзор"],
          ["users", "Подборка"],
          ["search", "Банк кандидатов"],
          ["briefcase", "Потребности"],
          ["send", "Приглашения"],
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
          ["send", "Приглашения"],
          ["search", "Вакансии"],
          ["settings", "Настройки"],
        ];
  const currentCopy = pageCopy[active] ?? pageCopy["Обзор"];
  const groupLabels: Record<string, string> =
    role === "employer"
      ? { Обзор: "ГЛАВНОЕ", Потребности: "ПОДБОР", Приглашения: "ОБЩЕНИЕ", Аналитика: "ДАННЫЕ" }
      : { Обзор: "ГЛАВНОЕ", Профиль: "ПРОФИЛЬ", Тестирование: "ОЦЕНКА", Приглашения: "РАБОТА" };

  const showNotice = (message: string, type: "success" | "error" = "success") => {
    setNotice(message);
    setNoticeType(type);
    if (noticeTimer) window.clearTimeout(noticeTimer);
    setNoticeTimer(window.setTimeout(() => setNotice(""), 4200));
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

  const fspLogin = async (fspId: string) => {
    const response = await apiPost<AuthResponse>(`/fsp/login-by-fsp-id?fsp_id=${encodeURIComponent(fspId)}`);
    enterWithSession(response);
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
        currency: "RUB",
      });
      setInviteOpen(false);
      showNotice(`Приглашение для ${selected.name} отправлено`);
    } catch (requestError) {
      showNotice(requestError instanceof Error ? requestError.message : "Не удалось отправить приглашение", "error");
    } finally {
      setSent(false);
    }
  };

  if (!authenticated) {
    return <AuthScreen onLogin={login} onRegister={register} onVerify={verifyEmail} onFspLogin={fspLogin} onDemoLogin={demoLogin} />;
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
      <aside className="sidebar" data-tour="demo-navigation">
        <Logo />
        <div className="workspace-label">{role === "employer" ? "РАБОТОДАТЕЛЬ" : "СОИСКАТЕЛЬ"}</div>
        <nav className="nav">
          {nav.map(([icon, item]) => (
            <div className="nav-group-wrap" key={item}>
              {groupLabels[item] && <div className="nav-group-label">{groupLabels[item]}</div>}
              <button
                type="button"
                data-tooltip={navHints[item] ?? "Откройте раздел, чтобы посмотреть связанные данные."}
                aria-label={`${item}: ${navHints[item] ?? "Откройте раздел, чтобы посмотреть связанные данные."}`}
                className={`nav__item ${active === item ? "nav__item--active" : ""}`}
                onClick={() => setActive(item)}
              >
                <Icon name={icon} />
                <span>{item}</span>
                {item === "Приглашения" && <b>3</b>}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <div className="company">
            <div className="company__avatar">{role === "employer" ? "NT" : "АМ"}</div>
            <div>
              <strong>{role === "employer" ? "NovaTech" : "Алексей Морозов"}</strong>
              <span>{role === "employer" ? "tech@novatech.ru" : "alexey@example.ru"}</span>
            </div>
            <Icon name="chevron" size={15} />
          </div>
          <button type="button" className="logout-button" onClick={logout}>Выйти</button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">{currentCopy.eyebrow}</div>
            <div className="page-title">{currentCopy.title}</div>
          </div>
          <div className="topbar__actions">
            {offlineDemo && <span className="demo-mode-badge">ДЕМО · ЛОКАЛЬНЫЕ ДАННЫЕ</span>}
            <div className="role-switch role-switch--static" aria-label="Тип аккаунта">
              {offlineDemo ? <><button type="button" className={role === "candidate" ? "active" : ""} onClick={() => { setRole("candidate"); setActive("Обзор"); window.localStorage.setItem("fsp-role", "candidate"); }}>Кандидат</button><button type="button" className={role === "employer" ? "active" : ""} onClick={() => { setRole("employer"); setActive("Обзор"); window.localStorage.setItem("fsp-role", "employer"); }}>Компания</button></> : <span>{role === "employer" ? "Компания" : "Кандидат"}</span>}
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
            <button type="button" className="icon-button" aria-label="Открыть приглашения" title="Открыть приглашения" onClick={() => setActive("Приглашения")}>
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

        {role === "employer" && active === "Подборка" ? (
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
              <span className="status"><i /> Подбор активен</span>
            </div>
            <div className="need-summary__meta">
              {activeNeed ? <><span>{activeNeed.specialization}</span><span>{new Intl.NumberFormat("ru-RU").format(activeNeed.salary_min)}–{new Intl.NumberFormat("ru-RU").format(activeNeed.salary_max)} ₽</span><span>{activeNeed.work_format === "remote" ? "Удалённо" : activeNeed.work_format}</span></> : <span>Создайте потребность, чтобы получить адресный подбор</span>}
            </div>
          </div>
          <Button variant="ghost">Изменить</Button>
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
          <Button variant="outline">
            Фильтры · <span className="filter-count">2</span>
          </Button>
          <div className="view-switch">
            <button type="button" className={viewMode === "list" ? "active" : ""} onClick={() => setViewMode("list")}><Icon name="grid" /> База</button>
            <button type="button" className={viewMode === "swipe" ? "active" : ""} onClick={() => setViewMode("swipe")}><Icon name="users" /> Свайп</button>
          </div>
          <div className="toolbar__result">
            Найдено <strong>{filtered.length}</strong>
          </div>
        </section>

        {viewMode === "swipe" ? (
          <SwipeDeck
            items={filtered.length ? filtered : candidates}
            onOpen={setResumeCandidate}
            onInvite={(candidate) => {
              if (!compare.includes(candidate.id)) setCompare((current) => [...current.slice(-2), candidate.id]);
            }}
            onNotify={showNotice}
          />
        ) : (
        <div className="content-grid">
          <section className="candidates-list" data-tour="candidate-list">
            <div className="list-head">
              <div>КАНДИДАТЫ ПО РЕЛЕВАНТНОСТИ</div>
              <button type="button">Сначала высокий матч <span>↕</span></button>
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
                    <strong>{candidate.score}%</strong>
                    <span>СОВПАДЕНИЕ</span>
                  </div>
                </div>
                <div className="candidate-card__middle">
                  {candidate.backendId ? <div className="match-explanation">{candidate.summary}</div> : <Radar values={candidate.radar} target={candidate.jobRadar} compact />}
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
                    <span className="fsp-badge">◆ Достижения ФСП: {candidate.achievementsCount}</span>
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
              <div className="empty-state">По выбранным параметрам кандидаты не найдены</div>
            )}
          </section>

          {backendCandidates.length > 0 && <aside className="profile-panel" data-tour="candidate-profile">
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
              <div className="grade-line__score">06.001 / ур. 6</div>
            </div>
            <div className="panel-section">
              <div className="section-title">
                <span>ЧЕГО НЕ ХВАТАЕТ</span>
                <div className="legend">
                  <i className="legend__candidate" /> Кандидат
                  <i className="legend__job" /> Вакансия
                </div>
              </div>
              <p className="feature-description feature-description--left">Детализация навыков появится после получения результатов тестирования кандидата.</p>
            </div>
            <div className="explain-card">
              <div className="explain-card__icon">i</div>
              <div>
                <strong>Почему этот кандидат в подборке</strong>
                <p>{selected.summary}</p>
                <span>Зона роста: {selected.gap}</span>
              </div>
            </div>
            <div className="panel-section">
              <div className="section-title">
                <span>ПОДТВЕРЖДЁННЫЙ СТЕК</span>
              </div>
              <div className="tags tags--large">
                {selected.skills.map((skill) => <span key={skill}>{skill}</span>)}
              </div>
            </div>
            <div className="profile-metrics">
              <div><span>ОЦЕНКА ДОВЕРИЯ</span><strong>Нет данных</strong><small>Не предоставляется matching API</small></div>
              <div><span>ФСП</span><strong>{selected.achievementsCount || "—"}</strong><small>{selected.fspVerified ? "достижения подтверждены" : "Нет подтверждения"}</small></div>
              <div><span>АКТУАЛЬНОСТЬ</span><strong>—</strong><small>Нет данных</small></div>
            </div>
            <div className="profile-panel__actions">
              <Button variant="outline" onClick={() => toggleCompare(selected.id)}>
                <Icon name="compare" /> Сравнить
              </Button>
              <Button onClick={() => setInviteOpen(true)}>
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
            onOpenCandidates={() => setActive("Подборка")}
            onOpenResume={setResumeCandidate}
            onNotify={showNotice}
            onNavigate={setActive}
            onNeedCreated={(need) => {
              setEmployerNeeds((current) => current.some((item) => item.id === need.id) ? current : [need, ...current]);
              setActiveNeedId(need.id);
              setSelectedCandidate(null);
              setActive("Подборка");
              apiGet<{ candidates: MatchingCandidate[] }>(`/matching/for-need/${need.id}`)
                .then((response) => setBackendCandidates(response.candidates.map(mapMatchToCandidate)))
                .catch((error: unknown) => showNotice(error instanceof Error ? error.message : "Не удалось сформировать подборку", "error"));
            }}
          />
        ) : (
          <CandidateScreen active={active} onNotify={showNotice} onNavigate={setActive} demoMode={offlineDemo} />
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
        <div className="modal-backdrop" onMouseDown={() => setInviteOpen(false)}>
          <div className="modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal__head">
              <div>
                <span>НОВОЕ ПРИГЛАШЕНИЕ</span>
                <strong>Пригласить {selected.name}</strong>
              </div>
              <button type="button" onClick={() => setInviteOpen(false)}><Icon name="close" /></button>
            </div>
            <div className="invite-person">
              <div className="avatar">{selected.initials}</div>
              <div><strong>{selected.role} · {selected.level}</strong><span>{selected.score}% совпадение с потребностью</span></div>
            </div>
            <label className="field">
              <span>ОПИСАНИЕ ПРЕДЛОЖЕНИЯ</span>
              <textarea value={offerDescription} onChange={(event) => setOfferDescription(event.target.value)} />
            </label>
            <div className="field-row">
              <label className="field">
                <span>ЗАРПЛАТА ОТ, ₽</span>
                <input inputMode="numeric" value={inviteSalaryMin} onChange={(event) => setInviteSalaryMin(event.target.value)} />
              </label>
              <label className="field">
                <span>ЗАРПЛАТА ДО, ₽</span>
                <input inputMode="numeric" value={inviteSalaryMax} onChange={(event) => setInviteSalaryMax(event.target.value)} />
              </label>
            </div>
            <label className="field">
              <span>СПОСОБ СВЯЗИ</span>
              <input value={inviteContact} onChange={(event) => setInviteContact(event.target.value)} placeholder="Email или Telegram" />
            </label>
            <div className="salary-note">
              Зарплатный диапазон обязателен и будет показан кандидату до принятия приглашения.
            </div>
            <div className="modal__actions">
              <Button variant="ghost" onClick={() => setInviteOpen(false)}>Отмена</Button>
              <Button onClick={submitInvite}>
                {sent ? "Отправляем…" : "Отправить приглашение"} <Icon name="send" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {role === "employer" && resumeCandidate && (
        <ResumeModal
          candidate={resumeCandidate}
          onClose={() => setResumeCandidate(null)}
          onInvite={() => {
            setSelectedId(resumeCandidate.id);
            setSelectedCandidate(resumeCandidate);
            setResumeCandidate(null);
            setInviteOpen(true);
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
      {demoTourOpen && <DemoSpotlightTour role={role} onFinish={() => { setDemoTourOpen(false); window.localStorage.setItem("fsp-demo-tour-complete", "true"); }} />}
    </div>
  );
}

export default App;
