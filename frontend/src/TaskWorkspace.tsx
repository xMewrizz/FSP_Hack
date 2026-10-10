import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiRequest } from "./api";
import { ALL_GRADES, ALL_SPECIALIZATIONS } from "./catalog";

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

const demoSubmission: TaskSubmission = {
  id: "demo-submission-pending",
  task_id: "demo-employer-task",
  candidate_id: "demo-candidate",
  candidate_name: "Алексей Морозов",
  answer_text: "Добавил cursor pagination, проверку входных данных и тесты на последнюю страницу.",
  answer_links: ["https://github.com/example/pagination"],
  status: "pending_review",
  score: null,
  max_score: 10,
  passed: null,
  contact_consent: true,
};

const demoTask: EmployerTask = {
  id: "demo-employer-task",
  title: "Пагинация списка кандидатов",
  description: "Спроектируйте API-эндпоинт с cursor pagination для быстро меняющегося списка. Опишите контракт, граничные случаи и тесты.",
  task_type: "manual_review",
  max_score: 10,
  is_active: true,
  specialization: "Backend",
  min_grade: "junior",
  max_grade: "senior",
  evaluation_criteria: ["Корректный курсор и устойчивый порядок", "Обработка пустой и последней страницы", "Тесты и ясность API-контракта"],
  resource_links: ["https://github.com/example/api"],
  created_at: new Date().toISOString(),
  submissions_count: 1,
};

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
  const [tasks, setTasks] = useState<EmployerTask[]>(demoMode ? [demoTask] : []);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [submissions, setSubmissions] = useState<TaskSubmission[]>(demoMode && role === "employer" ? [demoSubmission] : []);
  const [busy, setBusy] = useState(false);
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
      setSubmissions(task.id === demoTask.id ? [demoSubmission] : []);
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
      <span>{uploading ? "Загружаем файлы…" : "Прикрепить файлы · до 5 МБ"}</span>
      <input type="file" multiple disabled={uploading} onChange={(event) => void uploadFiles(event.target.files)} />
    </label>
    {files.map((file) => <button type="button" key={file.id} className="task-workspace__file" onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))}>{file.file_name} ×</button>)}
  </div>;

  return <div className="page-content task-workspace">
    <section className="task-workspace__hero">
      <span>{role === "employer" ? "ЗАДАНИЯ КАНДИДАТАМ" : "ПРАКТИКА И ОТКЛИКИ"}</span>
      <h2>{role === "employer" ? "Задания и ответы" : "Задания по вашему направлению"}</h2>
      <p>{role === "employer" ? "Опубликуйте практическую задачу, проверьте решение и откройте приглашение только после выставления оценки." : "Условие содержит критерии проверки. При отправке решения подтвердите, что HR автора задания может связаться с вами."}</p>
    </section>

    {role === "employer" ? <div className="task-workspace__layout">
      <section className="feature-card">
        <div className="feature-head"><div><span>НОВОЕ ЗАДАНИЕ</span><strong>Сформулируйте задачу</strong></div></div>
        <form className="task-workspace__form" onSubmit={(event) => void createTask(event)}>
          <label className="field"><span>НАЗВАНИЕ</span><input maxLength={200} value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} /></label>
          <div className="field-row field-row--flush">
            <label className="field"><span>СПЕЦИАЛИЗАЦИЯ</span><select value={form.specialization} onChange={(event) => setForm((current) => ({ ...current, specialization: event.target.value }))}>{ALL_SPECIALIZATIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label className="field"><span>ОТ ГРЕЙДА</span><select value={form.min_grade} onChange={(event) => setForm((current) => ({ ...current, min_grade: event.target.value }))}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="field"><span>ДО ГРЕЙДА</span><select value={form.max_grade} onChange={(event) => setForm((current) => ({ ...current, max_grade: event.target.value }))}>{ALL_GRADES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          </div>
          <label className="field"><span>УСЛОВИЕ ЗАДАНИЯ</span><textarea required value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
          <label className="field"><span>КРИТЕРИИ ОЦЕНИВАНИЯ · ПО ОДНОМУ НА СТРОКУ</span><textarea required placeholder={"Корректность решения\nРазбор граничных случаев\nКачество объяснения"} value={form.criteria} onChange={(event) => setForm((current) => ({ ...current, criteria: event.target.value }))} /></label>
          <label className="field"><span>ССЫЛКИ НА GITHUB И МАТЕРИАЛЫ · ПО ОДНОЙ НА СТРОКУ</span><textarea placeholder="https://github.com/org/repository" value={form.resource_links} onChange={(event) => setForm((current) => ({ ...current, resource_links: event.target.value }))} /></label>
          {fileControls}
          <button type="submit" className="button" disabled={busy || uploading}>{busy ? "Публикуем…" : "Опубликовать задание"}</button>
        </form>
      </section>
      <section className="feature-card">
        <div className="feature-head"><div><span>ОПУБЛИКОВАНО</span><strong>Ваши задания</strong></div></div>
        {tasks.map((task) => <article className="task-workspace__task" key={task.id}>
          <div><span>{task.specialization ?? "Все направления"} · {task.min_grade ?? "Любой"} — {task.max_grade ?? "грейд"}</span><strong>{task.title}</strong><small>{task.submissions_count ?? 0} решений</small></div>
          <button type="button" className="button button--outline" onClick={() => void loadSubmissions(task)}>Проверить ответы</button>
        </article>)}
        {!tasks.length && <div className="empty-state">Пока нет заданий. Создайте первое.</div>}
        {selectedTask && <div className="task-workspace__reviews"><h3>Ответы · {selectedTask.title}</h3>
          {submissions.map((submission) => <article className="task-workspace__submission" key={submission.id}>
            <strong>{submission.candidate_name ?? "Кандидат"} · {submission.status === "graded" ? `Оценка ${submission.score}/${submission.max_score}` : "Ожидает проверки"}</strong>
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
                <h4>Кандидат разрешил передать контакты HR</h4>
                <label className="field"><span>СПОСОБ СВЯЗИ</span><input value={inviteContact} onChange={(event) => setInviteContact(event.target.value)} placeholder="Почта, телефон или ссылка на чат" /></label>
                <div className="field-row field-row--flush">
                  <label className="field"><span>ЗАРПЛАТА ОТ, ₽</span><input type="number" min="1" value={inviteSalaryMin} onChange={(event) => setInviteSalaryMin(event.target.value)} /></label>
                  <label className="field"><span>ЗАРПЛАТА ДО, ₽</span><input type="number" min="1" value={inviteSalaryMax} onChange={(event) => setInviteSalaryMax(event.target.value)} /></label>
                </div>
                <button type="button" className="button" onClick={() => void inviteCandidate(submission)}>Отправить приглашение</button>
              </div>}
            </>}
          </article>)}
          {!submissions.length && <p className="empty-state">Ответов на это задание пока нет.</p>}
        </div>}
      </section>
    </div> : <div className="task-workspace__candidate">
      {tasks.map((task) => <article className="feature-card task-workspace__candidate-card" key={task.id}>
        <div className="feature-head"><div><span>{task.company_name ?? "Работодатель"} · {task.specialization ?? "Все направления"} · {task.min_grade ?? "Любой"} — {task.max_grade ?? "грейд"}</span><strong>{task.title}</strong></div></div>
        <p>{task.description}</p>
        {task.evaluation_criteria?.length ? <div className="topic-summary">{task.evaluation_criteria.map((criterion) => <div key={criterion}><span>{criterion}</span></div>)}</div> : null}
        {task.resource_links?.map((link) => <a key={link} href={link} target="_blank" rel="noreferrer">{link}</a>)}
        {task.attachments?.map((file) => <button type="button" key={file.id} onClick={() => void downloadFile(file)}>{file.file_name}</button>)}
        {task.my_submission ? <div className="notice-box">{task.my_submission.status === "pending_review" ? "Решение ожидает проверки работодателем." : `Оценка: ${task.my_submission.score}/${task.my_submission.max_score}. ${task.my_submission.feedback ?? ""}`}</div> : <>
          <label className="field"><span>ВАШЕ РЕШЕНИЕ</span><textarea value={answer} onChange={(event) => setAnswer(event.target.value)} /></label>
          <label className="field"><span>ССЫЛКИ НА GITHUB И РЕШЕНИЕ · ПО ОДНОЙ НА СТРОКУ</span><textarea placeholder="https://github.com/user/solution" value={links} onChange={(event) => setLinks(event.target.value)} /></label>
          {fileControls}
          <div className="notice-box">Отправляя решение, вы автоматически соглашаетесь передать ваши контактные данные HR автора задания для связи после проверки.</div>
          <button type="button" className="button" disabled={busy || uploading} onClick={() => void submitAnswer(task)}>{busy ? "Отправляем…" : "Отправить решение"}</button>
        </>}
      </article>)}
      {!tasks.length && <div className="empty-state">Для вашего направления пока нет активных заданий.</div>}
    </div>}
  </div>;
}
