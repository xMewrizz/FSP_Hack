import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiRequest } from "./api";
import { ALL_GRADES, ALL_SPECIALIZATIONS } from "./catalog";
import TaskChatPanel from "./TaskChatPanel";

type TaskFile = { id: string; file_name: string; download_url: string };
type TaskSubmission = {
  id: string;
  task_id: string;
  candidate_id: string;
  candidate_name?: string | null;
  task_title?: string | null;
  answer_text: string;
  answer_links?: string[];
  attachments?: TaskFile[];
  status: "pending_review" | "graded";
  score: number | null;
  max_score: number;
  passed: boolean | null;
  feedback?: string | null;
  contact_consent?: boolean;
  reviewed_at?: string | null;
};
type EmployerTask = {
  id: string;
  title: string;
  description: string;
  company_name?: string | null;
  task_type: "auto_check" | "manual_review";
  max_score: number;
  is_active: boolean;
  specialization?: string | null;
  min_grade?: string | null;
  max_grade?: string | null;
  evaluation_criteria?: string[];
  resource_links?: string[];
  attachments?: TaskFile[];
  created_at: string;
  submissions_count?: number;
  my_submission?: TaskSubmission | null;
};

const demoSubmissions: TaskSubmission[] = [
  {
    id: "demo-submission-pending",
    task_id: "demo-employer-task-booking",
    candidate_id: "demo-candidate",
    candidate_name: "Алексей Морозов",
    task_title: "Как не допустить двойную запись",
    answer_text: "Перед подтверждением время ненадолго закрепляется за клиентом. Если он не завершил запись, время снова становится доступным. Если два клиента выбрали одно время одновременно, второму предлагаются ближайшие свободные варианты.",
    status: "pending_review",
    score: null,
    max_score: 10,
    passed: null,
    contact_consent: true,
  },
  {
    id: "demo-submission-graded",
    task_id: "demo-employer-task-access",
    candidate_id: "demo-candidate-2",
    candidate_name: "Мария Волкова",
    task_title: "Понятное восстановление доступа",
    answer_text: "Сначала уточнить адрес учётной записи, затем отправить одноразовую ссылку с ограниченным сроком действия. Показать нейтральное сообщение, чтобы не раскрывать, зарегистрирован ли такой адрес. Предусмотреть повторную отправку и понятную ошибку для просроченной ссылки.",
    status: "graded",
    score: 9,
    max_score: 10,
    passed: true,
    feedback: "Хорошо продуман сценарий и защита личных данных. Учтены повторная отправка и просроченная ссылка.",
    contact_consent: true,
    reviewed_at: new Date().toISOString(),
  },
  {
    id: "demo-submission-second-pending",
    task_id: "demo-employer-task-orders",
    candidate_id: "demo-candidate-3",
    candidate_name: "Илья Соколов",
    task_title: "История заказов без долгого ожидания",
    answer_text: "Показывать сначала последние заказы, а старые подгружать по запросу. Если данных много, разбивать их на небольшие порции и сохранять выбранные фильтры. Для часто просматриваемого списка использовать готовую копию данных с регулярным обновлением.",
    status: "pending_review",
    score: null,
    max_score: 10,
    passed: null,
    contact_consent: true,
  },
];

