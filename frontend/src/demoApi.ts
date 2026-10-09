type DemoRole = "candidate" | "employer";

type DemoCandidate = {
  candidate_id: string;
  first_name: string;
  last_name: string;
  specialization: string;
  verified_grade: string;
  declared_grade: string;
  city: string;
  work_format: string;
  fsp_verified: boolean;
  achievements_count: number;
  skills: string[];
  salary_expectation?: number | null;
  salary_tax_type?: "gross" | "net";
  match_score: number;
  available_from: string;
  trust_score: number;
  trust_flags: Array<{ label: string; status: "verified" | "review" | "warning"; detail: string }>;
  resume_versions: Array<{ id: string; label: string; date: string; summary: string }>;
  match_explanation: { summary: string; matched_skills: string[]; missing_skills: string[]; salary_match?: boolean; salary_note?: string };
};

type DemoNeed = {
  id: string;
  employer_id: string;
  company_name: string;
  title: string;
  specialization: string;
  required_grade: string;
  required_skills: Array<{ name: string; weight: number; required: boolean }>;
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
  currency: string;
  work_format: string;
  city: string;
  description: string;
  is_active: boolean;
  created_at: string;
};

type DemoInvitation = {
  id: string;
  employer_id: string;
  company_name: string;
  candidate_id: string;
  candidate_name: string;
  need_id: string | null;
  need_title: string | null;
  offer_description: string;
  contact_method: string;
  salary_min: number;
  salary_max: number;
  currency: string;
  status: string;
  candidate_reply: string | null;
  created_at: string;
  accepted_at: string | null;
  candidate_contacts: { email: string; phone: string; telegram: string } | null;
};

type DemoInvitationMessage = {
  id: string;
  invitation_id: string;
  sender_role: DemoRole;
  body: string;
  created_at: string;
  read: boolean;
};

type DemoVacancy = {
  id: string;
  employer_id: string;
  title: string;
  specialization: string;
  required_grade: string;
  required_skills: string[];
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
  currency: string;
  work_format: string;
  city: string | null;
  description: string;
  is_published: boolean;
  created_at: string;
  updated_at: string;
  company: { id: string; company_name: string; industry: string; website: string; city: string };
};

type DemoVacancyApplication = {
  id: string;
  vacancy_id: string;
  status: "pending" | "reviewed" | "accepted" | "rejected";
  cover_letter: string | null;
  created_at: string;
  status_updated_at: string | null;
  candidate_id: string;
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
  vacancy_title: string;
  company_name: string;
  salary_min: number;
  salary_max: number;
  salary_tax_type: "gross" | "net";
};

const candidateProfile = {
  first_name: "Алексей",
  last_name: "Морозов",
  email: "alexey.demo@example.ru",
  phone: "+7 900 000-00-01",
  telegram: "@alexey_demo",
  bio: "Backend-разработчик. Создаю API и сервисы обработки данных.",
  city: "Москва",
  specialization: "Backend",
  declared_grade: "middle",
  verified_grade: "middle",
  work_format: "remote",
  salary_expectation: 240000,
  salary_tax_type: "gross" as const,
  fsp_id: "FSP-77-001",
  fsp_verified: true,
  agreed_152_fz: true,
  agreed_publication: true,
  visibility_public: true,
  agreed_osint: true,
  mentor_available: false,
  onboarding_completed: true,
};

const employerProfile = {
  email: "demo@novatech.example",
  company_name: "NovaTech",
  description: "Продуктовая команда финансовых технологий.",
  industry: "FinTech",
  website: "https://example.com",
  contact_person: "Команда найма",
  phone: "+7 900 000-00-02",
  city: "Москва",
  onboarding_completed: true,
};

