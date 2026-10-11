import { useEffect, useMemo, useState, type ReactNode } from "react";

type Candidate = {
  id: number;
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

function Icon({
  name,
  size = 22,
}: {
  name: string;
  size?: number;
}) {
  const paths: Record<string, ReactNode> = {
    menu: (
      <>
        <path d="M4 6h16M4 12h16M4 18h16" />
      </>
    ),
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
  disabled,
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
      className={`button button--${variant} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

function ModalShell({
  eyebrow,
  title,
  onClose,
  children,
  wide,
}: {
  eyebrow: string;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`modal ${wide ? "modal--wide" : ""}`} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal__head">
          <div>
            <span>{eyebrow}</span>
            <strong>{title}</strong>
          </div>
          <button type="button" onClick={onClose} aria-label="Закрыть"><Icon name="close" /></button>
        </div>
        <div className="modal__body">{children}</div>
      </div>
    </div>
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
  const center = 100;
  const maxR = compact ? 65 : 60;
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
      x: center + Math.cos(angle) * (maxR + 18),
      y: center + Math.sin(angle) * (maxR + 18),
    };
  };

  return (
    <svg
      className={`radar ${compact ? "radar--compact" : ""}`}
      viewBox="0 0 200 200"
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
          const isLeft = pos.x < center - 10;
          const isRight = pos.x > center + 10;
          return (
            <text
              key={label}
              x={pos.x}
              y={pos.y}
              textAnchor={isLeft ? "end" : isRight ? "start" : "middle"}
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
  Приглашения: { eyebrow: "ПРЕДЛОЖЕНИЯ РАБОТОДАТЕЛЕЙ", title: "Приглашения" },
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
  Обзор: "Сводка: метрики, воронка и что требует внимания сегодня",
  Подборка: "Кандидаты под активную потребность: база и быстрый свайп",
  "Банк кандидатов": "Вся верифицированная база. Контакты скрыты до согласия",
  Потребности: "Опишите специалиста — система соберёт карту навыков и выдачу",
  Приглашения: "Исходящие и входящие предложения, статусы и открытые контакты",
  "Вакансии компании": "Публикация вакансий, отклики и короткие задачи для проверки",
  Аналитика: "Точность подбора, разрывы в навыках и план выходов",
  Настройки: "Профиль компании или кандидата, доступ, уведомления и согласия",
  Профиль: "Резюме, опыт, фото и распознанный PDF",
  Тестирование: "Проверка навыков для подтверждения уровня",
  "Мой грейд": "Подтверждённый уровень, карта навыков и история попыток",
  Задания: "Короткие кейсы, чтобы профиль не устаревал",
  Вакансии: "Открытые позиции с зарплатой до отклика",
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
  return (
    <div className={`metric-card ${accent ? "metric-card--accent" : ""}`}>
      <div className="metric-card__head">
        <span>{label}</span>
        {icon && <Icon name={icon} size={18} />}
      </div>
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
  onNotify,
}: {
  active: string;
  onOpenCandidates: () => void;
  onOpenResume: (candidate: Candidate) => void;
  onNotify: (message: string) => void;
}) {
  const [saved, setSaved] = useState(false);
  const [parsed, setParsed] = useState(true);
  const [vacancyEditor, setVacancyEditor] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [taskModal, setTaskModal] = useState(false);
  const [atsOpen, setAtsOpen] = useState(false);
  const [responsesOpen, setResponsesOpen] = useState(false);
  const [logoOpen, setLogoOpen] = useState(false);

  if (active === "Обзор") {
    return (
      <div className="page-content">
        <div className="metrics-grid">
          <MetricCard label="АКТИВНЫЕ ПОТРЕБНОСТИ" value="3" detail="+1 за эту неделю" accent icon="briefcase" />
          <MetricCard label="КАНДИДАТОВ В ПОДБОРКАХ" value="48" detail="12 новых профилей" icon="users" />
          <MetricCard label="ОТПРАВЛЕНО ПРИГЛАШЕНИЙ" value="16" detail="8 ожидают ответа" icon="send" />
          <MetricCard label="КОНВЕРСИЯ В КОНТАКТ" value="62%" detail="+8% к прошлому месяцу" icon="chart" />
        </div>
        <div className="dashboard-grid">
          <section className="feature-card feature-card--wide">
            <div className="feature-head">
              <div><span>АКТИВНЫЙ ПОДБОР</span><strong>Текущие потребности</strong></div>
              <Button variant="ghost" onClick={onOpenCandidates}>Все потребности</Button>
            </div>
            {[
              ["Backend-разработчик", "Middle", "18 кандидатов", "94%", 86],
              ["Frontend-разработчик", "Senior", "9 кандидатов", "91%", 63],
              ["DevOps-инженер", "Middle", "21 кандидат", "88%", 74],
            ].map((row) => (
              <button type="button" className="need-row" key={row[0]} onClick={onOpenCandidates}>
                <div className="need-row__icon"><Icon name="briefcase" /></div>
                <div><strong>{row[0]}</strong><span>{row[1]}</span></div>
                <div><span>В подборке</span><strong>{row[2]}</strong></div>
                <div><span>Лучшее совпадение</span><strong className="green">{row[3]}</strong></div>
                <Progress value={Number(row[4])} />
                <Icon name="chevron" />
              </button>
            ))}
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>ВОРОНКА</span><strong>Приглашения</strong></div></div>
            <div className="funnel">
              <div><span>Отправлено</span><strong>16</strong><Progress value={100} /></div>
              <div><span>Просмотрено</span><strong>12</strong><Progress value={75} /></div>
              <div><span>Принято</span><strong>8</strong><Progress value={50} /></div>
              <div><span>Контакт</span><strong>6</strong><Progress value={38} /></div>
            </div>
          </section>
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ПОСЛЕДНИЕ СОБЫТИЯ</span><strong>Активность</strong></div></div>
            <div className="activity-list">
              <div><i className="activity-dot activity-dot--green" /><p><strong>Алексей Морозов</strong> принял приглашение</p><span>12 мин назад</span></div>
              <div><i className="activity-dot" /><p>В подборке Backend появились <strong>4 новых кандидата</strong></p><span>1 час назад</span></div>
              <div><i className="activity-dot activity-dot--red" /><p><strong>Елена Смирнова</strong> просмотрела предложение</p><span>3 часа назад</span></div>
            </div>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>КАЧЕСТВО МАТЧИНГА</span><strong>За 30 дней</strong></div></div>
            <p className="feature-description">Качество подбора будет оценено по независимым оценкам работодателей. Подтверждённой метрики пока нет.</p>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Банк кандидатов") {
    return (
      <div className="page-content">
        <div className="bank-toolbar">
          <div className="search-field search-field--wide"><Icon name="search" /><input placeholder="Имя, специализация или технология" /></div>
          <Button variant="outline" onClick={() => setFiltersOpen(true)}><Icon name="filter" /> Фильтры</Button>
          <Button variant="outline" onClick={() => setFiltersOpen(true)}>Грейд</Button>
          <Button variant="outline" onClick={() => setFiltersOpen(true)}>Формат</Button>
          <Button variant="outline" onClick={() => setFiltersOpen(true)}>Доверие</Button>
        </div>
        {filtersOpen && (
          <ModalShell eyebrow="ФИЛЬТРЫ БАЗЫ" title="Уточните выдачу кандидатов" onClose={() => setFiltersOpen(false)}>
            <div className="field-row field-row--flush">
              <label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select defaultValue="backend"><option value="backend">Backend</option><option>Frontend</option><option>DevOps</option></select></label>
              <label className="field"><span>ГРЕЙД</span><select defaultValue="middle"><option value="middle">Middle</option><option>Senior</option><option>Junior</option></select></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field"><span>ФОРМАТ</span><select><option>Любой</option><option>Удалённо</option><option>Гибрид</option></select></label>
              <label className="field"><span>ГОРОД</span><input placeholder="Москва" /></label>
            </div>
            <div className="modal__actions">
              <Button variant="ghost" onClick={() => setFiltersOpen(false)}>Сбросить</Button>
              <Button onClick={() => { setFiltersOpen(false); onNotify("Фильтры применены к базе кандидатов"); }}>Показать результаты</Button>
            </div>
          </ModalShell>
        )}
        <div className="table-card">
          <div className="table-summary"><strong>1 284 верифицированных профиля</strong><span>Контакты скрыты до принятия приглашения</span></div>
          <div className="data-table data-table--candidates">
            <div className="data-row data-row--head"><span>КАНДИДАТ</span><span>КАТЕГОРИЯ</span><span>СТЕК</span><span>ДОВЕРИЕ</span><span>АКТИВНОСТЬ</span><span /></div>
            {candidates.map((candidate) => (
              <div className="data-row" key={candidate.id}>
                <div className="table-person"><div className="avatar">{candidate.initials}</div><div><strong>{candidate.name}</strong><span>{candidate.location}</span></div></div>
                <div><strong>{candidate.role}</strong><span>{candidate.level} · подтверждён</span></div>
                <div className="mini-tags">{candidate.skills.slice(0, 3).map((skill) => <span key={skill}>{skill}</span>)}</div>
                <strong className="green">{candidate.trust}</strong>
                <div><strong>Активен</strong><span>{candidate.updated}</span></div>
                <Button variant="outline" onClick={() => onOpenResume(candidate)}>Открыть резюме</Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (active === "Потребности") {
    return (
      <div className="page-content">
        <div className="steps">
          <div className="active"><b>1</b><span>Описание</span></div>
          <div><b>2</b><span>Оценка важности</span></div>
          <div><b>3</b><span>Публикация</span></div>
        </div>
        <div className="split-layout">
          <section className="feature-card">
            <div className="feature-head"><div><span>ШАГ 1 ИЗ 3</span><strong>Опишите специалиста</strong></div></div>
            <label className="field field--flush"><span>ОПИСАНИЕ ПОТРЕБНОСТИ</span><textarea defaultValue="Ищем Middle Backend-разработчика в команду платформы. Важны Python или Go, уверенная работа с PostgreSQL, проектирование REST API и опыт с Docker." /></label>
            <div className="field-row field-row--flush">
              <label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select defaultValue="backend"><option value="backend">Backend-разработчик</option><option>Frontend-разработчик</option></select></label>
              <label className="field"><span>УРОВЕНЬ</span><select defaultValue="middle"><option value="middle">Middle</option><option>Senior</option></select></label>
            </div>
            <div className="field-row field-row--flush">
              <label className="field"><span>ЗАРПЛАТА ОТ, ₽</span><input defaultValue="220 000" /></label>
              <label className="field"><span>ЗАРПЛАТА ДО, ₽</span><input defaultValue="280 000" /></label>
            </div>
            <Button onClick={() => setParsed(true)}><Icon name="chart" /> Проанализировать описание</Button>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>ИЗВЛЕЧЁННЫЕ ТРЕБОВАНИЯ</span><strong>Важность навыков — от 1 до 5</strong></div><span className="status"><i /> Готово</span></div>
            {parsed && (
              <>
                <p className="feature-description feature-description--left">Чем выше значение, тем сильнее этот навык влияет на позицию кандидата в подборке.</p>
                <div className="skill-weights">
                  {[
                    ["API и интеграции", 5],
                    ["Базы данных", 5],
                    ["Язык программирования", 4],
                    ["CI/CD", 3],
                    ["Тестирование", 3],
                    ["Алгоритмы", 2],
                  ].map(([skill, weight]) => (
                    <div key={String(skill)}><span>{skill}</span><input aria-label={`Вес ${skill}`} type="range" min="1" max="5" defaultValue={Number(weight)} /><strong>{weight}/5</strong></div>
                  ))}
                </div>
                <div className="job-radar"><Radar values={[8,8,8,7,7,7]} target={[8,8,8,7,7,7]} compact /><div><span>ИДЕАЛЬНЫЙ ПРОФИЛЬ</span><strong>Карта навыков вакансии</strong></div></div>
                <div className="parsed-tags"><span>ОБЯЗАТЕЛЬНО</span><b>Python</b><b>PostgreSQL</b><b>REST</b></div>
                <div className="parsed-tags"><span>ЖЕЛАТЕЛЬНО</span><b>Docker</b><b>Kafka</b></div>
                <div className="adjacent-skill"><Icon name="compare" /><div><strong>Смежный навык найден</strong><span>Кандидаты с RabbitMQ будут показаны с пометкой «вероятно, быстро освоит Kafka».</span></div></div>
                <div className="team-gap"><span>НАВЫКИ ТЕКУЩЕЙ КОМАНДЫ</span><div className="tags"><span>Python</span><span>PostgreSQL</span><span>Docker</span></div><p>Системе сильнее всего не хватает экспертизы в Kafka и проектировании API — эти навыки получат больший вес.</p></div>
                <Button onClick={onOpenCandidates}>Сформировать подборку <Icon name="chevron" /></Button>
              </>
            )}
          </section>
        </div>
      </div>
    );
  }

  if (active === "Приглашения") {
    return <Invitations employer />;
  }

  if (active === "Вакансии компании") {
    return (
      <div className="page-content">
        <div className="vacancy-head"><div><strong>Вакансии NovaTech</strong><span>Зарплатный диапазон обязателен для публикации</span></div><Button onClick={() => setVacancyEditor(!vacancyEditor)}><span className="button-plus">+</span> Создать вакансию</Button></div>
        {vacancyEditor && (
          <section className="feature-card vacancy-editor">
            <div className="feature-head"><div><span>НОВАЯ ВАКАНСИЯ</span><strong>Основные условия</strong></div><Button variant="ghost" onClick={() => setVacancyEditor(false)}>Закрыть</Button></div>
            <div className="field-row field-row--flush"><label className="field"><span>НАЗВАНИЕ *</span><input defaultValue="Backend-разработчик" /></label><label className="field"><span>СПЕЦИАЛИЗАЦИЯ *</span><select><option>Backend</option><option>Frontend</option><option>DevOps</option></select></label></div>
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
          ].map((item) => <article key={item[0]}><div className="need-row__icon"><Icon name="briefcase" /></div><div><strong>{item[0]}</strong><span>{item[1]} · {item[2]}</span></div><b>{item[3]}</b><em>{item[4]}</em><Button variant="outline" onClick={() => setVacancyEditor(true)}>Редактировать</Button><Button variant="ghost" onClick={() => setResponsesOpen(true)}>Отклики</Button></article>)}
        </div>
        <section className="feature-card employer-task-create"><div><span>РЕГУЛЯРНАЯ ЗАДАЧА</span><strong>Проверьте кандидатов на реальном кейсе</strong><p>Создайте короткую задачу — результат будет виден только вашей компании и добавит свежий сигнал в профиль.</p></div><Button variant="outline" onClick={() => setTaskModal(true)}>Создать задачу</Button></section>
        {responsesOpen && (
          <ModalShell eyebrow="ОТКЛИКИ" title="Backend-разработчик · 8 откликов" onClose={() => setResponsesOpen(false)} wide>
            {candidates.slice(0, 4).map((candidate) => (
              <button type="button" className="need-row" key={candidate.id} onClick={() => { setResponsesOpen(false); onOpenResume(candidate); }}>
                <div className="need-row__icon"><span>{candidate.initials}</span></div>
                <div><strong>{candidate.name}</strong><span>{candidate.role} · {candidate.level}</span></div>
                <div><span>Совпадение</span><strong>{candidate.score}%</strong></div>
                <div><span>Статус</span><strong>Новый</strong></div>
                <Icon name="chevron" />
              </button>
            ))}
          </ModalShell>
        )}
        {taskModal && (
          <ModalShell eyebrow="НОВАЯ ЗАДАЧА" title="Короткий кейс для кандидатов" onClose={() => setTaskModal(false)}>
            <label className="field field--flush"><span>НАЗВАНИЕ</span><input defaultValue="Code review обработчика API" /></label>
            <label className="field field--flush"><span>ОПИСАНИЕ</span><textarea defaultValue="Найдите проблемы безопасности и производительности в сниппете. 10 минут, результат виден только NovaTech." /></label>
            <div className="field-row field-row--flush">
              <label className="field"><span>ВРЕМЯ, МИН</span><input defaultValue="10" /></label>
              <label className="field"><span>НАВЫК</span><select><option>API</option><option>Базы данных</option><option>CI/CD</option></select></label>
            </div>
            <div className="modal__actions">
              <Button variant="ghost" onClick={() => setTaskModal(false)}>Отмена</Button>
              <Button onClick={() => { setTaskModal(false); onNotify("Задача создана и будет показана в профилях кандидатов"); }}>Опубликовать задачу</Button>
            </div>
          </ModalShell>
        )}
      </div>
    );
  }

  if (active === "Аналитика") {
    return (
      <div className="page-content">
        <section className="feature-card">
          <div className="feature-head"><div><span>АНАЛИТИКА</span><strong>Данных пока недостаточно</strong></div></div>
          <p className="feature-description feature-description--left">Метрики качества теста и подбора появятся после проверки на реальных участниках и оценок работодателей.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="settings-layout">
        <section className="feature-card form-card" data-tour="company-form">
          <div className="feature-head"><div><span>КОМПАНИЯ</span><strong>Профиль NovaTech</strong></div></div>
          <div className="company-logo-upload"><div className="company__avatar">NT</div><div><strong>Логотип компании</strong><span>PNG или SVG, до 5 МБ</span></div><Button variant="outline" onClick={() => setLogoOpen(true)}>Заменить</Button></div>
          <label className="field field--flush"><span>НАЗВАНИЕ КОМПАНИИ</span><input defaultValue="NovaTech" /></label>
          <label className="field field--flush"><span>ОПИСАНИЕ</span><textarea defaultValue="Разрабатываем платформенные решения для финансового сектора." /></label>
          <div className="field-row field-row--flush"><label className="field"><span>НАПРАВЛЕНИЕ</span><input defaultValue="Финтех" /></label><label className="field"><span>РАЗМЕР КОМАНДЫ</span><input defaultValue="120 человек" /></label></div>
          <div className="field-row field-row--flush"><label className="field"><span>САЙТ</span><input defaultValue="https://novatech.ru" /></label><label className="field"><span>ИНН · НЕОБЯЗАТЕЛЬНО</span><input defaultValue="7701234567" /></label></div>
          <div className="field-row field-row--flush"><label className="field"><span>КОНТАКТНЫЙ EMAIL</span><input defaultValue="hr@novatech.ru" /></label><label className="field"><span>ТЕЛЕФОН</span><input defaultValue="+7 495 123-45-67" /></label></div>
          <Button onClick={() => { setSaved(true); onNotify("Профиль компании сохранён"); }}>{saved ? "Сохранено" : "Сохранить изменения"}</Button>
        </section>
        <section className="feature-card form-card">
          <div className="feature-head"><div><span>БЕЗОПАСНОСТЬ</span><strong>Доступ и уведомления</strong></div></div>
          <ToggleRow title="Email о новых кандидатах" detail="Ежедневная подборка по активным потребностям" checked />
          <ToggleRow title="Статусы приглашений" detail="Сообщать о просмотре и принятии" checked />
          <ToggleRow title="Двухфакторная авторизация" detail="Дополнительная защита аккаунта" />
          <div className="integration-card"><Icon name="settings" /><div><strong>ATS-интеграция</strong><span>Подключите webhook или REST API</span></div><Button variant="outline" onClick={() => setAtsOpen(true)}>Настроить</Button></div>
        </section>
      </div>
      {logoOpen && (
        <ModalShell eyebrow="ЛОГОТИП" title="Замените логотип компании" onClose={() => setLogoOpen(false)}>
          <div className="upload-box"><Icon name="briefcase" size={26} /><strong>Перетащите PNG или SVG</strong><span>До 5 МБ, квадратный формат выглядит лучше в подборках</span><Button variant="outline" onClick={() => { setLogoOpen(false); onNotify("Логотип обновлён"); }}>Выбрать файл</Button></div>
        </ModalShell>
      )}
      {atsOpen && (
        <ModalShell eyebrow="ИНТЕГРАЦИЯ" title="Подключение ATS" onClose={() => setAtsOpen(false)}>
          <label className="field field--flush"><span>WEBHOOK URL</span><input placeholder="https://ats.novatech.ru/hooks/fsp" /></label>
          <label className="field field--flush"><span>API-КЛЮЧ</span><input placeholder="Секретный ключ останется только у вас" /></label>
          <div className="modal__actions">
            <Button variant="ghost" onClick={() => setAtsOpen(false)}>Отмена</Button>
            <Button onClick={() => { setAtsOpen(false); onNotify("ATS-интеграция сохранена"); }}>Сохранить подключение</Button>
          </div>
        </ModalShell>
      )}
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

function Invitations({ employer = false, onNotify }: { employer?: boolean; onNotify?: (message: string) => void }) {
  const [statuses, setStatuses] = useState(["Ожидает ответа", "Просмотрено", "Принято"]);
  const contacts = ["@novatech_hr", "@praktikum_team", "@ozontech_jobs"];
  const update = (index: number, status: string) => {
    setStatuses((current) => current.map((item, i) => i === index ? status : item));
    onNotify?.(status === "Принято" ? "Приглашение принято — контакт компании открыт" : "Приглашение отклонено");
  };
  return (
    <div className="page-content">
      <div className="tab-row"><button type="button" className="active">Все <span>3</span></button><button type="button">Ожидают ответа</button><button type="button">Принятые</button><button type="button">Отклонённые</button></div>
      <div className="invitation-list">
        {(employer ? candidates : candidates.map((item, index) => ({ ...item, name: ["NovaTech", "Яндекс Практикум", "Ozon Tech"][index], role: ["Backend-разработчик", "Python-разработчик", "Software Engineer"][index] }))).map((item, index) => (
          <article className="invitation-card" key={item.id}>
            <div className="invitation-logo">{employer ? item.initials : item.name.slice(0, 2).toUpperCase()}</div>
            <div className="invitation-main"><span>{employer ? "КАНДИДАТ" : "ПРИГЛАШЕНИЕ ОТ КОМПАНИИ"}</span><strong>{item.name}</strong><p>{item.role} · уровень {item.level}</p>{!employer && <p className="invitation-description">Присоединяйтесь к продуктовой команде: развитие API, работа с данными и участие в архитектурных решениях.</p>}<div className="tags"><span>{item.salary}</span><span>{item.format}</span>{!employer && <span>Связь: Telegram или почта</span>}</div></div>
            {!employer && <div className="invitation-radar"><Radar values={item.jobRadar} target={item.radar} compact /><span>Карта навыков вакансии</span></div>}
            <div className="invitation-status"><span className={`status-pill status-pill--${statuses[index] === "Принято" ? "green" : "violet"}`}>{statuses[index]}</span><small>{index + 2} дня назад</small></div>
            {!employer && statuses[index] !== "Принято" && <div className="invitation-actions"><Button variant="ghost" onClick={() => update(index, "Отклонено")}>Отклонить</Button><Button onClick={() => update(index, "Принято")}>Принять</Button></div>}
            {!employer && statuses[index] === "Принято" && <div className="contact-box"><span>КОНТАКТ ОТКРЫТ</span><strong>{contacts[index]}</strong></div>}
          </article>
        ))}
      </div>
    </div>
  );
}

function CandidateScreen({
  active,
  onNotify,
  onNavigate,
}: {
  active: string;
  onNotify: (message: string) => void;
  onNavigate: (tab: string) => void;
}) {
  const [testStarted, setTestStarted] = useState(false);
  const [question, setQuestion] = useState(1);
  const [answer, setAnswer] = useState("");
  const [testDone, setTestDone] = useState(false);
  const [taskDone, setTaskDone] = useState(false);
  const [saved, setSaved] = useState(false);
  const [applied, setApplied] = useState<number[]>([]);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [fspOpen, setFspOpen] = useState(false);
  const [jobFilters, setJobFilters] = useState(false);

  if (active === "Обзор") {
    return (
      <div className="page-content">
        <div className="candidate-welcome">
          <div><span>ДОБРЫЙ ДЕНЬ, АЛЕКСЕЙ</span><strong>Ваш профиль видят работодатели</strong><p>Профиль подтверждён и находится в категории Backend · Middle.</p></div>
          <div className="profile-completion"><strong>92%</strong><span>Профиль заполнен</span><Progress value={92} /></div>
        </div>
        <div className="metrics-grid">
          <MetricCard label="ПРОСМОТРЫ ПРОФИЛЯ" value="34" detail="+12 за неделю" accent icon="users" />
          <MetricCard label="ПРИГЛАШЕНИЯ" value="3" detail="2 новых" icon="bell" />
          <MetricCard label="ПОДТВЕРЖДЁННЫЙ ГРЕЙД" value="Middle" detail="Результат базового теста" icon="check" />
          <MetricCard label="ПРОФИЛЬ" value="Виден" detail="Опубликован кандидатом" icon="sun" />
        </div>
        <div className="dashboard-grid">
          <section className="feature-card">
            <div className="feature-head"><div><span>ТЕКУЩИЙ СТАТУС</span><strong>Backend · Middle</strong></div><span className="status"><i /> Подтверждён</span></div>
            <Radar values={[8,9,8,7,6,7]} target={[8,8,8,7,7,7]} />
          </section>
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ТРЕБУЕТ ВНИМАНИЯ</span><strong>Следующие действия</strong></div></div>
            <div className="action-list">
              <div><div className="action-number">01</div><div><strong>Ответьте на 2 приглашения</strong><span>Работодатели ждут решения</span></div><Button onClick={() => onNavigate("Приглашения")}>Открыть</Button></div>
              <div><div className="action-number">02</div><div><strong>Решите регулярную задачу</strong><span>Сохраните актуальность профиля</span></div><Button variant="outline" onClick={() => onNavigate("Задания")}>Начать</Button></div>
              <div><div className="action-number">03</div><div><strong>Добавьте опыт работы</strong><span>Профиль заполнен на 92%</span></div><Button variant="ghost" onClick={() => onNavigate("Профиль")}>Дополнить</Button></div>
            </div>
          </section>
          <section className="feature-card feature-card--fsp">
            <div className="feature-head"><div><span>ДОСТИЖЕНИЯ ФСП</span><strong>Свяжите ФСП ID</strong></div><div className="fsp-symbol">◆</div></div>
            <p className="feature-description feature-description--left">Доступные тестовые записи отображаются отдельно от грейда и не повышают балл подбора.</p>
            <Button variant="outline" onClick={() => onNavigate("Настройки")}>Связать ФСП ID</Button>
          </section>
        </div>
      </div>
    );
  }

  if (active === "Профиль") {
    return (
      <div className="page-content">
        <div className="settings-layout settings-layout--profile">
          <section className="feature-card form-card" data-tour="candidate-profile">
            <div className="profile-edit-head"><div className="avatar avatar--xl">АМ</div><div><strong>Алексей Морозов</strong><span>Backend-разработчик · Москва</span></div><Button variant="outline" onClick={() => setPhotoOpen(true)}>Заменить фото</Button></div>
            <div className="field-row field-row--flush"><label className="field"><span>ИМЯ</span><input defaultValue="Алексей" /></label><label className="field"><span>ФАМИЛИЯ</span><input defaultValue="Морозов" /></label></div>
            <label className="field field--flush"><span>О СЕБЕ</span><textarea defaultValue="Backend-разработчик с опытом создания высоконагруженных API и сервисов обработки данных." /></label>
            <div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input defaultValue="Москва" /></label><label className="field"><span>ФОРМАТ РАБОТЫ</span><select><option>Удалённо</option><option>Гибрид</option></select></label></div>
            <Button onClick={() => { setSaved(true); onNotify("Изменения профиля сохранены"); }}>{saved ? "Профиль сохранён" : "Сохранить"}</Button>
          </section>
          <section className="feature-card">
            <div className="feature-head"><div><span>РЕЗЮМЕ</span><strong>Опыт и документы</strong></div></div>
            <div className="upload-box"><Icon name="briefcase" size={26} /><strong>Загрузить PDF-резюме</strong><span>Система автоматически извлечёт опыт, стек и контакты</span><Button variant="outline" onClick={() => setPdfOpen(true)}>Выбрать файл</Button></div>
            <div className="resume-entry"><span>2022 — сейчас</span><strong>Backend-разработчик · FinCore</strong><p>Python, FastAPI, PostgreSQL. Команда 8 человек.</p></div>
            <div className="resume-entry"><span>2020 — 2022</span><strong>Junior Python Developer · DataLab</strong><p>Django, Celery, Redis.</p></div>
            <div className="soft-skills"><span>СОФТ-СКИЛЛЫ</span><div className="tags tags--large"><span>Коммуникация</span><span>Лидерство</span><span>Agile</span><span>Scrum</span></div></div>
            <Button variant="outline" onClick={() => onNotify("PDF-профиль скачан")}>Скачать PDF-профиль</Button>
          </section>
        </div>
        {photoOpen && (
          <ModalShell eyebrow="ФОТО" title="Обновите фото профиля" onClose={() => setPhotoOpen(false)}>
            <div className="upload-box"><Icon name="users" size={26} /><strong>Квадратное фото, до 5 МБ</strong><span>Его увидят работодатели после принятия приглашения</span><Button onClick={() => { setPhotoOpen(false); onNotify("Фото профиля обновлено"); }}>Загрузить</Button></div>
          </ModalShell>
        )}
        {pdfOpen && (
          <ModalShell eyebrow="ДОКУМЕНТ" title="Загрузка файла" onClose={() => setPdfOpen(false)}>
            <div className="upload-box"><Icon name="briefcase" size={26} /><strong>PDF до 10 МБ</strong><span>После загрузки поля резюме заполнятся автоматически — их можно поправить</span><Button onClick={() => { setPdfOpen(false); onNotify("Файл принят, поля резюме обновлены"); }}>Выбрать PDF</Button></div>
          </ModalShell>
        )}
      </div>
    );
  }

  if (active === "Тестирование") {
    if (testDone) {
      return <div className="page-content"><div className="test-result"><div className="result-check"><Icon name="check" size={34} /></div><span>ТЕСТ ЗАВЕРШЁН</span><strong>Уровень Middle подтверждён</strong><p>Вы решили 14 из 16 адаптивных задач. Итоговый балл: 8,4 из 10. Точность оценки высокая.</p><div className="result-score"><b>8,1</b><span>Средний балл карты навыков</span></div><Button onClick={() => { setTestDone(false); setTestStarted(false); setQuestion(1); }}>Посмотреть подробный результат</Button></div></div>;
    }
    if (testStarted) {
      return (
        <div className="test-shell">
          <div className="test-top"><div><span>АДАПТИВНОЕ ТЕСТИРОВАНИЕ · BACKEND</span><strong>Задача {question} из ~15</strong></div><div className="timer">18:42</div></div>
          <Progress value={question * 7} />
          <div className="test-content test-content--focused">
            <div className="question-card"><span>БАЗЫ ДАННЫХ · УРОВЕНЬ УТОЧНЯЕТСЯ</span><strong>Какой уровень изоляции транзакций предотвращает dirty read, но допускает non-repeatable read?</strong><div className="answers">{["Read Uncommitted", "Read Committed", "Repeatable Read", "Serializable"].map((item) => <button type="button" key={item} className={answer === item ? "selected" : ""} onClick={() => setAnswer(item)}><i />{item}</button>)}</div></div>
          </div>
          <div className="test-footer"><Button variant="ghost">Пропустить</Button><Button onClick={() => { if (question >= 5) setTestDone(true); else { setQuestion(question + 1); setAnswer(""); } }} className={!answer ? "button--disabled" : ""}>Ответить и продолжить <Icon name="chevron" /></Button></div>
        </div>
      );
    }
    return (
      <div className="page-content">
        <div className="test-intro">
          <div className="test-intro__graphic"><span>&lt;/&gt;</span><i /><b /></div>
          <span>АДАПТИВНЫЙ ТЕСТ</span><strong>Подтвердите уровень Backend Middle</strong><p>Тест подбирает сложность под ваши ответы. У каждого кандидата уникальная, но сопоставимая по сложности последовательность заданий.</p>
          <div className="test-features"><div><b>12–20</b><span>задач</span></div><div><b>45 мин</b><span>максимум</span></div><div><b>6</b><span>компетенций</span></div></div>
          <div className="notice-box">Таймер запускается отдельно для каждой задачи. Вернуться к предыдущему ответу нельзя.</div>
          <div className="test-choice-actions"><Button onClick={() => setTestStarted(true)}>Начать тестирование <Icon name="chevron" /></Button></div>
        </div>
      </div>
    );
  }

  if (active === "Мой грейд") {
    return (
      <div className="page-content">
        <div className="grade-hero"><div><span>ПОДТВЕРЖДЁННОЕ ВЛАДЕНИЕ СТЕКОМ</span><strong>Backend · Middle</strong><p>Профстандарт 06.001 · уровень квалификации 6</p></div><div className="grade-stamp"><Icon name="check" /><span>ПОДТВЕРЖДЕНО</span><strong>12.05.2025</strong></div></div>
        <div className="dashboard-grid">
          <section className="feature-card"><div className="feature-head"><div><span>ОСНОВНАЯ КАРТА НАВЫКОВ</span><strong>Компетенции</strong></div></div><Radar values={[8,9,8,7,6,7]} target={[7,7,7,7,7,7]} /></section>
          <section className="feature-card feature-card--wide">
            <div className="feature-head"><div><span>ДЕТАЛИ РЕЗУЛЬТАТА</span><strong>Подтверждённые навыки</strong></div></div>
            <div className="skill-table">{labels.map((label, index) => <div key={label}><span>{label}</span><Progress value={[80,90,80,70,60,70][index]} /><strong>{[8,9,8,7,6,7][index]}/10</strong></div>)}</div>
            <div className="grade-actions"><div><span>Следующая попытка повышения</span><strong>через 48 дней</strong></div><Button variant="outline" onClick={() => setHistoryOpen(true)}>История тестов</Button><Button onClick={() => setPlanOpen(true)}>План развития</Button></div>
            <div className="growth-recommendation"><Icon name="chart" /><div><strong>Путь к уровню Senior</strong><p>Поднимите CI/CD с 6 до 7 и тестирование с 6 до 7. Мы подобрали 4 короткие задачи для тренировки.</p></div><Button variant="outline" onClick={() => onNavigate("Задания")}>Открыть задачи</Button></div>
          </section>
          <section className="feature-card feature-card--wide"><div className="feature-head"><div><span>ДОСТИЖЕНИЯ ФСП</span><strong>Спортивное программирование</strong></div></div><div className="achievement-grid"><div><b>◆</b><strong>Призёр ИТМО 2024</strong><span>Алгоритмическое программирование</span></div><div><b>◆</b><strong>Финалист хакатона ФСП</strong><span>Продуктовое программирование</span></div></div></section>
          <section className="feature-card"><div className="feature-head"><div><span>ОЦЕНКА ДОВЕРИЯ</span><strong>Доверие к профилю</strong></div></div><div className="trust-large">0,92</div><p className="feature-description">Расхождений между версиями резюме не обнаружено.</p></section>
          <section className="feature-card feature-card--wide"><div className="feature-head"><div><span>МОИ НАПРАВЛЕНИЯ</span><strong>Карты навыков</strong></div></div><div className="secondary-radars"><div><Radar values={[6,7,5,6,8,5]} target={[6,6,6,6,6,6]} compact /><strong>Дизайн</strong></div><div><Radar values={[7,6,8,7,6,7]} target={[6,6,6,6,6,6]} compact /><strong>Управление проектами</strong></div></div></section>
          <section className="feature-card"><div className="feature-head"><div><span>ИСТОРИЯ ТЕСТОВ</span><strong>Последние результаты</strong></div></div><div className="history-table history-table--tests"><div><span>12.05.2025</span><strong>Middle</strong><b>Подтверждён</b><em>8,1</em></div><div><span>18.02.2025</span><strong>Middle</strong><b>Требуется развитие</b><em>6,4</em></div></div></section>
        </div>
        {historyOpen && (
          <ModalShell eyebrow="ИСТОРИЯ" title="Результаты тестов" onClose={() => setHistoryOpen(false)}>
            <div className="history-table history-table--tests"><div><span>12.05.2025</span><strong>Backend Middle</strong><b>Подтверждён</b><em>8,1</em></div><div><span>18.02.2025</span><strong>Backend Middle</strong><b>Требуется развитие</b><em>6,4</em></div><div><span>09.11.2024</span><strong>Junior</strong><b>Подтверждён</b><em>7,2</em></div></div>
          </ModalShell>
        )}
        {planOpen && (
          <ModalShell eyebrow="РАЗВИТИЕ" title="Путь к Senior" onClose={() => setPlanOpen(false)}>
            <p className="feature-description feature-description--left">Сфокусируйтесь на двух зонах роста. После коротких задач карта навыков обновится без полного ретеста.</p>
            <div className="funnel"><div><span>CI/CD</span><strong>6 → 7</strong><Progress value={60} /></div><div><span>Тестирование</span><strong>6 → 7</strong><Progress value={60} /></div></div>
            <div className="modal__actions"><Button onClick={() => { setPlanOpen(false); onNavigate("Задания"); }}>Перейти к задачам</Button></div>
          </ModalShell>
        )}
      </div>
    );
  }

  if (active === "Задания") {
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

  if (active === "Вакансии") {
    return (
      <div className="page-content">
        <div className="tab-row"><button type="button" className="active">Все вакансии</button><button type="button">Мои отклики <span>{applied.length}</span></button><button type="button">Просмотрены</button><button type="button">Приняты</button></div>
        {applied.length > 0 && <div className="application-status"><Icon name="check" /><div><strong>Последний отклик отправлен</strong><span>Статус: отправлен · работодатель ещё не просмотрел профиль</span></div><Button variant="ghost">Все статусы</Button></div>}
        <div className="bank-toolbar"><div className="search-field search-field--wide"><Icon name="search" /><input placeholder="Название, компания или технология" /></div><Button variant="outline" onClick={() => setJobFilters(true)}><Icon name="filter" /> Фильтры</Button></div>
        {jobFilters && (
          <ModalShell eyebrow="ФИЛЬТРЫ" title="Вакансии под ваш профиль" onClose={() => setJobFilters(false)}>
            <div className="field-row field-row--flush"><label className="field"><span>УРОВЕНЬ</span><select><option>Middle</option><option>Senior</option></select></label><label className="field"><span>ФОРМАТ</span><select><option>Удалённо</option><option>Гибрид</option></select></label></div>
            <div className="modal__actions"><Button onClick={() => { setJobFilters(false); onNotify("Фильтры вакансий обновлены"); }}>Применить</Button></div>
          </ModalShell>
        )}
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
        <section className="feature-card"><div className="feature-head"><div><span>ПРИВАТНОСТЬ</span><strong>Видимость профиля</strong></div></div><ToggleRow title="Виден работодателям" detail="Профиль участвует в поиске и подборках" checked /><ToggleRow title="Показывать карту навыков" detail="Работодатели видят подтверждённые компетенции" checked /><ToggleRow title="Показывать достижения" detail="Достижения влияют на ранжирование" checked /><ToggleRow title="Показывать оценку доверия" detail="Без деталей проверки резюме" checked /></section>
        <section className="feature-card form-card"><div className="feature-head"><div><span>СОГЛАСИЯ И ИНТЕГРАЦИИ</span><strong>Данные профиля</strong></div></div><ToggleRow title="Обработка персональных данных" detail="Согласие по 152-ФЗ" checked /><ToggleRow title="OSINT-проверка" detail="Сравнение истории резюме" checked /><div className="integration-card"><div className="fsp-symbol">◆</div><div><strong>ФСП ID подключён</strong><span>FSP-2024-01842 · 2 достижения</span></div><Button variant="outline" onClick={() => setFspOpen(true)}>Управление</Button></div><Button onClick={() => { setSaved(true); onNotify("Настройки сохранены"); }}>{saved ? "Настройки сохранены" : "Сохранить настройки"}</Button></section>
      </div>
      {fspOpen && (
        <ModalShell eyebrow="ФСП ID" title="Связанный спортивный профиль" onClose={() => setFspOpen(false)}>
          <label className="field field--flush"><span>ИДЕНТИФИКАТОР</span><input defaultValue="FSP-2024-01842" /></label>
          <p className="feature-description feature-description--left">Отключение скроет достижения из ранжирования, но история тестов сохранится.</p>
          <div className="modal__actions"><Button variant="outline" onClick={() => { setFspOpen(false); onNotify("ФСП ID отключён"); }}>Отвязать</Button><Button onClick={() => { setFspOpen(false); onNotify("ФСП ID сохранён"); }}>Сохранить</Button></div>
        </ModalShell>
      )}
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
  const [version, setVersion] = useState<"current" | "2024" | "2023">("current");
  const versionNote = version === "current"
    ? candidate.about
    : version === "2024"
      ? `${candidate.about} Версия сохранена до последнего обновления опыта.`
      : "Ранняя версия профиля: меньше подтверждённых навыков и опыта, указано первое место работы.";
  const trustFlag = candidate.trust < 0.78
    ? "Есть расхождение в длительности одного из мест работы. Опыт мог быть завышен."
    : candidate.trust < 0.88
      ? "Часть опыта требует дополнительного подтверждения документами."
      : "Критичных расхождений в истории резюме не обнаружено.";

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
              <Radar values={candidate.radar} target={candidate.jobRadar} compact />
              <div className="compare-facts">
                <div><span>Уровень</span><strong>{candidate.level}</strong></div>
                <div><span>Опыт</span><strong>{candidate.experience}</strong></div>
                <div><span>Зарплата</span><strong>{candidate.salary}</strong></div>
                <div><span>Доверие</span><strong>{candidate.trust.toFixed(2).replace(".", ",")}</strong></div>
                <div><span>Город</span><strong>{candidate.location}</strong></div>
                <div><span>Формат</span><strong>{candidate.format}</strong></div>
              </div>
              <div className="tags">{candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
              <div className="compare-summary"><span>ПОЧЕМУ В ПОДБОРКЕ</span><p>{candidate.summary}</p><b>{candidate.gap}</b></div>
              <Button variant="outline" onClick={() => onOpen(candidate)}>Открыть полное резюме</Button>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProductTour({
  steps,
  onFinish,
  onNeedTab,
}: {
  steps: { tab: string; target: string; title: string; text: string }[];
  onFinish: () => void;
  onNeedTab: (tab: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const item = steps[step];

  useEffect(() => {
    onNeedTab(item.tab);
  }, [item.tab, onNeedTab]);

  useEffect(() => {
    const update = () => {
      const el = document.querySelector(item.target);
      setRect(el ? el.getBoundingClientRect() : null);
    };
    const timer = window.setTimeout(update, 60);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [item.target, item.tab, step]);

  const popoverStyle = rect
    ? {
        top: Math.min(rect.bottom + 14, window.innerHeight - 240),
        left: Math.min(Math.max(16, rect.left), window.innerWidth - 380),
      }
    : { top: "50%", left: "50%", transform: "translate(-50%, -50%)" };

  return (
    <div className="tour-layer">
      <button type="button" className="tour-dim" aria-label="Пропустить подсказки" onClick={onFinish} />
      {rect && (
        <div
          className="tour-spot"
          style={{
            top: rect.top - 10,
            left: rect.left - 10,
            width: rect.width + 20,
            height: rect.height + 20,
          }}
        />
      )}
      <div className="tour-popover" style={popoverStyle}>
        <span>ПОДСКАЗКА {step + 1} / {steps.length}</span>
        <strong>{item.title}</strong>
        <p>{item.text}</p>
        <div className="guide-actions">
          <Button variant="ghost" onClick={onFinish}>Пропустить</Button>
          <Button onClick={() => (step === steps.length - 1 ? onFinish() : setStep(step + 1))}>
            {step === steps.length - 1 ? "Понятно" : "Далее"} <Icon name="chevron" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function AuthScreen({ onLogin }: { onLogin: (role: "employer" | "candidate", isNew: boolean) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [selectedRole, setSelectedRole] = useState<"employer" | "candidate">("candidate");
  const [email, setEmail] = useState("demo@fsp-career.ru");
  const [password, setPassword] = useState("demo2025");
  const [confirmed, setConfirmed] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [code, setCode] = useState("");

  return (
    <div className="auth-page">
      <div className="auth-brand">
        <Logo />
        <span>КАРЬЕРА С ПОДТВЕРЖДЁННЫМИ НАВЫКАМИ</span>
        <strong>Работа, где сначала смотрят на то, что вы умеете</strong>
        <p>Подтвердите навыки тестом или достижениями ФСП, получите понятную карту компетенций и предложения с зарплатой.</p>
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
        <p>{mode === "login" ? "Используйте демонстрационные данные или свой email." : "Выберите роль — позже её можно будет изменить."}</p>
        <div className="auth-role">
          <button type="button" className={selectedRole === "candidate" ? "active" : ""} onClick={() => setSelectedRole("candidate")}><Icon name="users" /><strong>Кандидат</strong><span>Ищу предложения</span></button>
          <button type="button" className={selectedRole === "employer" ? "active" : ""} onClick={() => setSelectedRole("employer")}><Icon name="briefcase" /><strong>Компания</strong><span>Ищу специалистов</span></button>
        </div>
        {!emailSent ? (
          <>
            <label className="field field--flush"><span>EMAIL</span><input value={email} onChange={(event) => setEmail(event.target.value)} type="email" /></label>
            <label className="field field--flush"><span>ПАРОЛЬ</span><input value={password} onChange={(event) => setPassword(event.target.value)} type="password" /></label>
            {mode === "register" && <label className="auth-consent"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>Согласен на обработку персональных данных по 152-ФЗ</span></label>}
            <Button className={(!email || !password || (mode === "register" && !confirmed)) ? "button--disabled" : ""} onClick={() => { if (!email || !password || (mode === "register" && !confirmed)) return; if (mode === "register") setEmailSent(true); else onLogin(selectedRole, false); }}>
              {mode === "login" ? "Войти в кабинет" : "Подтвердить email"} <Icon name="chevron" />
            </Button>
          </>
        ) : (
          <div className="email-confirm">
            <div className="result-check"><Icon name="send" /></div>
            <strong>Письмо отправлено</strong>
            <p>Введите код, который мы отправили на {email}. Для демонстрации подойдёт любой код из четырёх цифр.</p>
            <label className="field field--flush"><span>КОД ПОДТВЕРЖДЕНИЯ</span><input value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="0000" inputMode="numeric" /></label>
            <Button className={code.length !== 4 ? "button--disabled" : ""} onClick={() => code.length === 4 && onLogin(selectedRole, true)}>Подтвердить и продолжить</Button>
            <button type="button" className="manual-link" onClick={() => setEmailSent(false)}>Изменить email</button>
          </div>
        )}
        <div className="auth-sso"><span>или</span><Button variant="outline">Продолжить через ФСП ID</Button><small>Подготовлена совместимость с Keycloak и OAuth 2.0</small></div>
      </div>
    </div>
  );
}

function CandidateOnboarding({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [consent, setConsent] = useState(false);
  const [specialization, setSpecialization] = useState("Backend");
  const [grade, setGrade] = useState("Middle");
  const [city, setCity] = useState("Москва");
  const [format, setFormat] = useState("Удалённо");
  const [fspId, setFspId] = useState("");
  const [osint, setOsint] = useState(false);
  const steps = ["Согласие", "Специализация", "Формат работы", "Резюме", "ФСП и проверка"];
  const canContinue = step !== 0 || consent;

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <Logo />
        <div className="onboarding-progress">{steps.map((item, index) => <div key={item} className={index <= step ? "active" : ""}><b>{index + 1}</b><span>{item}</span></div>)}</div>
        <div className="onboarding-content">
          {step === 0 && <><span>ШАГ 1</span><strong>Согласие на обработку данных</strong><p>Это необходимо, чтобы хранить профиль и показывать его выбранным работодателям.</p><label className="consent-large"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>Я согласен на обработку персональных данных по 152-ФЗ и публикацию профиля в выбранном режиме видимости.</span></label></>}
          {step === 1 && <><span>ШАГ 2</span><strong>Выберите направление и уровень</strong><p>Позже уровень можно подтвердить только тестом; достижения ФСП показываются отдельно.</p><div className="field-row field-row--flush"><label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={specialization} onChange={(event) => setSpecialization(event.target.value)}>{["Backend", "Frontend", "QA", "DevOps", "Data Science", "Информационная безопасность", "Product Manager", "Системный аналитик", "Дизайн", "Партнёрства", "Ивенты", "Project Management"].map((item) => <option key={item}>{item}</option>)}</select></label><label className="field"><span>ПРЕДПОЛАГАЕМЫЙ УРОВЕНЬ</span><select value={grade} onChange={(event) => setGrade(event.target.value)}>{["Junior", "Middle", "Senior", "Lead"].map((item) => <option key={item}>{item}</option>)}</select></label></div></>}
          {step === 2 && <><span>ШАГ 3</span><strong>Где и как вы хотите работать</strong><div className="field-row field-row--flush"><label className="field"><span>ГОРОД</span><input value={city} onChange={(event) => setCity(event.target.value)} /></label><label className="field"><span>ФОРМАТ</span><select value={format} onChange={(event) => setFormat(event.target.value)}><option>Удалённо</option><option>Гибрид</option><option>Офис</option></select></label></div><ToggleRow title="Готов к переезду" detail="Работодатели смогут учитывать это при подборе" /></>}
          {step === 3 && <><span>ШАГ 4</span><strong>Добавьте резюме</strong><p>PDF будет распознан: система извлечёт имя, контакты, компании, даты и навыки. Всё можно исправить перед сохранением.</p><div className="upload-box"><Icon name="briefcase" size={28} /><strong>Перетащите PDF сюда</strong><span>PyMuPDF и spaCy предзаполнят профиль</span><Button variant="outline">Выбрать файл</Button></div><button type="button" className="manual-link">Заполнить резюме вручную</button></>}
          {step === 4 && <><span>ШАГ 5</span><strong>Свяжите достижения ФСП</strong><p>ФСП ID может показать доступные тестовые записи достижений. Если ID нет, профиль продолжит работать.</p><label className="field field--flush"><span>ФСП ID · НЕОБЯЗАТЕЛЬНО</span><input value={fspId} onChange={(event) => setFspId(event.target.value)} placeholder="Например, FSP-2025-00142" /></label><label className="consent-large"><input type="checkbox" checked={osint} onChange={(event) => setOsint(event.target.checked)} /><span>Разрешаю проверку истории резюме для расчёта оценки доверия. Без согласия будет установлено нейтральное значение 0,50.</span></label></>}
        </div>
        <div className="onboarding-actions"><Button variant="ghost" onClick={() => setStep(Math.max(0, step - 1))}>{step === 0 ? "Вернуться ко входу" : "Назад"}</Button><Button className={!canContinue ? "button--disabled" : ""} onClick={() => canContinue && (step === steps.length - 1 ? onComplete() : setStep(step + 1))}>{step === steps.length - 1 ? "Завершить настройку" : "Далее"} <Icon name="chevron" /></Button></div>
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
  const candidate = items[index % items.length];

  const move = (nextDirection: "left" | "right") => {
    setDirection(nextDirection);
    window.setTimeout(() => {
      if (nextDirection === "right") onNotify(`${candidate.name} добавлен в список интересных`);
      setIndex((current) => current + 1);
      setDirection(null);
    }, 320);
  };

  return (
    <div className="swipe-workspace">
      <div className="swipe-deck">
        <article className={`swipe-card ${direction ? `swipe-card--${direction}` : ""}`}>
          <div className="swipe-card__cover">
            <div className="resume-avatar">{candidate.initials}</div>
            <div><span>ПОДТВЕРЖДЁННЫЙ ПРОФИЛЬ</span><strong>{candidate.name}</strong><p>{candidate.role} · {candidate.level} · {candidate.location}</p></div>
            <div className="resume-match"><span>Совпадение</span><strong>{candidate.score}%</strong></div>
          </div>
          <div className="swipe-card__body">
            <Radar values={candidate.radar} target={candidate.jobRadar} compact />
            <div className="swipe-details">
              <p>{candidate.summary}</p>
              <div className="swipe-facts">
                <div><span>Опыт</span><strong>{candidate.experience}</strong></div>
                <div><span>Ожидания</span><strong>{candidate.salary}</strong></div>
                <div><span>Формат</span><strong>{candidate.format}</strong></div>
                <div><span>Доверие</span><strong>{candidate.trust.toFixed(2).replace(".", ",")}</strong></div>
              </div>
              <div className="tags">{candidate.skills.slice(0, 5).map((skill) => <span key={skill}>{skill}</span>)}</div>
              {candidate.achievements[0] && <div className="swipe-achievement">◆ {candidate.achievements[0]}</div>}
            </div>
          </div>
        </article>
        <div className="swipe-rail">
          <button type="button" className="swipe-action swipe-action--skip" onClick={() => move("left")}><Icon name="close" /><span>Пропустить</span></button>
          <button type="button" className="swipe-action swipe-action--open" onClick={() => onOpen(candidate)}><Icon name="users" /><span>Резюме</span></button>
          <button type="button" className="swipe-action swipe-action--save" onClick={() => { move("right"); onInvite(candidate); }}><Icon name="check" /><span>Интересен</span></button>
          <div className="swipe-counter">{index + 1} / {items.length}</div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(() => window.localStorage.getItem("fsp-auth") === "true");
  const [onboarding, setOnboarding] = useState(false);
  const [role, setRole] = useState<"employer" | "candidate">("employer");
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.localStorage.getItem("fsp-theme") === "dark" ? "dark" : "light",
  );
  const [active, setActive] = useState("Подборка");
  const [selectedId, setSelectedId] = useState(1);
  const [query, setQuery] = useState("");
  const [onlyFsp, setOnlyFsp] = useState(false);
  const [compare, setCompare] = useState<number[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [notice, setNotice] = useState("");
  const [resumeCandidate, setResumeCandidate] = useState<Candidate | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "swipe">("list");
  const [accountOpen, setAccountOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(
    () => window.localStorage.getItem("fsp-auth") === "true" && window.localStorage.getItem("fsp-tour-seen-employer") !== "true",
  );

  useEffect(() => {
    window.localStorage.setItem("fsp-theme", theme);
  }, [theme]);

  const filtered = useMemo(
    () =>
      candidates.filter(
        (candidate) =>
          (!onlyFsp || candidate.achievements.length > 0) &&
          `${candidate.name} ${candidate.skills.join(" ")}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [onlyFsp, query],
  );
  const selected =
    candidates.find((candidate) => candidate.id === selectedId) ?? candidates[0];

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

  const switchRole = (nextRole: "employer" | "candidate") => {
    setRole(nextRole);
    setActive(nextRole === "employer" ? "Подборка" : "Обзор");
  };

  const showNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3500);
  };

  const login = (nextRole: "employer" | "candidate", isNew: boolean) => {
    window.localStorage.setItem("fsp-auth", "true");
    setAuthenticated(true);
    switchRole(nextRole);
    setOnboarding(isNew && nextRole === "candidate");
    const tourKey = `fsp-tour-seen-${nextRole}`;
    setTourOpen(!isNew || nextRole === "employer" ? window.localStorage.getItem(tourKey) !== "true" : false);
  };

  const logout = () => {
    window.localStorage.removeItem("fsp-auth");
    setAuthenticated(false);
    setAccountOpen(false);
    setNavOpen(false);
  };

  const finishTour = () => {
    window.localStorage.setItem(`fsp-tour-seen-${role}`, "true");
    setTourOpen(false);
  };

  const employerTour = [
    { tab: "Подборка", target: "[data-tour=nav]", title: "Разделы кабинета", text: "Слева — обзор, подборка, база, потребности и настройки. Наведите на пункт, чтобы увидеть, что внутри." },
    { tab: "Подборка", target: "[data-tour=need]", title: "Активная потребность", text: "Подборка строится вокруг этой роли. Здесь же можно изменить описание и веса навыков." },
    { tab: "Подборка", target: "[data-tour=view]", title: "База и свайп", text: "База — список с сравнением справа. Свайп — карточка и действия в одном экране, без прокрутки вниз." },
    { tab: "Подборка", target: "[data-tour=invite]", title: "Пригласить", text: "Зарплата уходит кандидату сразу. Контакты откроются только после его согласия." },
    { tab: "Настройки", target: "[data-tour=company-form]", title: "Профиль компании", text: "Название, контакты и логотип. Сохраните изменения — они попадут в приглашения." },
  ];
  const candidateTour = [
    { tab: "Обзор", target: "[data-tour=nav]", title: "Ваш кабинет", text: "Профиль, тест, грейд, задания и вакансии. Подсказка появляется при наведении на пункт меню." },
    { tab: "Обзор", target: "[data-tour=role]", title: "Роль", text: "Переключатель в шапке меняет кабинет компании и кандидата — удобно для демонстрации." },
    { tab: "Профиль", target: "[data-tour=candidate-profile]", title: "Профиль и резюме", text: "Здесь фото, опыт и PDF. Работодатель видит только то, что вы разрешили в настройках." },
  ];

  const toggleCompare = (id: number) => {
    setCompare((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length < 3
          ? [...current, id]
          : current,
    );
  };

  const submitInvite = () => {
    setSent(true);
    window.setTimeout(() => {
      setInviteOpen(false);
      setSent(false);
      showNotice(`Приглашение для ${selected.name} отправлено`);
    }, 700);
  };

  if (!authenticated) {
    return <AuthScreen onLogin={login} />;
  }

  if (onboarding) {
    return <CandidateOnboarding onComplete={() => { setOnboarding(false); setTourOpen(window.localStorage.getItem("fsp-tour-seen-candidate") !== "true"); showNotice("Профиль создан — можно подтвердить навыки"); }} />;
  }

  return (
    <div className={`app-shell ${navOpen ? "app-shell--nav-open" : ""}`} data-theme={theme}>
      <button type="button" className="nav-backdrop" aria-label="Закрыть меню" onClick={() => setNavOpen(false)} />
      <aside className="sidebar" data-tour="nav">
        <Logo />
        <div className="workspace-label">{role === "employer" ? "РАБОТОДАТЕЛЬ" : "СОИСКАТЕЛЬ"}</div>
        <nav className="nav">
          {nav.map(([icon, item]) => (
            <div className="nav-group-wrap" key={item}>
              {groupLabels[item] && <div className="nav-group-label">{groupLabels[item]}</div>}
              <button
                type="button"
                data-tooltip={navHints[item] ?? item}
                className={`nav__item ${active === item ? "nav__item--active" : ""}`}
                onClick={() => { setActive(item); setNavOpen(false); }}
              >
                <Icon name={icon} />
                <span>{item}</span>
                {item === "Приглашения" && <b>3</b>}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <button type="button" className="company" onClick={() => setAccountOpen(true)}>
            <div className="company__avatar">{role === "employer" ? "NT" : "АМ"}</div>
            <div>
              <strong>{role === "employer" ? "NovaTech" : "Алексей Морозов"}</strong>
              <span>{role === "employer" ? "tech@novatech.ru" : "alexey@example.ru"}</span>
            </div>
            <Icon name="chevron" size={15} />
          </button>
          <button type="button" className="logout-button" onClick={logout}>Выйти из аккаунта</button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar__lead">
            <button type="button" className="nav-toggle" aria-label="Открыть меню" onClick={() => setNavOpen(true)}>
              <Icon name="menu" />
            </button>
            <div>
              <div className="eyebrow">{currentCopy.eyebrow}</div>
              <div className="page-title">{currentCopy.title}</div>
            </div>
          </div>
          <div className="topbar__actions">
            <div className="role-switch" data-tour="role">
              <button type="button" className={role === "employer" ? "active" : ""} onClick={() => switchRole("employer")}>Компания</button>
              <button type="button" className={role === "candidate" ? "active" : ""} onClick={() => switchRole("candidate")}>Кандидат</button>
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
            <button type="button" className="icon-button" aria-label="Уведомления" onClick={() => setNotesOpen(true)}>
              <Icon name="bell" />
              <i />
            </button>
            {role === "employer" ? (
              <Button variant="outline" onClick={() => setActive("Потребности")}>
                <span className="button-plus">+</span> Потребность
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setActive("Профиль")}>Профиль</Button>
            )}
          </div>
        </header>

        {role === "employer" && active === "Подборка" ? (
          <div className="selection-stage">
        <section className="need-summary" data-tour="need">
          <div className="need-summary__icon">
            <Icon name="briefcase" size={21} />
          </div>
          <div className="need-summary__main">
            <div className="need-summary__top">
              <div>
                <span className="muted-label">АКТИВНАЯ ПОТРЕБНОСТЬ</span>
                <strong>Backend-разработчик · Middle</strong>
              </div>
              <span className="status"><i /> Подбор активен</span>
            </div>
            <div className="need-summary__meta">
              <span>Python / Go</span>
              <span>PostgreSQL</span>
              <span>REST / gRPC</span>
              <span>220–280 тыс. ₽</span>
              <span>Удалённо / гибрид</span>
            </div>
          </div>
          <Button variant="ghost" onClick={() => setActive("Потребности")}>Изменить</Button>
        </section>

        <section className="toolbar">
          <div className="search-field">
            <Icon name="search" />
            <input
              aria-label="Поиск по навыкам или имени"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Имя или навык"
            />
          </div>
          <Button
            variant={onlyFsp ? "primary" : "outline"}
            onClick={() => setOnlyFsp((value) => !value)}
          >
            <Icon name="filter" /> ФСП
          </Button>
          <div className="view-switch" data-tour="view">
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
          <section className="candidates-list">
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
                  setResumeCandidate(candidate);
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
                    <div>{candidate.role} · {candidate.level}</div>
                  </div>
                  <div className="match">
                    <strong>{candidate.score}%</strong>
                    <span>СОВПАДЕНИЕ</span>
                  </div>
                </div>
                <div className="candidate-card__middle">
                  <Radar values={candidate.radar} target={candidate.jobRadar} compact />
                  <div className="candidate-card__facts">
                    <div>
                      <span>Опыт</span>
                      <strong>{candidate.experience}</strong>
                    </div>
                    <div>
                      <span>Ожидания</span>
                      <strong>{candidate.salary}</strong>
                    </div>
                    <div>
                      <span>Формат</span>
                      <strong>{candidate.format}</strong>
                    </div>
                    <div>
                      <span>Доверие</span>
                      <strong className="trust"><i /> {candidate.trust.toFixed(2).replace(".", ",")}</strong>
                    </div>
                  </div>
                </div>
                <div className="tags">
                  {candidate.skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}
                  <span>+{Math.max(0, candidate.skills.length - 4)}</span>
                </div>
                <div className="candidate-card__footer">
                  <span>Обновлён {candidate.updated}</span>
                  {candidate.achievements.length > 0 && (
                    <span className="fsp-badge">◆ {candidate.achievements[0]}</span>
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

          <aside className="profile-panel">
            <div className="profile-panel__head">
              <span>ПРОФИЛЬ КАНДИДАТА</span>
              <button type="button" aria-label="Закрыть профиль"><Icon name="close" /></button>
            </div>
            <div className="profile-hero">
              <div className="avatar avatar--large">{selected.initials}</div>
              <div className="profile-hero__main">
                <div className="profile-hero__name">{selected.name}</div>
                <div className="profile-hero__role">{selected.role}</div>
                <div className="profile-hero__meta">{selected.location} · {selected.format}</div>
              </div>
            </div>
            <div className="grade-line">
              <div>
                <span>ПОДТВЕРЖДЁННЫЙ УРОВЕНЬ</span>
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
              <Radar values={selected.radar} target={selected.jobRadar} />
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
              <div><span>ОЦЕНКА ДОВЕРИЯ</span><strong><i /> {selected.trust.toFixed(2).replace(".", ",")}</strong><small>Без расхождений</small></div>
              <div><span>ФСП</span><strong>{selected.achievements.length || "—"}</strong><small>{selected.achievements.length ? "достижения" : "Нет истории"}</small></div>
              <div><span>АКТУАЛЬНОСТЬ</span><strong>98%</strong><small>Активен</small></div>
            </div>
            <div className="profile-panel__actions" data-tour="invite">
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
          </aside>
        </div>
        )}
          </div>
        ) : role === "employer" ? (
          <EmployerScreen
            active={active}
            onOpenCandidates={() => setActive("Подборка")}
            onOpenResume={setResumeCandidate}
            onNotify={showNotice}
          />
        ) : (
          <CandidateScreen active={active} onNotify={showNotice} onNavigate={setActive} />
        )}
      </main>

      {role === "employer" && active === "Подборка" && compare.length > 0 && (
        <div className="compare-bar">
          <div className="compare-bar__avatars">
            {compare.map((id) => {
              const candidate = candidates.find((item) => item.id === id)!;
              return <span key={id}>{candidate.initials}</span>;
            })}
          </div>
          <div>
            <strong>{compare.length} из 3 кандидатов</strong>
            <span>Выберите минимум двух для сравнения карт навыков</span>
          </div>
          <Button variant="ghost" onClick={() => setCompare([])}>Очистить</Button>
          <Button
            disabled={compare.length < 2}
            onClick={() => setCompareOpen(true)}
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
              <textarea defaultValue="Приглашаем в продуктовую команду NovaTech. Вы будете развивать API платформы и работать с высоконагруженными сервисами." />
            </label>
            <div className="field-row">
              <label className="field">
                <span>ЗАРПЛАТА ОТ, ₽</span>
                <input defaultValue="220 000" />
              </label>
              <label className="field">
                <span>ЗАРПЛАТА ДО, ₽</span>
                <input defaultValue="280 000" />
              </label>
            </div>
            <label className="field">
              <span>СПОСОБ СВЯЗИ</span>
              <input defaultValue="Telegram / корпоративная почта" />
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
            setResumeCandidate(null);
            setInviteOpen(true);
          }}
        />
      )}

      {role === "employer" && compareOpen && (
        <CompareModal
          items={compare
            .map((id) => candidates.find((candidate) => candidate.id === id))
            .filter((candidate): candidate is Candidate => Boolean(candidate))}
          onClose={() => setCompareOpen(false)}
          onOpen={(candidate) => {
            setCompareOpen(false);
            setResumeCandidate(candidate);
            setResumeCandidate(candidate);
          }}
        />
      )}

      {accountOpen && (
        <ModalShell eyebrow="АККАУНТ" title={role === "employer" ? "NovaTech" : "Алексей Морозов"} onClose={() => setAccountOpen(false)}>
          <div className="account-sheet">
            <div className="company-logo-upload">
              <div className="company__avatar">{role === "employer" ? "NT" : "АМ"}</div>
              <div><strong>{role === "employer" ? "tech@novatech.ru" : "alexey@example.ru"}</strong><span>Сессия демо-аккаунта</span></div>
            </div>
            <Button variant="outline" onClick={() => { setAccountOpen(false); setActive("Настройки"); }}>Открыть настройки</Button>
            <Button variant="outline" onClick={() => { setAccountOpen(false); setTourOpen(true); }}>Показать подсказки</Button>
            <Button variant="danger" onClick={logout}>Выйти из аккаунта</Button>
          </div>
        </ModalShell>
      )}

      {notesOpen && (
        <ModalShell eyebrow="УВЕДОМЛЕНИЯ" title="Что произошло" onClose={() => setNotesOpen(false)}>
          <div className="activity-list">
            <div><i className="activity-dot activity-dot--green" /><p><strong>Алексей Морозов</strong> принял приглашение</p><span>12 мин</span></div>
            <div><i className="activity-dot" /><p>В подборке Backend появились <strong>4 новых кандидата</strong></p><span>1 ч</span></div>
            <div><i className="activity-dot activity-dot--red" /><p><strong>Елена Смирнова</strong> просмотрела предложение</p><span>3 ч</span></div>
          </div>
        </ModalShell>
      )}

      {tourOpen && (
        <ProductTour
          steps={role === "employer" ? employerTour : candidateTour}
          onFinish={finishTour}
          onNeedTab={setActive}
        />
      )}

      {notice && <div className="toast"><Icon name="check" /> {notice}</div>}
    </div>
  );
}

export default App;