const demoTasks: EmployerTask[] = [
  {
    id: "demo-employer-task-booking",
    title: "Как не допустить двойную запись",
    description: "Два клиента одновременно выбирают одно и то же время для встречи. Опишите, как помочь обоим выбрать свободное время и не потерять запись.",
    task_type: "manual_review",
    max_score: 10,
    is_active: true,
    specialization: "Backend",
    min_grade: "junior",
    max_grade: "middle",
    evaluation_criteria: ["Понятный сценарий для обоих клиентов", "Что произойдёт, если подтверждение задержится", "Как убедиться, что запись не потерялась"],
    created_at: new Date().toISOString(),
    submissions_count: 1,
    company_name: "Команда сервиса «Запись»",
  },
  {
    id: "demo-employer-task-access",
    title: "Понятное восстановление доступа",
    description: "Клиент забыл пароль и хочет вернуться в свой профиль. Предложите безопасный и понятный порядок действий, включая повторную попытку и просроченную ссылку.",
    task_type: "manual_review",
    max_score: 10,
    is_active: true,
    specialization: "Backend",
    min_grade: "middle",
    max_grade: "senior",
    evaluation_criteria: ["Простой путь для клиента", "Защита личных данных", "Обработка повторной попытки и просроченной ссылки"],
    created_at: new Date().toISOString(),
    submissions_count: 1,
    company_name: "Команда сервиса «Запись»",
  },
  {
    id: "demo-employer-task-orders",
    title: "Быстрый поиск в истории заказов",
    description: "Клиенту нужно быстро найти заказ, сделанный несколько месяцев назад. Предложите удобный способ поиска и объясните, как показать много результатов, не заставляя ждать.",
    task_type: "manual_review",
    max_score: 10,
    is_active: true,
    specialization: "Backend",
    min_grade: "middle",
    max_grade: "senior",
    evaluation_criteria: ["Удобный поиск по прошлым заказам", "Быстрая загрузка результатов", "Понятное объяснение решения"],
    created_at: new Date().toISOString(),
    submissions_count: 1,
    company_name: "Команда сервиса «Запись»",
  },
];

const demoCandidateTasks = demoTasks.map((task) => ({
  ...task,
  my_submission: demoSubmissions.find((submission) => submission.task_id === task.id && submission.candidate_id === "demo-candidate")
    ?? (task.id === "demo-employer-task-access" ? demoSubmissions[1] : null),
}));

function gradeLabel(grade?: string | null) {
  return ALL_GRADES.find((item) => item.value === grade)?.label ?? grade ?? "Любой уровень";
}

function TaskIcon({ name, size = 18 }: { name: "clipboard" | "clock" | "check" | "briefcase" | "sparkle"; size?: number }) {
  const shapes = {
    clipboard: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4.5h6a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1ZM8 10h8M8 14h8M8 18h5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    check: <><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></>,
    briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></>,
    sparkle: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z" /><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></>,
  };

  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{shapes[name]}</svg>;
}