const candidates: DemoCandidate[] = [
  {
    candidate_id: "demo-candidate-alex",
    first_name: "Алексей",
    last_name: "Морозов",
    specialization: "Backend",
    verified_grade: "middle",
    declared_grade: "middle",
    city: "Москва",
    work_format: "remote",
    fsp_verified: true,
    achievements_count: 2,
    skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    salary_expectation: 250000,
    salary_tax_type: "gross",
    match_score: 94,
    available_from: "2026-10-15",
    trust_score: 0.92,
    trust_flags: [
      { label: "Опыт работы", status: "verified", detail: "Даты последовательны, перерывы объяснены." },
      { label: "Сроки в резюме", status: "verified", detail: "Подтверждённые периоды согласуются с профилем." },
      { label: "Навыки", status: "verified", detail: "Python и PostgreSQL подтверждены тестированием." },
    ],
    resume_versions: [
      { id: "current", label: "Текущая", date: "2026-10-01", summary: "Обновил описание архитектурных задач и добавил опыт разработки высоконагруженного API." },
      { id: "2025", label: "2025", date: "2025-05-18", summary: "Предыдущая версия: фокус на backend-разработке и оптимизации PostgreSQL." },
    ],
    match_explanation: { summary: "Подтверждённый Middle. Сильные API и базы данных. Зарплатные ожидания соответствуют («до вычета НДФЛ»).", matched_skills: ["Python", "PostgreSQL", "REST"], missing_skills: ["Kafka"], salary_match: true, salary_note: "Ожидания (250,000 ₽ до вычета НДФЛ) укладываются в бюджет вакансии" },
  },
  {
    candidate_id: "demo-candidate-elena",
    first_name: "Елена",
    last_name: "Смирнова",
    specialization: "Backend",
    verified_grade: "middle",
    declared_grade: "middle",
    city: "Санкт-Петербург",
    work_format: "hybrid",
    fsp_verified: true,
    achievements_count: 1,
    skills: ["Go", "gRPC", "PostgreSQL", "Kafka", "Kubernetes"],
    salary_expectation: 230000,
    salary_tax_type: "net",
    match_score: 89,
    available_from: "2026-11-01",
    trust_score: 0.88,
    trust_flags: [
      { label: "Опыт работы", status: "review", detail: "Один период указан только с точностью до года." },
      { label: "Сроки в резюме", status: "verified", detail: "Хронология мест работы не пересекается." },
      { label: "Навыки", status: "verified", detail: "Go и базы данных подтверждены результатом теста." },
    ],
    resume_versions: [
      { id: "current", label: "Текущая", date: "2026-09-27", summary: "Добавлен опыт с Kafka и эксплуатацией сервисов в Kubernetes." },
      { id: "2025", label: "2025", date: "2025-11-10", summary: "Предыдущая версия: Go, gRPC и проектирование API." },
    ],
    match_explanation: { summary: "Сильные распределённые системы и опыт с очередями. Требуется согласование налогового типа («на руки» vs «до вычета НДФЛ»).", matched_skills: ["PostgreSQL", "Kafka"], missing_skills: ["Python"], salary_match: false, salary_note: "Разный налоговый базис: потребность «до вычета НДФЛ», соискатель «на руки»" },
  },
  {
    candidate_id: "demo-candidate-dmitry",
    first_name: "Дмитрий",
    last_name: "Ким",
    specialization: "Backend",
    verified_grade: "middle",
    declared_grade: "middle",
    city: "Казань",
    work_format: "remote",
    fsp_verified: false,
    achievements_count: 0,
    skills: ["Python", "Django", "PostgreSQL", "Celery", "GitLab CI"],
    match_score: 84,
    available_from: "2026-10-21",
    trust_score: 0.76,
    trust_flags: [
      { label: "Возможное завышение стажа", status: "warning", detail: "Заявленный срок в одном месте работы длиннее подтверждённого. Это повод уточнить даты, не вывод о нарушении." },
      { label: "Сроки в резюме", status: "review", detail: "Попросите кандидата уточнить даты перед оффером." },
      { label: "Навыки", status: "verified", detail: "Python и PostgreSQL подтверждены тестированием." },
    ],
    resume_versions: [
      { id: "current", label: "Текущая", date: "2026-09-25", summary: "Уточнён стек Django, Celery и PostgreSQL." },
      { id: "2024", label: "2024", date: "2024-12-02", summary: "Предыдущая версия: первые backend-проекты и REST API." },
    ],
    match_explanation: { summary: "Уверенная работа с API и данными. История ФСП отсутствует.", matched_skills: ["Python", "PostgreSQL"], missing_skills: ["Kafka", "Docker"] },
  },
  {
    candidate_id: "demo-candidate-anna",
    first_name: "Анна",
    last_name: "Петрова",
    specialization: "Backend",
    verified_grade: "senior",
    declared_grade: "senior",
    city: "Новосибирск",
    work_format: "remote",
    fsp_verified: true,
    achievements_count: 1,
    skills: ["Java", "Spring", "Kafka", "PostgreSQL", "Kubernetes"],
    match_score: 91,
    available_from: "2026-12-01",
    trust_score: 0.95,
    trust_flags: [
      { label: "Опыт работы", status: "verified", detail: "Роли и даты подтверждаются профилем." },
      { label: "Сроки в резюме", status: "verified", detail: "Хронология согласована." },
      { label: "Навыки", status: "verified", detail: "Архитектура и Java подтверждены оценкой." },
    ],
    resume_versions: [
      { id: "current", label: "Текущая", date: "2026-10-03", summary: "Добавлено описание технического лидерства и платформенной архитектуры." },
      { id: "2025", label: "2025", date: "2025-08-14", summary: "Предыдущая версия: Senior backend-разработка и распределённые системы." },
    ],
    match_explanation: { summary: "Подтверждённый Senior. Сильные архитектура и эксплуатация.", matched_skills: ["PostgreSQL", "Kafka"], missing_skills: ["Python"] },
  },
];

const needs: DemoNeed[] = [
  {
    id: "demo-need-backend",
    employer_id: "demo-employer",
    company_name: "NovaTech",
    title: "Backend-разработчик",
    specialization: "Backend",
    required_grade: "middle",
    required_skills: [
      { name: "Python", weight: 1, required: true },
      { name: "PostgreSQL", weight: 0.9, required: true },
      { name: "REST", weight: 0.8, required: true },
      { name: "Docker", weight: 0.6, required: false },
    ],
    salary_min: 220000,
    salary_max: 280000,
    salary_tax_type: "gross",
    currency: "RUB",
    work_format: "remote",
    city: "Москва",
    description: "Разработка API продуктовой платформы.",
    is_active: true,
    created_at: "2026-10-01T10:00:00Z",
  },
  {
    id: "demo-need-devops",
    employer_id: "demo-employer",
    company_name: "NovaTech",
    title: "DevOps-инженер",
    specialization: "DevOps / SRE",
    required_grade: "middle",
    required_skills: [{ name: "Kubernetes", weight: 1, required: true }],
    salary_min: 230000,
    salary_max: 300000,
    salary_tax_type: "gross",
    currency: "RUB",
    work_format: "hybrid",
    city: "Москва",
    description: "Развитие инфраструктуры и CI/CD.",
    is_active: true,
    created_at: "2026-10-02T10:00:00Z",
  },
];

