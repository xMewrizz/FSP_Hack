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
  score: number;
  feedback: string;
  criterion_scores: Record<string, number>;
  evaluator: string;
  needs_manual_review: boolean;
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
      setSelectedCode(assigned[0]?.code ?? null);
    }).catch((error: unknown) => {
      if (!cancelled) onNotify(error instanceof Error ? error.message : "Не удалось загрузить задания", "error");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [specialization, grade, assessmentId, assignedCodes.join("|")]);

  const selected = questions.find((item) => item.code === selectedCode);
  const latest = submissions.find((item) => item.question_code === selectedCode && item.assessment_id === assessmentId);

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
      const saved = await apiPost<Submission>(`/testing/open-questions/${encodeURIComponent(selected.code)}/submit`, { answer_text: answer.trim(), assessment_id: assessmentId });
      setSubmissions((current) => [saved, ...current]);
      onSaved();
      onNotify("Ответ сохранён. Оценка показана ниже.");
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
      const checked = await apiPost<Submission>(`/testing/open-submissions/${submission.id}/retry-evaluation`, {});
      setSubmissions((current) => current.map((item) => item.id === checked.id ? checked : item));
      onSaved();
      onNotify("Ответ проверен повторно.");
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
    <p className="feature-description feature-description--left">Для подтверждения грейда нужно выполнить все развёрнутые задания набора ({assignedCodes.length}). Каждый ответ даёт до 10 баллов. Если проверка временно недоступна, ответ останется в форме для повторной отправки.</p>
    {loading ? <div className="empty-state">Загружаем задания…</div> : questions.length === 0 ? <div className="empty-state">Для этого направления и грейда открытых заданий пока нет.</div> : <>
      <label className="field field--flush"><span>ЗАДАНИЕ</span><select value={selectedCode ?? ""} onChange={(event) => { setSelectedCode(event.target.value); setAnswer(""); setRunResult(null); }}>
        {questions.map((item) => <option key={item.code} value={item.code}>{item.skill} · {item.title}</option>)}
      </select></label>
      {selected && <>
        <div className="open-questions__task"><span>{selected.question_type === "code" ? "Задание с кодом" : "Развёрнутый ответ"} · {selected.skill}</span><h3>{selected.title}</h3><p>{selected.question_text}</p></div>
        <details className="assessment-info"><summary>Что проверяется</summary><ul>{selected.rubric_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul></details>
        {!latest && <><label className="field field--flush"><span>{selected.question_type === "code" ? "ВАШ КОД" : "ВАШ ОТВЕТ"}</span><textarea value={answer} maxLength={12000} rows={selected.question_type === "code" ? 14 : 9} spellCheck={selected.question_type !== "code"} onChange={(event) => { setAnswer(event.target.value); setRunResult(null); }} placeholder={selected.question_type === "code" ? "Напишите решение здесь…" : "Опишите решение и объясните основные шаги…"} /></label>
        <div className="open-questions__actions">
          {RUNNABLE_CODE_TASKS.has(selected.code) && <button type="button" className="button button--outline" disabled={!answer.trim() || running || sending} onClick={() => void testCode()}>{running ? "Проверяем код…" : "Пробный запуск"}</button>}
          <button type="button" className="button button--primary" disabled={!answer.trim() || sending || running} onClick={() => void submit()}>{sending ? "Отправляем…" : "Отправить ответ"}</button>
        </div></>}
        {sending && <div className="notice-box" role="status" aria-live="polite">Проверяем ответ моделью · {waitSeconds} с. Проверка может занять несколько минут. Дождитесь результата перед переходом на другую страницу.</div>}
        {runResult && <div className="notice-box" role="status">Пробный запуск: {runResult.tests_passed} из {runResult.tests_total} проверок. {runResult.feedback}</div>}
        {latest && <div className="open-questions__result" role="status"><strong>{latest.reviewed_at ? "Оценка проверена вручную" : latest.needs_manual_review ? "Ожидает проверки" : "Автоматическая оценка"}</strong><p>{latest.needs_manual_review ? "Итоговый балл появится после проверки ответа." : `${Math.round(latest.score * 100)}% · ${latest.feedback}`}</p>{latest.manual_reviewer_notes && <p>Комментарий проверяющего: {latest.manual_reviewer_notes}</p>}{!latest.needs_manual_review && <details className="assessment-info"><summary>Результат по критериям</summary><ul>{Object.entries(latest.criterion_scores).map(([criterion, score]) => <li key={criterion}>{criterion}: {Math.round(score * 100)}%</li>)}</ul></details>}{latest.needs_manual_review && assessmentId && <button type="button" className="button button--outline" disabled={retrying} onClick={() => void retryEvaluation(latest)}>{retrying ? `Проверяем · ${waitSeconds} с` : "Повторить автоматическую проверку"}</button>}<button type="button" className="button button--outline" onClick={() => void refreshResult()}>Обновить результат</button></div>}
      </>}
    </>}
  </section>;
}
