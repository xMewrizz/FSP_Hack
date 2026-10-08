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
  match_explanation: { summary: string; matched_skills: string[]; missing_skills: string[] };
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
    return { need_id: need.id, need_title: need.title, total: candidates.length, candidates } as T;
  }
  if (route === "/matching/search" && method === "GET") {
    const specialization = url.searchParams.get("specialization");
    const grade = url.searchParams.get("grade");
    const workFormat = url.searchParams.get("work_format");
    const city = url.searchParams.get("city")?.toLowerCase();
    const fspOnly = url.searchParams.get("fsp_only") === "true";
    return candidates.filter((item) =>
      (!specialization || item.specialization === specialization) &&
      (!grade || item.verified_grade === grade || item.declared_grade === grade) &&
      (!workFormat || item.work_format === workFormat) &&
      (!city || item.city.toLowerCase().includes(city)) &&
      (!fspOnly || item.fsp_verified),
    ) as T;
  }

  if (route === "/invitations/sent" && method === "GET") return invitations as T;
  if (route === "/invitations/my" && method === "GET") return invitationsForCandidate() as T;
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