const invitations: DemoInvitation[] = [
  {
    id: "demo-invitation-1",
    employer_id: "demo-employer",
    company_name: "NovaTech",
    candidate_id: candidates[0].candidate_id,
    candidate_name: `${candidates[0].first_name} ${candidates[0].last_name}`,
    need_id: needs[0].id,
    need_title: needs[0].title,
    offer_description: "Приглашаем присоединиться к команде платформы и развивать высоконагруженный API.",
    contact_method: "Telegram: @novatech_demo",
    salary_min: 220000,
    salary_max: 280000,
    currency: "RUB",
    status: "sent",
    candidate_reply: null,
    created_at: "2026-10-03T12:00:00Z",
    accepted_at: null,
    candidate_contacts: null,
  },
  {
    id: "demo-invitation-2",
    employer_id: "demo-employer",
    company_name: "Яндекс Практикум",
    candidate_id: "demo-candidate-demo",
    candidate_name: "Алексей Морозов",
    need_id: null,
    need_title: "Backend-разработчик",
    offer_description: "Развитие продуктового API и участие в архитектурных решениях.",
    contact_method: "Почта: team@example.ru",
    salary_min: 200000,
    salary_max: 260000,
    currency: "RUB",
    status: "viewed",
    candidate_reply: null,
    created_at: "2026-10-04T12:00:00Z",
    accepted_at: null,
    candidate_contacts: null,
  },
];

invitations[1].status = "accepted";
invitations[1].accepted_at = "2026-10-04T15:30:00Z";
invitations[1].candidate_contacts = { email: "alexey.demo@example.ru", phone: "+7 900 000-00-01", telegram: "@alexey_demo" };

const invitationMessages: DemoInvitationMessage[] = [
  {
    id: "demo-message-1",
    invitation_id: "demo-invitation-2",
    sender_role: "employer",
    body: "Добрый день! Приглашаем обсудить задачи команды и условия сотрудничества.",
    created_at: "2026-10-04T15:30:00Z",
    read: false,
  },
];

const vacancies: DemoVacancy[] = [
  {
    id: "demo-vacancy-1",
    employer_id: "demo-employer",
    title: "Backend-разработчик",
    specialization: "Backend",
    required_grade: "middle",
    required_skills: ["Python", "FastAPI", "PostgreSQL", "Docker"],
    salary_min: 220000,
    salary_max: 280000,
    salary_tax_type: "gross",
    currency: "RUB",
    work_format: "remote",
    city: "Москва",
    description: "Развитие API финансовой платформы, работа с PostgreSQL и сервисами обработки событий.",
    is_published: true,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
    company: { id: "demo-company", company_name: "NovaTech", industry: "FinTech", website: "https://example.com", city: "Москва" },
  },
  {
    id: "demo-vacancy-2",
    employer_id: "demo-employer",
    title: "Инженер платформы данных",
    specialization: "Data Science / ML",
    required_grade: "middle",
    required_skills: ["Python", "SQL", "Docker"],
    salary_min: 230000,
    salary_max: 300000,
    salary_tax_type: "net",
    currency: "RUB",
    work_format: "hybrid",
    city: "Москва",
    description: "Разработка сервисов обработки данных и поддержка инфраструктуры аналитической платформы.",
    is_published: true,
    created_at: "2026-10-02T10:00:00Z",
    updated_at: "2026-10-02T10:00:00Z",
    company: { id: "demo-company", company_name: "NovaTech", industry: "FinTech", website: "https://example.com", city: "Москва" },
  },
];

const vacancyApplications: DemoVacancyApplication[] = [{
  id: "demo-application-seed-1",
  vacancy_id: "demo-vacancy-1",
  status: "reviewed",
  cover_letter: "Развиваю backend-сервисы на Python и FastAPI, работаю с PostgreSQL и очередями.",
  created_at: "2026-10-05T10:00:00Z",
  status_updated_at: "2026-10-05T13:00:00Z",
  candidate_id: "demo-candidate-alex",
  candidate: {
    first_name: candidateProfile.first_name,
    last_name: candidateProfile.last_name,
    email: candidateProfile.email,
    phone: candidateProfile.phone,
    telegram: candidateProfile.telegram,
    city: candidateProfile.city,
    specialization: candidateProfile.specialization,
    verified_grade: candidateProfile.verified_grade,
    skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
  },
  vacancy_title: vacancies[0].title,
  company_name: vacancies[0].company.company_name,
  salary_min: vacancies[0].salary_min,
  salary_max: vacancies[0].salary_max,
  salary_tax_type: vacancies[0].salary_tax_type,
}];
const vacancyApplicationMessages: Record<string, DemoInvitationMessage[]> = {
  "demo-application-seed-1": [
    {
      id: "demo-application-seed-message-1",
      invitation_id: "demo-application-seed-1",
      sender_role: "candidate",
      body: "Здравствуйте! Откликнулся на вакансию. Буду рад обсудить задачи платформенной команды.",
      created_at: "2026-10-05T10:00:00Z",
      read: true,
    },
    {
      id: "demo-application-seed-message-2",
      invitation_id: "demo-application-seed-1",
      sender_role: "employer",
      body: "Добрый день, Алексей! Спасибо за отклик. Посмотрим профиль и вернёмся с удобным временем для знакомства.",
      created_at: "2026-10-05T13:00:00Z",
      read: false,
    },
  ],
};

