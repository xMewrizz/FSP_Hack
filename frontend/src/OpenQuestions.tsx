import { useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";

type OpenQuestion = {
  code: string;
  title: string;
  specialization: string;
  grade: string;
  question_type: "free_text" | "code";
  skill: string;
  question_text: string;
  rubric_criteria: string[];
};

type Submission = {
  id: string;
  question_code: string;
  assessment_id: string | null;
  answer_text: string;
  score: number;
  feedback: string;
  criterion_scores: Record<string, number>;
  evaluator: string;
  needs_manual_review: boolean;
  evaluation_status: "queued" | "evaluating" | "completed" | "failed" | "manual_review";
  reviewed_at: string | null;
  manual_reviewer_notes: string | null;
  created_at: string;
};

type CodeRun = {
  status: string;
  score: number;
  tests_total: number;
  tests_passed: number;
  feedback: string;
};

const RUNNABLE_CODE_TASKS = new Set(["OPEN-BE-CODE-01", "OPEN-BE-CODE-02"]);

export default function OpenQuestions({ specialization, grade, assessmentId, assignedCodes, onSaved, onNotify }: {
  specialization: string | null | undefined;
  grade: string | null | undefined;
  assessmentId: string | null | undefined;
  assignedCodes: string[];
  onSaved: () => void;
  onNotify: (message: string, type?: "success" | "error") => void;
}) {
  const [questions, setQuestions] = useState<OpenQuestion[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [waitSeconds, setWaitSeconds] = useState(0);
  const [running, setRunning] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [runResult, setRunResult] = useState<CodeRun | null>(null);

  useEffect(() => {
    if (!sending && !retrying) return;
    const timer = window.setInterval(() => setWaitSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [sending, retrying]);

  useEffect(() => {
    if (!submissions.some((item) => item.assessment_id === assessmentId && ["queued", "evaluating"].includes(item.evaluation_status))) return;
    const timer = window.setInterval(() => {
      void apiGet<Submission[]>("/testing/open-submissions").then((updated) => {
        setSubmissions(updated);
        if (updated.some((item) => item.assessment_id === assessmentId &&
          ["completed", "failed", "manual_review"].includes(item.evaluation_status) &&
          submissions.some((previous) => previous.id === item.id && ["queued", "evaluating"].includes(previous.evaluation_status)))) {
          onSaved();
        }
      }).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [assessmentId, submissions]);

  useEffect(() => {
    if (!specialization || !grade) return;
    let cancelled = false;
    setLoading(true);
    setSelectedCode(null);
    setAnswer("");
    setRunResult(null);
    Promise.all([
      apiGet<OpenQuestion[]>(`/testing/open-questions?specialization=${encodeURIComponent(specialization)}&grade=${encodeURIComponent(grade)}`),
      apiGet<Submission[]>("/testing/open-submissions"),
    ]).then(([available, history]) => {
      if (cancelled) return;
      const assigned = available.filter((item) => assignedCodes.includes(item.code));
      setQuestions(assigned);
      setSubmissions(history);
      setSelectedCode(assigned.find((item) => !history.some((entry) =>
        entry.assessment_id === assessmentId && entry.question_code === item.code))?.code ?? null);
    }).catch((error: unknown) => {
      if (!cancelled) onNotify(error instanceof Error ? error.message : "Не удалось загрузить задания", "error");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [specialization, grade, assessmentId, assignedCodes.join("|")]);

  const selected = questions.find((item) => item.code === selectedCode);

  const refreshResult = async () => {
    try {
      setSubmissions(await apiGet<Submission[]>("/testing/open-submissions"));
      onSaved();
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось обновить результат", "error");
    }
  };

  const submit = async () => {
    if (!selected || !answer.trim() || sending) return;
    setWaitSeconds(0);
    setSending(true);
    try {
      const saved = await apiPost<Submission>(`/testing/open-questions/${encodeURIComponent(selected.code)}/queue`, { answer_text: answer.trim(), assessment_id: assessmentId });
      setSubmissions((current) => [saved, ...current]);
      setAnswer("");
      setRunResult(null);
      const next = questions.find((item) => item.code !== selected.code &&
        !submissions.some((existing) => existing.assessment_id === assessmentId && existing.question_code === item.code));
      setSelectedCode(next?.code ?? null);
      onSaved();
      onNotify("Ответ сохранён и проверяется. Можно перейти к следующему заданию.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Не удалось отправить ответ", "error");
    } finally {
      setSending(false);
    }
  };

  const testCode = async () => {
    if (!selected || !answer.trim() || running) return;
    setRunning(true);
    setRunResult(null);
    try {
      const result = await apiPost<CodeRun>(`/testing/open-questions/${encodeURIComponent(selected.code)}/test-run`, { code: answer });
      setRunResult(result);
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Пробный запуск недоступен", "error");
    } finally {
      setRunning(false);
    }
  };

  const retryEvaluation = async (submission: Submission) => {
    if (retrying) return;
    setRetrying(true);
    setWaitSeconds(0);
    try {
      const checked = await apiPost<Submission>(`/testing/open-submissions/${submission.id}/queue-retry`, {});
      setSubmissions((current) => current.map((item) => item.id === checked.id ? checked : item));
      onSaved();
      onNotify(checked.evaluation_status === "queued" ? "Ответ снова поставлен на проверку." : "Ответ проверен повторно.");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Повторная проверка недоступна", "error");
    } finally {
      setRetrying(false);
    }
  };

  if (!specialization || !grade) return <section className="feature-card"><div className="empty-state">Укажите специализацию и грейд в профиле, чтобы увидеть задания.</div></section>;
  if (!assessmentId || assignedCodes.length === 0) return <section className="feature-card"><div className="empty-state">Сначала откройте базовый набор тестов. Открытые задания закрепятся за ним.</div></section>;

  return <section className="feature-card open-questions">
    <div className="feature-head"><div><span>РАЗВЁРНУТЫЕ ЗАДАНИЯ</span><strong>{specialization} · {grade}</strong></div></div>
    <p className="feature-description feature-description--left">Для подтверждения грейда нужно выполнить все развёрнутые задания набора ({assignedCodes.length}). Каждый ответ даёт до 10 баллов. После отправки ответ сохраняется; следующие задания можно решать, пока идёт проверка.</p>
    {loading ? <div className="empty-state">Загружаем задания…</div> : questions.length === 0 ? <div className="empty-state">Для этого направления и грейда открытых заданий пока нет.</div> : questions.map((item, index) => {
      const saved = submissions.find((entry) => entry.assessment_id === assessmentId && entry.question_code === item.code);
      const isSelected = selectedCode === item.code;
      const isPending = saved && ["queued", "evaluating"].includes(saved.evaluation_status);
      const hasScore = saved && saved.evaluation_status === "completed" && !saved.needs_manual_review;
      return <div className="open-questions__task" key={item.code}>
        <span>ЗАДАНИЕ {index + 1} ИЗ {questions.length} · {item.question_type === "code" ? "Код" : "Развёрнутый ответ"} · {item.skill}</span>
        <h3>{item.title}</h3>
        <p>{item.question_text}</p>
        <details className="assessment-info"><summary>Что проверяется</summary><ul>{item.rubric_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul></details>
        {saved ? <div className="open-questions__result" role="status">
          <strong>Ваш ответ</strong><p>{saved.answer_text}</p>
          <strong>{hasScore ? `Баллы: ${Number((saved.score * 10).toFixed(1))} из 10` : isPending ? "Баллы: проверяется" : saved.evaluation_status === "failed" ? "Баллы: проверка не удалась" : "Баллы: ожидается проверка"}</strong>
          {hasScore && saved.feedback && <p>{saved.feedback}</p>}
          {saved.evaluation_status === "failed" && saved.feedback && <p>{saved.feedback}</p>}
          {saved.manual_reviewer_notes && <p>Комментарий проверяющего: {saved.manual_reviewer_notes}</p>}
          {hasScore && Object.keys(saved.criterion_scores).length > 0 && <details className="assessment-info"><summary>Результат по критериям</summary><ul>{Object.entries(saved.criterion_scores).map(([criterion, score]) => <li key={criterion}>{criterion}: {Math.round(score * 100)}%</li>)}</ul></details>}
          {(saved.evaluation_status === "failed" || saved.evaluation_status === "manual_review") && assessmentId && <button type="button" className="button button--outline" disabled={retrying} onClick={() => void retryEvaluation(saved)}>{retrying ? `Проверяем · ${waitSeconds} с` : "Повторить автоматическую проверку"}</button>}
          {!hasScore && <button type="button" className="button button--outline" onClick={() => void refreshResult()}>Обновить результат</button>}
        </div> : <>
          {!isSelected && <button type="button" className="button button--outline" onClick={() => { setSelectedCode(item.code); setAnswer(""); setRunResult(null); }}>Ответить на задание</button>}
          {isSelected && <>
            <label className="field field--flush"><span>{item.question_type === "code" ? "ВАШ КОД" : "ВАШ ОТВЕТ"}</span><textarea value={answer} maxLength={12000} rows={item.question_type === "code" ? 14 : 9} spellCheck={item.question_type !== "code"} onChange={(event) => { setAnswer(event.target.value); setRunResult(null); }} placeholder={item.question_type === "code" ? "Напишите решение здесь…" : "Опишите решение и объясните основные шаги…"} /></label>
            <div className="open-questions__actions">
              {RUNNABLE_CODE_TASKS.has(item.code) && <button type="button" className="button button--outline" disabled={!answer.trim() || running || sending} onClick={() => void testCode()}>{running ? "Проверяем код…" : "Пробный запуск"}</button>}
              <button type="button" className="button button--primary" disabled={!answer.trim() || sending || running} onClick={() => void submit()}>{sending ? "Отправляем…" : "Отправить ответ"}</button>
            </div>
            {sending && <div className="notice-box" role="status" aria-live="polite">Сохраняем ответ…</div>}
            {runResult && <div className="notice-box" role="status">Пробный запуск: {runResult.tests_passed} из {runResult.tests_total} проверок. {runResult.feedback}</div>}
          </>}
        </>}
      </div>;
    })}
  </section>;
}