export default function TaskWorkspace({
  role,
  demoMode,
  onNotify,
}: {
  role: "candidate" | "employer";
  demoMode: boolean;
  onNotify: (message: string, type?: "success" | "error") => void;
}) {
  const notifyRef = useRef(onNotify);
  const [tasks, setTasks] = useState<EmployerTask[]>(demoMode ? (role === "candidate" ? demoCandidateTasks : demoTasks) : []);
  const [selectedTaskId, setSelectedTaskId] = useState(demoMode && role === "employer" ? demoTasks[0].id : "");
  const [openChatSubmissionId, setOpenChatSubmissionId] = useState<string | null>(null);
  const [submissions, setSubmissions] = useState<TaskSubmission[]>(demoMode && role === "employer" ? [demoSubmissions[0]] : []);
  const [mockSubmissions, setMockSubmissions] = useState(demoSubmissions);
  const [busy, setBusy] = useState(false);
  const [createFormOpen, setCreateFormOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<TaskFile[]>([]);
  const [links, setLinks] = useState("");
  const [answer, setAnswer] = useState("");
  const [score, setScore] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [inviteSalaryMin, setInviteSalaryMin] = useState("180000");
  const [inviteSalaryMax, setInviteSalaryMax] = useState("240000");
  const [inviteContact, setInviteContact] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
    specialization: "Backend",
    min_grade: "junior",
    max_grade: "senior",
    criteria: "",
    resource_links: "",
  });

  useEffect(() => {
    notifyRef.current = onNotify;
  }, [onNotify]);

  useEffect(() => {
    if (!demoMode) return;
    setTasks(role === "candidate" ? demoCandidateTasks : demoTasks);
    setSelectedTaskId(role === "employer" ? demoTasks[0].id : "");
    setSubmissions(role === "employer" ? [mockSubmissions[0]] : []);
  }, [demoMode, role]);

  useEffect(() => {
    if (demoMode) return;
    const path = role === "employer" ? "/employer/tasks" : "/candidate/tasks";
    apiGet<EmployerTask[]>(path)
      .then((items) => setTasks(items))
      .catch((error: unknown) => notifyRef.current(error instanceof Error ? error.message : "Не удалось загрузить задания", "error"));
  }, [demoMode, role]);

  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0];

  const loadSubmissions = async (task: EmployerTask) => {
    setSelectedTaskId(task.id);
    if (demoMode) {
      setSubmissions(mockSubmissions.filter((submission) => submission.task_id === task.id));
      return;
    }
    try {
      setSubmissions(await apiGet<TaskSubmission[]>(`/employer/tasks/${task.id}/submissions`));
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось загрузить ответы", "error");
    }
  };

  const uploadFiles = async (selected: FileList | null) => {
    if (!selected?.length) return;
    setUploading(true);
    try {
      const uploaded: TaskFile[] = [];
      for (const file of Array.from(selected)) {
        if (file.size > 5 * 1024 * 1024) throw new Error(`${file.name}: размер файла не должен превышать 5 МБ`);
        if (demoMode) {
          uploaded.push({ id: `demo-file-${crypto.randomUUID()}`, file_name: file.name, download_url: "" });
          continue;
        }
        const body = new FormData();
        body.append("file", file);
        uploaded.push(await apiRequest<TaskFile>("/tasks/attachments", { method: "POST", body }));
      }
      setFiles((current) => [...current, ...uploaded]);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось прикрепить файл", "error");
    } finally {
      setUploading(false);
    }
  };

  const createTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.title.trim() || !form.description.trim() || !form.criteria.trim()) {
      onNotify("Заполните название, условие и критерии оценивания", "error");
      return;
    }
    setBusy(true);
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      task_type: "manual_review",
      max_score: 10,
      specialization: form.specialization,
      min_grade: form.min_grade,
      max_grade: form.max_grade,
      evaluation_criteria: form.criteria.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      resource_links: form.resource_links.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      attachment_ids: files.map((file) => file.id),
    };
    try {
      const created: EmployerTask = demoMode
        ? { ...payload, id: `demo-task-${Date.now()}`, task_type: "manual_review", is_active: true, created_at: new Date().toISOString(), attachments: files }
        : await apiPost<EmployerTask>("/employer/tasks", payload);
      setTasks((current) => [created, ...current]);
      setSelectedTaskId(created.id);
      setSubmissions([]);
      setFiles([]);
      setForm((current) => ({ ...current, title: "", description: "", criteria: "", resource_links: "" }));
      setCreateFormOpen(false);
      onNotify("Задание опубликовано");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось создать задание", "error");
    } finally {
      setBusy(false);
    }
  };

  const reviewSubmission = async (submission: TaskSubmission) => {
    const numericScore = Number(score[submission.id]);
    if (!Number.isFinite(numericScore) || numericScore < 0 || numericScore > submission.max_score) {
      onNotify(`Укажите балл от 0 до ${submission.max_score}`, "error");
      return;
    }
    setBusy(true);
    try {
      const result = demoMode
        ? { ...submission, status: "graded" as const, score: numericScore, passed: numericScore / submission.max_score > 0.75, feedback: feedback[submission.id] || "" }
        : await apiPost<TaskSubmission>(`/employer/tasks/submissions/${submission.id}/review`, {
            score: numericScore,
            passed: numericScore / submission.max_score > 0.75,
            feedback: feedback[submission.id] || "",
          });
      setSubmissions((current) => current.map((item) => item.id === result.id ? result : item));
      if (demoMode) {
        setMockSubmissions((current) => current.map((item) => item.id === result.id ? result : item));
      }
      onNotify("Оценка и комментарий сохранены");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось оценить задание", "error");
    } finally {
      setBusy(false);
    }
  };

  const inviteCandidate = async (submission: TaskSubmission) => {
    if (submission.status !== "graded" || !submission.contact_consent) return;
    const salaryMin = Number(inviteSalaryMin);
    const salaryMax = Number(inviteSalaryMax);
    if (!inviteContact.trim() || !Number.isFinite(salaryMin) || !Number.isFinite(salaryMax) || salaryMin <= 0 || salaryMax < salaryMin) {
      onNotify("Укажите способ связи и корректный диапазон зарплаты", "error");
      return;
    }
    try {
      if (!demoMode) {
        await apiPost("/invitations", {
          candidate_id: submission.candidate_id,
          offer_description: `По итогам задания «${submission.task_title ?? selectedTask?.title ?? "задание"}»: ${feedback[submission.id] || submission.feedback || "Предлагаем обсудить сотрудничество."}`,
          contact_method: inviteContact.trim(),
          salary_min: salaryMin,
          salary_max: salaryMax,
          salary_tax_type: "gross",
          currency: "RUB",
        });
      }
      onNotify(`Приглашение для ${submission.candidate_name ?? "кандидата"} отправлено`);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось пригласить кандидата", "error");
    }
  };

  const submitAnswer = async (task: EmployerTask) => {
    if (!answer.trim()) {
      onNotify("Добавьте решение перед отправкой", "error");
      return;
    }
    setBusy(true);
    try {
      if (demoMode) {
        const result: TaskSubmission = {
          id: `demo-answer-${Date.now()}`,
          task_id: task.id,
          candidate_id: "demo-candidate",
          task_title: task.title,
          answer_text: answer.trim(),
          answer_links: links.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
          attachments: files,
          status: "pending_review",
          score: null,
          max_score: task.max_score,
          passed: null,
          contact_consent: true,
        };
        setTasks((current) => current.map((item) => item.id === task.id ? { ...item, my_submission: result } : item));
      } else {
        const result = await apiPost<TaskSubmission>(`/candidate/tasks/${task.id}/submit`, {
          answer_text: answer.trim(),
          answer_links: links.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
          attachment_ids: files.map((file) => file.id),
        });
        setTasks((current) => current.map((item) => item.id === task.id ? { ...item, my_submission: result } : item));
      }
      setAnswer("");
      setLinks("");
      setFiles([]);
      onNotify("Решение отправлено работодателю");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось отправить решение", "error");
    } finally {
      setBusy(false);
    }
  };

  const downloadFile = async (file: TaskFile) => {
    if (demoMode) {
      onNotify("В демо вложения представлены как макет");
      return;
    }
    try {
      const blob = await apiGet<Blob>(file.download_url);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.file_name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось скачать вложение", "error");
    }
  };

  const fileControls = <div className="task-workspace__files">
    <label className="task-workspace__upload">
      <span>{uploading ? "Загружаем файлы…" : "Прикрепить файл"}</span>
      <input type="file" multiple disabled={uploading} onChange={(event) => void uploadFiles(event.target.files)} />
    </label>
    {files.map((file) => <button type="button" key={file.id} className="task-workspace__file" onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))}>{file.file_name} ×</button>)}
  </div>;

  return <div className="page-content task-workspace">
    <section className="task-workspace__hero">
      <div className="task-workspace__hero-copy">
        <span className="task-workspace__hero-icon"><TaskIcon name={role === "employer" ? "briefcase" : "sparkle"} size={22} /></span>
        <div>
        <span>{role === "employer" ? "ЗАДАНИЯ КАНДИДАТАМ" : "ПРАКТИКА И ОТКЛИКИ"}</span>
        <h2>{role === "employer" ? "Задания и ответы" : "Задания по вашему направлению"}</h2>
        <p>{role === "employer" ? "Публикуйте практические задания, проверяйте решения и приглашайте кандидатов после оценки." : "Выберите задание по своему уровню, отправьте решение и получите обратную связь от работодателя."}</p>
        </div>
      </div>
      {role === "employer" && <button type="button" className="button" onClick={() => setCreateFormOpen((open) => !open)}>
        <TaskIcon name={createFormOpen ? "check" : "clipboard"} size={16} />
        {createFormOpen ? "Скрыть форму" : "Новое задание"}
      </button>}
    </section>

    {role === "employer" ? <>
      {createFormOpen && <section className="feature-card task-workspace__create-panel">
        <div className="feature-head"><div><span>НОВОЕ ЗАДАНИЕ</span><strong><TaskIcon name="sparkle" size={17} />Сформулируйте задачу</strong></div></div>
        <form className="task-workspace__form" onSubmit={(event) => void createTask(event)}>
          <label className="field"><span>НАЗВАНИЕ</span><input maxLength={200} value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} /></label>
          <div className="field-row field-row--flush">
            <label className="field"><span>НАПРАВЛЕНИЕ</span><select value={form.specialization} onChange={(event) => setForm((current) => ({ ...current, specialization: event.target.value }))}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label className="field"><span>УРОВЕНЬ ОТ</span><select value={form.min_grade} onChange={(event) => setForm((current) => ({ ...current, min_grade: event.target.value }))}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="field"><span>УРОВЕНЬ ДО</span><select value={form.max_grade} onChange={(event) => setForm((current) => ({ ...current, max_grade: event.target.value }))}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          </div>
          <label className="field"><span>УСЛОВИЕ ЗАДАНИЯ</span><textarea required value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
          <label className="field"><span>КРИТЕРИИ ОЦЕНИВАНИЯ · ПО ОДНОМУ НА СТРОКУ</span><textarea required placeholder={"Корректность решения\nРазбор граничных случаев\nКачество объяснения"} value={form.criteria} onChange={(event) => setForm((current) => ({ ...current, criteria: event.target.value }))} /></label>
          <label className="field"><span>ПОЛЕЗНЫЕ ССЫЛКИ · ПО ОДНОЙ НА СТРОКУ</span><textarea placeholder="https://example.com/material" value={form.resource_links} onChange={(event) => setForm((current) => ({ ...current, resource_links: event.target.value }))} /></label>
          {fileControls}
          <button type="submit" className="button" disabled={busy || uploading}>{busy ? "Публикуем…" : "Опубликовать задание"}</button>
        </form>
      </section>}
      <div className="task-workspace__layout">
        <section className="feature-card task-workspace__task-list">
          <div className="feature-head"><div><span>РАБОЧАЯ ПАНЕЛЬ</span><strong><TaskIcon name="clipboard" size={17} />Ваши задания <small>{tasks.length}</small></strong></div></div>
          {tasks.map((task) => {
            const pendingCount = task.id.startsWith("demo-")
              ? mockSubmissions.filter((submission) => submission.task_id === task.id && submission.status === "pending_review").length
              : null;
            const submissionsLabel = pendingCount ? `${pendingCount} ответ(а) ожидают проверки` : `${task.submissions_count ?? 0} ответов`;
            return <article className={`task-workspace__task${selectedTaskId === task.id ? " task-workspace__task--selected" : ""}`} key={task.id}>
              <div className="task-workspace__task-icon"><TaskIcon name={pendingCount ? "clock" : "clipboard"} size={19} /></div>
              <div className="task-workspace__task-copy"><span>{task.specialization ?? "Все направления"} · {gradeLabel(task.min_grade)} — {gradeLabel(task.max_grade)}</span><strong>{task.title}</strong><small><TaskIcon name={pendingCount ? "clock" : "check"} size={13} />{submissionsLabel}</small></div>
              <button type="button" className="button button--outline" onClick={() => void loadSubmissions(task)}>{pendingCount ? <><TaskIcon name="check" size={15} />Проверить</> : "Открыть"}</button>
            </article>;
          })}
          {!tasks.length && <div className="empty-state">Пока нет заданий. Создайте первое — оно появится здесь.</div>}
        </section>
        <section className="feature-card task-workspace__review-panel">
          {selectedTask ? <>
            <div className="feature-head"><div><span>{selectedTask.specialization ?? "Все направления"} · {gradeLabel(selectedTask.min_grade)} — {gradeLabel(selectedTask.max_grade)}</span><strong><TaskIcon name="clipboard" size={17} />{selectedTask.title}</strong></div><span className="task-workspace__score-badge">до {selectedTask.max_score} баллов</span></div>
            <div className="task-workspace__reviews">
              <section className="task-workspace__brief">
                <span><TaskIcon name="sparkle" size={14} />УСЛОВИЕ ЗАДАНИЯ</span>
                <p>{selectedTask.description}</p>
                {selectedTask.evaluation_criteria?.length ? <>
                  <strong><TaskIcon name="check" size={15} />Критерии оценки</strong>
                  <ul>{selectedTask.evaluation_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
                </> : null}
              </section>
              <h3><TaskIcon name="briefcase" size={17} />Ответы <span>{submissions.length}</span></h3>
              {submissions.map((submission) => <article className="task-workspace__submission" key={submission.id}>
                <strong><TaskIcon name={submission.status === "graded" ? "check" : "clock"} size={16} />{submission.candidate_name ?? "Кандидат"} · {submission.status === "graded" ? `Оценка ${submission.score}/${submission.max_score}` : "Ожидает проверки"}</strong>
                <p>{submission.answer_text}</p>
                {submission.answer_links?.map((link) => <a key={link} href={link} target="_blank" rel="noreferrer">{link}</a>)}
                {submission.attachments?.map((file) => <button type="button" key={file.id} onClick={() => void downloadFile(file)}>{file.file_name}</button>)}
                {submission.status === "pending_review" ? <>
                  <label className="field"><span>БАЛЛ · ИЗ {submission.max_score}</span><input type="number" min="0" max={submission.max_score} step="0.1" value={score[submission.id] ?? ""} onChange={(event) => setScore((current) => ({ ...current, [submission.id]: event.target.value }))} /></label>
                  <label className="field"><span>КОММЕНТАРИЙ КАНДИДАТУ</span><textarea value={feedback[submission.id] ?? ""} onChange={(event) => setFeedback((current) => ({ ...current, [submission.id]: event.target.value }))} /></label>
                  <button type="button" className="button" disabled={busy} onClick={() => void reviewSubmission(submission)}>Сохранить оценку</button>
                </> : <>
                  <p>{submission.feedback || "Работодатель оценил решение."}</p>
                  {submission.contact_consent && <div className="task-workspace__invite">
                    <h4>Пригласить кандидата к сотрудничеству</h4>
                    <label className="field"><span>СПОСОБ СВЯЗИ</span><input value={inviteContact} onChange={(event) => setInviteContact(event.target.value)} placeholder="Почта, телефон или ссылка на чат" /></label>
                    <div className="field-row field-row--flush">
                      <label className="field"><span>ЗАРПЛАТА ОТ, ₽</span><input type="number" min="1" value={inviteSalaryMin} onChange={(event) => setInviteSalaryMin(event.target.value)} /></label>
                      <label className="field"><span>ЗАРПЛАТА ДО, ₽</span><input type="number" min="1" value={inviteSalaryMax} onChange={(event) => setInviteSalaryMax(event.target.value)} /></label>
                    </div>
                    <button type="button" className="button" onClick={() => void inviteCandidate(submission)}>Отправить приглашение</button>
                  </div>}
                </>}
                {!demoMode && <><button type="button" className="button button--outline" onClick={() => setOpenChatSubmissionId((current) => current === submission.id ? null : submission.id)}>{openChatSubmissionId === submission.id ? "Скрыть переписку" : "Написать в личку"}</button>{openChatSubmissionId === submission.id && <TaskChatPanel submissionId={submission.id} taskTitle={selectedTask.title} otherName={submission.candidate_name ?? "Кандидат"} />}</>}
              </article>)}
              {!submissions.length && <p className="empty-state">Ответов на это задание пока нет.</p>}
            </div>
          </> : <div className="empty-state">Создайте или выберите задание, чтобы посмотреть ответы.</div>}
        </section>
      </div>
    </> : <div className="task-workspace__candidate">
      {tasks.map((task) => <article className="feature-card task-workspace__candidate-card" key={task.id}>
        <div className="feature-head"><div><span>{task.company_name ?? "Работодатель"} · {task.specialization ?? "Все направления"} · {gradeLabel(task.min_grade)} — {gradeLabel(task.max_grade)}</span><strong><TaskIcon name="clipboard" size={17} />{task.title}</strong></div></div>
        <p>{task.description}</p>
        {task.evaluation_criteria?.length ? <div className="task-workspace__criteria"><strong>На что обратят внимание</strong><div className="topic-summary">{task.evaluation_criteria.map((criterion) => <div key={criterion}><span>{criterion}</span></div>)}</div></div> : null}
        {task.resource_links?.map((link) => <a key={link} href={link} target="_blank" rel="noreferrer">{link}</a>)}
        {task.attachments?.map((file) => <button type="button" key={file.id} onClick={() => void downloadFile(file)}>{file.file_name}</button>)}
        {task.title.startsWith("Демо ·") ? <div className="task-workspace__candidate-status task-workspace__candidate-status--pending"><TaskIcon name="briefcase" size={17} /><span>Демонстрационное задание: условие и критерии доступны для просмотра, отправка решения закрыта.</span></div> : task.my_submission ? <div className={`task-workspace__candidate-status task-workspace__candidate-status--${task.my_submission.status === "pending_review" ? "pending" : task.my_submission.passed ? "passed" : "needs-work"}`}>
          <TaskIcon name={task.my_submission.status === "pending_review" ? "clock" : task.my_submission.passed ? "check" : "sparkle"} size={17} />
          <span>{task.my_submission.status === "pending_review"
            ? "Решение отправлено — работодатель скоро его проверит."
            : `${task.my_submission.passed ? "Отличный результат" : "Есть куда расти"} · ${task.my_submission.score}/${task.my_submission.max_score} баллов. ${task.my_submission.feedback ?? ""}`}</span>
        </div> : <>
          <label className="field"><span>ВАШЕ РЕШЕНИЕ</span><textarea value={answer} onChange={(event) => setAnswer(event.target.value)} /></label>
          <label className="field"><span>ССЫЛКИ НА МАТЕРИАЛЫ ИЛИ ПРИМЕР РЕШЕНИЯ</span><textarea placeholder="https://example.com/your-work" value={links} onChange={(event) => setLinks(event.target.value)} /></label>
          {fileControls}
          <div className="task-workspace__candidate-status task-workspace__candidate-status--pending"><TaskIcon name="briefcase" size={17} /><span>После отправки решения вы сможете переписываться с работодателем внутри сервиса. Контакты откроются ему только после принятия приглашения.</span></div>
          <button type="button" className="button" disabled={busy || uploading} onClick={() => void submitAnswer(task)}><TaskIcon name="check" size={16} />{busy ? "Отправляем…" : "Отправить решение"}</button>
        </>}
        {task.my_submission && !demoMode && <><button type="button" className="button button--outline" onClick={() => setOpenChatSubmissionId((current) => current === task.my_submission?.id ? null : task.my_submission?.id ?? null)}>{openChatSubmissionId === task.my_submission.id ? "Скрыть переписку" : "Написать работодателю"}</button>{openChatSubmissionId === task.my_submission.id && <TaskChatPanel submissionId={task.my_submission.id} taskTitle={task.title} otherName={task.company_name ?? "Работодатель"} />}</>}
      </article>)}
      {!tasks.length && <div className="empty-state">Для вашего направления пока нет активных заданий.</div>}
    </div>}
  </div>;
}