const questions = [
  {
    id: "demo-question-1",
    topic: "SQL и транзакции",
    question_type: "single_choice",
    question_text: "Какое свойство ACID отвечает за сохранность подтверждённых изменений после сбоя?",
    options: [{ id: "A", text: "Atomicity" }, { id: "B", text: "Consistency" }, { id: "C", text: "Isolation" }, { id: "D", text: "Durability" }],
    correct: "D",
  },
  {
    id: "demo-question-2",
    topic: "REST API",
    question_type: "single_choice",
    question_text: "Какой метод обычно используют для полного обновления ресурса?",
    options: [{ id: "A", text: "GET" }, { id: "B", text: "PUT" }, { id: "C", text: "TRACE" }, { id: "D", text: "CONNECT" }],
    correct: "B",
  },
  {
    id: "demo-question-3",
    topic: "Python и структуры данных",
    question_type: "single_choice",
    question_text: "Какова средняя сложность проверки наличия элемента в set Python?",
    options: [{ id: "A", text: "O(1)" }, { id: "B", text: "O(log n)" }, { id: "C", text: "O(n)" }, { id: "D", text: "O(n log n)" }],
    correct: "A",
  },
];

let testHistory: Array<Record<string, unknown>> = [];
let activeTestId: string | null = null;
let currentCandidateProfile = { ...candidateProfile };
let currentEmployerProfile = { ...employerProfile };
let nextNeedId = 3;
let nextInvitationId = 3;
const demoMentors = [
  { user_id: "demo-mentor-anna", name: "Анна Петрова", specialization: "Backend", verified_grade: "senior", skills: ["Python", "PostgreSQL", "Architecture", "Kafka"], city: "Москва" },
  { user_id: "demo-mentor-elena", name: "Елена Смирнова", specialization: "Backend", verified_grade: "senior", skills: ["Go", "Kafka", "Kubernetes", "gRPC"], city: "Санкт-Петербург" },
];
const networkConversations: Array<{
  id: string;
  other_user_id: string;
  other_name: string;
  skill_focus: string;
  status: "pending" | "accepted" | "rejected";
  can_accept: boolean;
  last_message: string;
  updated_at: string;
}> = [];
const networkMessages: Record<string, Array<{ id: string; body: string; created_at: string; is_mine: boolean }>> = {};

function currentRole(): DemoRole {
  return window.localStorage.getItem("fsp-role") === "employer" ? "employer" : "candidate";
}

function parseBody(options: RequestInit) {
  if (typeof options.body !== "string") return {};
  try {
    return JSON.parse(options.body) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function invitationsForCandidate() {
  return invitations.filter((item) => item.candidate_name.includes(currentCandidateProfile.first_name));
}

function createDemoProfilePdf() {
  const content = "BT\n/F1 18 Tf\n50 760 Td\n(FSP Career demo profile) Tj\n0 -30 Td\n/F1 12 Tf\n(Local demonstration data) Tj\nET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(new TextEncoder().encode(pdf).length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const xrefOffset = new TextEncoder().encode(pdf).length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
  return new Blob([pdf], { type: "application/pdf" });
}

export async function requestDemoApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = new URL(path, window.location.origin);
  const route = url.pathname.replace(/^\/api\/v1/, "");
  const method = (options.method ?? "GET").toUpperCase();
  const body = parseBody(options);

  if (route === "/system/seed" && method === "POST") {
    return { message: "Локальные демонстрационные данные готовы" } as T;
  }
  if (route === "/auth/me" && method === "GET") {
    return { role: currentRole(), onboarding_completed: true, profile: currentRole() === "candidate" ? currentCandidateProfile : currentEmployerProfile } as T;
  }
  if (route === "/auth/logout" && method === "POST") return { message: "Успешный выход из демо-режима" } as T;

  if (["/candidate/profile", "/candidates/profile"].includes(route) && method === "GET") return { ...currentCandidateProfile } as T;
  if (["/candidate/profile", "/candidates/profile"].includes(route) && method === "PUT") {
    currentCandidateProfile = { ...currentCandidateProfile, ...body } as typeof currentCandidateProfile;
    return { ...currentCandidateProfile } as T;
  }
  if (["/candidate/onboarding", "/candidates/onboarding"].includes(route) && method === "POST") {
    currentCandidateProfile = { ...currentCandidateProfile, ...body, onboarding_completed: true } as typeof currentCandidateProfile;
    return { ...currentCandidateProfile } as T;
  }
  if (route === "/candidate/link-fsp" && method === "POST") {
    currentCandidateProfile = { ...currentCandidateProfile, fsp_id: String(body.fsp_id ?? ""), fsp_verified: true };
    return { ...currentCandidateProfile } as T;
  }
  if (route === "/candidate/resume/upload" && method === "POST") {
    return {
      first_name: currentCandidateProfile.first_name,
      last_name: currentCandidateProfile.last_name,
      email: currentCandidateProfile.email,
      phone: currentCandidateProfile.phone,
      telegram: currentCandidateProfile.telegram,
      city: currentCandidateProfile.city,
      specialization: currentCandidateProfile.specialization,
      suggested_grade: currentCandidateProfile.declared_grade,
      extracted_skills: candidates[0].skills,
      text_preview: "Опыт разработки API на Python, FastAPI и PostgreSQL. Работа с контейнерами Docker, очередями и тестированием сервисов.",
    } as T;
  }
  if (route === "/candidate/profile/pdf" && method === "GET") return createDemoProfilePdf() as T;
  if (route === "/fsp/diplomas/upload" && method === "POST") {
    const file = options.body instanceof FormData ? options.body.get("file") : null;
    return { status: "pending_review", file_name: file instanceof File ? file.name : "demo-diploma.pdf" } as T;
  }

  if (["/employer/profile", "/employers/profile"].includes(route) && method === "GET") return { ...currentEmployerProfile } as T;
  if (["/employer/profile", "/employers/profile"].includes(route) && method === "PUT") {
    currentEmployerProfile = { ...currentEmployerProfile, ...body, onboarding_completed: true } as typeof currentEmployerProfile;
    return { ...currentEmployerProfile } as T;
  }
  if (["/employer/onboarding", "/employers/onboarding"].includes(route) && method === "POST") {
    currentEmployerProfile = { ...currentEmployerProfile, ...body, onboarding_completed: true } as typeof currentEmployerProfile;
    return { ...currentEmployerProfile } as T;
  }

  if (route === "/vacancies/my" && method === "GET") {
    return vacancies.filter((vacancy) => vacancy.employer_id === "demo-employer") as T;
  }
  if (route === "/vacancies/applications/my" && method === "GET") {
    return vacancyApplications
      .filter((application) => application.candidate_id === "demo-candidate-alex")
      .map(({ candidate: _candidate, candidate_id: _candidateId, ...application }) => application) as T;
  }
  if (route === "/vacancies/applications/conversations" && method === "GET") {
    const role = currentRole();
    return vacancyApplications
      .filter((application) => role === "candidate"
        ? application.candidate_id === "demo-candidate-alex"
        : application.vacancy_id.startsWith("demo-vacancy-"))
      .map((application) => {
        const messages = vacancyApplicationMessages[application.id] ?? [];
        return {
          id: application.id,
          vacancy_id: application.vacancy_id,
          vacancy_title: application.vacancy_title,
          company_name: application.company_name,
          candidate_name: `${application.candidate.first_name} ${application.candidate.last_name}`,
          status: application.status,
          last_message: messages[messages.length - 1]?.body ?? "Отклик отправлен",
        };
      }) as T;
  }
  if (route === "/vacancies" && method === "GET") {
    return vacancies.filter((vacancy) => vacancy.is_published) as T;
  }
  if (route === "/vacancies" && method === "POST") {
    const now = new Date().toISOString();
    const vacancy: DemoVacancy = {
      id: `demo-vacancy-${Date.now()}`,
      employer_id: "demo-employer",
      title: String(body.title ?? ""),
      specialization: String(body.specialization ?? ""),
      required_grade: String(body.required_grade ?? ""),
      required_skills: Array.isArray(body.required_skills) ? body.required_skills.map(String) : [],
      salary_min: Number(body.salary_min ?? 0),
      salary_max: Number(body.salary_max ?? 0),
      salary_tax_type: body.salary_tax_type === "net" ? "net" : "gross",
      currency: String(body.currency ?? "RUB"),
      work_format: String(body.work_format ?? "remote"),
      city: typeof body.city === "string" ? body.city : null,
      description: String(body.description ?? ""),
      is_published: false,
      created_at: now,
      updated_at: now,
      company: { id: "demo-company", company_name: currentEmployerProfile.company_name, industry: currentEmployerProfile.industry, website: currentEmployerProfile.website, city: currentEmployerProfile.city },
    };
    vacancies.unshift(vacancy);
    return vacancy as T;
  }
  const vacancyApplicationsForEmployer = route.match(/^\/vacancies\/([^/]+)\/applications$/);
  if (vacancyApplicationsForEmployer && method === "GET") {
    return vacancyApplications
      .filter((application) => application.vacancy_id === vacancyApplicationsForEmployer[1])
      .map(({ candidate_id: _candidateId, ...application }) => application) as T;
  }
  const vacancyApply = route.match(/^\/vacancies\/([^/]+)\/apply$/);
  if (vacancyApply && method === "POST") {
    const vacancy = vacancies.find((item) => item.id === vacancyApply[1] && item.is_published);
    if (!vacancy) throw new Error("Демо-вакансия не найдена или уже снята с публикации");
    const existing = vacancyApplications.find((item) => item.vacancy_id === vacancy.id && item.candidate_id === "demo-candidate-alex");
    if (existing) throw new Error("Вы уже откликнулись на эту вакансию");
    const now = new Date().toISOString();
    const application: DemoVacancyApplication = {
      id: `demo-application-${Date.now()}`,
      vacancy_id: vacancy.id,
      status: "pending",
      cover_letter: typeof body.cover_letter === "string" ? body.cover_letter : null,
      created_at: now,
      status_updated_at: null,
      candidate_id: "demo-candidate-alex",
      candidate: {
        first_name: currentCandidateProfile.first_name,
        last_name: currentCandidateProfile.last_name,
        email: currentCandidateProfile.email,
        phone: currentCandidateProfile.phone,
        telegram: currentCandidateProfile.telegram,
        city: currentCandidateProfile.city,
        specialization: currentCandidateProfile.specialization,
        verified_grade: currentCandidateProfile.verified_grade,
        skills: candidates[0].skills,
      },
      vacancy_title: vacancy.title,
      company_name: vacancy.company.company_name,
      salary_min: vacancy.salary_min,
      salary_max: vacancy.salary_max,
      salary_tax_type: vacancy.salary_tax_type,
    };
    vacancyApplications.unshift(application);
    vacancyApplicationMessages[application.id] = [{
      id: `demo-application-message-${Date.now()}`,
      invitation_id: application.id,
      sender_role: "candidate",
      body: `Здравствуйте! Откликнулся на вакансию «${vacancy.title}». Буду рад обсудить задачи команды и свой опыт.`,
      created_at: now,
      read: false,
    }];
    return (({ candidate: _candidate, candidate_id: _candidateId, ...result }) => result)(application) as T;
  }
  const vacancyApplicationMessagesRoute = route.match(/^\/vacancies\/applications\/([^/]+)\/messages$/);
  if (vacancyApplicationMessagesRoute) {
    const application = vacancyApplications.find((item) => item.id === vacancyApplicationMessagesRoute[1]);
    if (!application) throw new Error("Демо-отклик не найден");
    const role = currentRole();
    if (role === "candidate" && application.candidate_id !== "demo-candidate-alex") throw new Error("Демо-чат не найден");
    if (role === "employer" && !application.vacancy_id.startsWith("demo-vacancy-")) throw new Error("Демо-чат не найден");
    if (method === "GET") {
      const messages = vacancyApplicationMessages[application.id] ?? [];
      for (const message of messages) if (message.sender_role !== role) message.read = true;
      return {
        messages: messages.map(({ id, body, created_at, sender_role }) => ({
          id,
          body,
          created_at,
          is_mine: sender_role === role,
        })),
      } as T;
    }
    if (method === "POST") {
      const text = String(body.body ?? "").trim();
      if (!text || text.length > 4000) throw new Error("Сообщение должно содержать от 1 до 4000 символов");
      const message: DemoInvitationMessage = {
        id: `demo-application-message-${Date.now()}`,
        invitation_id: application.id,
        sender_role: role,
        body: text,
        created_at: new Date().toISOString(),
        read: false,
      };
      (vacancyApplicationMessages[application.id] ??= []).push(message);
      return { id: message.id, body: message.body, created_at: message.created_at, is_mine: true } as T;
    }
  }
  const vacancyApplicationStatus = route.match(/^\/vacancies\/applications\/([^/]+)\/status$/);
  if (vacancyApplicationStatus && method === "PATCH") {
    const application = vacancyApplications.find((item) => item.id === vacancyApplicationStatus[1]);
    if (!application) throw new Error("Демо-отклик не найден");
    if (body.status !== "pending" && body.status !== "reviewed" && body.status !== "accepted" && body.status !== "rejected") {
      throw new Error("Недопустимый статус демо-отклика");
    }
    application.status = body.status;
    application.status_updated_at = new Date().toISOString();
    return { status: "ok", application_id: application.id, new_status: application.status, status_updated_at: application.status_updated_at } as T;
  }
  const vacancyUpdate = route.match(/^\/vacancies\/([^/]+)$/);
  if (vacancyUpdate && method === "PATCH") {
    const vacancy = vacancies.find((item) => item.id === vacancyUpdate[1] && item.employer_id === "demo-employer");
    if (!vacancy) throw new Error("Демо-вакансия не найдена");
    if (typeof body.title === "string") vacancy.title = body.title;
    if (typeof body.specialization === "string") vacancy.specialization = body.specialization;
    if (typeof body.required_grade === "string") vacancy.required_grade = body.required_grade;
    if (Array.isArray(body.required_skills)) vacancy.required_skills = body.required_skills.map(String);
    if (typeof body.salary_min === "number") vacancy.salary_min = body.salary_min;
    if (typeof body.salary_max === "number") vacancy.salary_max = body.salary_max;
    if (body.salary_tax_type === "gross" || body.salary_tax_type === "net") vacancy.salary_tax_type = body.salary_tax_type;
    if (typeof body.work_format === "string") vacancy.work_format = body.work_format;
    if (typeof body.city === "string" || body.city === null) vacancy.city = body.city;
    if (typeof body.description === "string") vacancy.description = body.description;
    if (typeof body.is_published === "boolean") vacancy.is_published = body.is_published;
    vacancy.updated_at = new Date().toISOString();
    return vacancy as T;
  }

  if (route === "/needs" && method === "GET") return needs.filter((need) => need.employer_id === "demo-employer") as T;
  if (route === "/needs" && method === "POST") {
    const need = {
      ...body,
      id: `demo-need-${nextNeedId++}`,
      employer_id: "demo-employer",
      company_name: currentEmployerProfile.company_name,
      required_skills: Array.isArray(body.required_skills) ? body.required_skills : [],
      salary_min: Number(body.salary_min ?? 0),
      salary_max: Number(body.salary_max ?? 0),
      salary_tax_type: (body.salary_tax_type as "gross" | "net") || "gross",
      currency: "RUB",
      work_format: String(body.work_format ?? "remote"),
      city: String(body.city ?? ""),
      is_active: true,
      created_at: new Date().toISOString(),
    } as DemoNeed;
    needs.unshift(need);
    return need as T;
  }
  if (route.startsWith("/matching/for-need/") && method === "GET") {
    const needId = route.split("/").pop();
    const need = needs.find((item) => item.id === needId) ?? needs[0];
    const eligible = candidates.filter((item) =>
      item.specialization === need.specialization && item.verified_grade === need.required_grade,
    );
    return { need_id: need.id, need_title: need.title, total: eligible.length, candidates: eligible } as T;
  }
  if (route === "/matching/search" && method === "GET") {
    const specialization = url.searchParams.get("specialization");
    const grade = url.searchParams.get("grade");
    const stack = (url.searchParams.get("stack") || url.searchParams.get("skill"))?.trim().toLowerCase();
    const workFormat = url.searchParams.get("work_format");
    const city = url.searchParams.get("city")?.toLowerCase();
    const fspOnly = url.searchParams.get("fsp_only") === "true";
    return candidates.filter((item) =>
      (!specialization || item.specialization === specialization) &&
      (!grade || item.verified_grade === grade) &&
      (!stack || item.skills.some((candidateSkill) => candidateSkill.toLowerCase().includes(stack))) &&
      (!workFormat || item.work_format === workFormat) &&
      (!city || item.city.toLowerCase().includes(city)) &&
      (!fspOnly || item.fsp_verified) &&
      item.verified_grade !== null,
    ) as T;
  }

  if (route === "/testing/roadmap/current" && method === "GET") return null as T;
  if (route === "/testing/additional" && method === "GET") return [] as T;
  if (route === "/invitations/sent" && method === "GET") return invitations as T;
  if (route === "/invitations/my" && method === "GET") return invitationsForCandidate() as T;
  if (route === "/network/mentors" && method === "GET") {
    const skill = (url.searchParams.get("skill") ?? "").trim().toLowerCase();
    return demoMentors.filter((mentor) => !skill || mentor.skills.some((item) => item.toLowerCase().includes(skill))) as T;
  }
  if (route === "/network/conversations" && method === "GET") return networkConversations as T;
  if (route === "/network/mentorship-requests" && method === "POST") {
    const mentor = demoMentors.find((item) => item.user_id === body.mentor_user_id);
    if (!mentor) throw new Error("Демо-наставник не найден");
    if (networkConversations.some((item) => item.other_user_id === mentor.user_id && item.status !== "rejected")) {
      throw new Error("Запрос или диалог с этим наставником уже существует");
    }
    const id = `demo-network-${Date.now()}`;
    const message = String(body.message ?? "").trim();
    const conversation = {
      id,
      other_user_id: mentor.user_id,
      other_name: mentor.name,
      skill_focus: String(body.skill_focus ?? ""),
      status: "pending" as const,
      can_accept: false,
      last_message: message,
      updated_at: new Date().toISOString(),
    };
    networkConversations.unshift(conversation);
    networkMessages[id] = [{ id: `${id}-request`, body: message, created_at: conversation.updated_at, is_mine: true }];
    return conversation as T;
  }
  const networkConversationAction = route.match(/^\/network\/conversations\/([^/]+)\/(accept|decline)$/);
  if (networkConversationAction && method === "POST") {
    const conversation = networkConversations.find((item) => item.id === networkConversationAction[1]);
    if (!conversation || !conversation.can_accept || conversation.status !== "pending") throw new Error("Запрос не найден");
    conversation.status = networkConversationAction[2] === "accept" ? "accepted" : "rejected";
    conversation.can_accept = false;
    return undefined as T;
  }
  const networkMessagesRoute = route.match(/^\/network\/conversations\/([^/]+)\/messages$/);
  if (networkMessagesRoute && method === "GET") {
    const conversation = networkConversations.find((item) => item.id === networkMessagesRoute[1]);
    if (!conversation) throw new Error("Диалог не найден");
    return { messages: networkMessages[conversation.id] ?? [] } as T;
  }
  if (networkMessagesRoute && method === "POST") {
    const conversation = networkConversations.find((item) => item.id === networkMessagesRoute[1]);
    if (!conversation || conversation.status !== "accepted") throw new Error("Наставник должен принять запрос до начала переписки");
    const message = {
      id: `demo-network-message-${Date.now()}`,
      body: String(body.body ?? "").trim(),
      created_at: new Date().toISOString(),
      is_mine: true,
    };
    networkMessages[conversation.id].push(message);
    conversation.last_message = message.body;
    conversation.updated_at = message.created_at;
    return message as T;
  }
  if (route === "/invitations/messages/unread-count" && method === "GET") {
    const role = currentRole();
    const byInvitation: Record<string, number> = {};
    for (const invitation of invitations.filter((item) => item.status === "accepted")) {
      const count = invitationMessages.filter((message) =>
        message.invitation_id === invitation.id && message.sender_role !== role && !message.read,
      ).length;
      if (count) byInvitation[invitation.id] = count;
    }
    return { unread_count: Object.values(byInvitation).reduce((sum, count) => sum + count, 0), by_invitation: byInvitation } as T;
  }
  const invitationMessagesRoute = route.match(/^\/invitations\/([^/]+)\/messages$/);
  if (invitationMessagesRoute && method === "GET") {
    const invitation = invitations.find((item) => item.id === invitationMessagesRoute[1]);
    if (!invitation || invitation.status !== "accepted") throw new Error("Чат доступен только после принятия приглашения");
    const role = currentRole();
    const messages = invitationMessages.filter((item) => item.invitation_id === invitation.id);
    for (const message of messages) if (message.sender_role !== role) message.read = true;
    return {
      unread_count: 0,
      messages: messages.map((message) => ({
        id: message.id,
        body: message.body,
        created_at: message.created_at,
        is_mine: message.sender_role === role,
      })),
    } as T;
  }
  if (invitationMessagesRoute && method === "POST") {
    const invitation = invitations.find((item) => item.id === invitationMessagesRoute[1]);
    const text = typeof body.body === "string" ? body.body.trim() : "";
    if (!invitation || invitation.status !== "accepted") throw new Error("Чат доступен только после принятия приглашения");
    if (!text || text.length > 4000) throw new Error("Сообщение должно содержать от 1 до 4000 символов");
    const message: DemoInvitationMessage = {
      id: `demo-message-${Date.now()}`,
      invitation_id: invitation.id,
      sender_role: currentRole(),
      body: text,
      created_at: new Date().toISOString(),
      read: false,
    };
    invitationMessages.push(message);
    return {
      id: message.id,
      body: message.body,
      created_at: message.created_at,
      is_mine: true,
    } as T;
  }
  if (route === "/invitations" && method === "POST") {
    const candidate = candidates.find((item) => item.candidate_id === body.candidate_id) ?? candidates[0];
    const need = needs.find((item) => item.id === body.need_id);
    const invitation: DemoInvitation = {
      id: `demo-invitation-${nextInvitationId++}`,
      employer_id: "demo-employer",
      company_name: currentEmployerProfile.company_name,
      candidate_id: candidate.candidate_id,
      candidate_name: `${candidate.first_name} ${candidate.last_name}`,
      need_id: typeof body.need_id === "string" ? body.need_id : null,
      need_title: need?.title ?? null,
      offer_description: String(body.offer_description ?? ""),
      contact_method: String(body.contact_method ?? ""),
      salary_min: Number(body.salary_min ?? 0),
      salary_max: Number(body.salary_max ?? 0),
      currency: "RUB",
      status: "sent",
      candidate_reply: null,
      created_at: new Date().toISOString(),
      accepted_at: null,
      candidate_contacts: null,
    };
    invitations.unshift(invitation);
    return invitation as T;
  }
  const invitationAction = route.match(/^\/invitations\/([^/]+)\/(accept|reject)$/);
  if (invitationAction && method === "POST") {
    const invitation = invitations.find((item) => item.id === invitationAction[1]);
    if (!invitation) throw new Error("Демо-приглашение не найдено");
    const accepted = invitationAction[2] === "accept";
    invitation.status = accepted ? "accepted" : "rejected";
    invitation.candidate_reply = typeof body.reply === "string" ? body.reply : null;
    invitation.accepted_at = accepted ? new Date().toISOString() : null;
    invitation.candidate_contacts = accepted ? { email: currentCandidateProfile.email, phone: currentCandidateProfile.phone ?? "", telegram: currentCandidateProfile.telegram ?? "" } : null;
    return invitation as T;
  }

  if (route === "/testing/history" && method === "GET") return testHistory as T;
  if ((route === "/testing/start" || route === "/fsp/olympiad/start") && method === "POST") {
    activeTestId = `demo-test-${Date.now()}`;
    return {
      session_id: activeTestId,
      specialization: currentCandidateProfile.specialization,
      target_grade: currentCandidateProfile.declared_grade,
      status: "in_progress",
      questions: questions.map(({ correct: _correct, ...question }) => question),
      total_questions: questions.length,
    } as T;
  }
  const testSubmit = route.match(/^\/(testing|fsp\/olympiad)\/([^/]+)\/submit$/);
  if (testSubmit && method === "POST" && activeTestId === testSubmit[2]) {
    const isOlympiad = testSubmit[1] === "fsp/olympiad";
    const answers = Array.isArray(body.answers) ? body.answers as Array<{ question_id: string; selected_answers: string[] }> : [];
    const correct = answers.filter((answer) => questions.some((question) => question.id === answer.question_id && answer.selected_answers.includes(question.correct))).length;
    const percentage = Math.round(correct / questions.length * 100);
    const result = {
      session_id: activeTestId,
      specialization: currentCandidateProfile.specialization,
      target_grade: currentCandidateProfile.declared_grade,
      score: correct,
      max_score: questions.length,
      percentage,
      passed: percentage >= 70,
      verified_grade: !isOlympiad && percentage >= 70 ? currentCandidateProfile.declared_grade : null,
      skill_breakdown: questions.map((question, index) => ({ topic: question.topic, score: index < correct ? 1 : 0, max_score: 1, percentage: index < correct ? 100 : 0 })),
      feedback: isOlympiad
        ? `Демо-олимпиада завершена: подтверждены навыки по ${correct} темам.`
        : percentage >= 70 ? "Демо-тест пройден. Результат сохранён в этой сессии." : "В демо-тесте пока недостаточно правильных ответов.",
      suggested_grade: !isOlympiad && percentage >= 90 ? "senior" : null,
    };
    if (!isOlympiad) {
      currentCandidateProfile = { ...currentCandidateProfile, verified_grade: result.verified_grade ?? currentCandidateProfile.verified_grade };
      testHistory.unshift({ id: activeTestId, specialization: result.specialization, target_grade: result.target_grade, percentage, passed: result.passed, status: "completed", created_at: new Date().toISOString(), completed_at: new Date().toISOString() });
    }
    activeTestId = null;
    return result as T;
  }

  throw new Error(`Демо-режим не поддерживает ${method} ${route}`);
}
