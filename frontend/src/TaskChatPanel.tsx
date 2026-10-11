import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiGet, apiPost } from "./api";

type TaskMessage = {
  id: string;
  body: string;
  created_at: string;
  is_mine: boolean;
};

export type TaskConversation = {
  submission_id: string;
  task_title: string;
  other_name: string;
  last_message: string | null;
  updated_at: string;
};

export default function TaskChatPanel({
  submissionId,
  taskTitle,
  otherName,
  onMessageSent,
}: {
  submissionId: string;
  taskTitle: string;
  otherName: string;
  onMessageSent?: () => void;
}) {
  const [messages, setMessages] = useState<TaskMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    const load = async () => {
      try {
        const result = await apiGet<TaskMessage[]>(`/tasks/submissions/${submissionId}/messages`);
        if (!cancelled) { setMessages(result); setError(""); }
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить переписку");
      } finally {
        if (!cancelled) { setLoading(false); timer = window.setTimeout(() => void load(), 5000); }
      }
    };
    void load();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [submissionId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages.length]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim()) return;
    setSending(true);
    try {
      const sent = await apiPost<TaskMessage>(`/tasks/submissions/${submissionId}/messages`, { body: draft.trim() });
      setMessages((current) => [...current, sent]);
      setDraft("");
      setError("");
      onMessageSent?.();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  };

  return <section className="conversation-panel task-conversation" aria-label={`Переписка по заданию ${taskTitle}`}>
    <header className="conversation-panel__header"><div><span>ЛИЧНАЯ ПЕРЕПИСКА ПО ЗАДАНИЮ</span><strong>{otherName}</strong><small>{taskTitle}</small></div></header>
    {error && <div className="conversation-error" role="alert">{error}</div>}
    <div className="conversation-messages">
      {loading ? <div className="empty-state">Загружаем сообщения…</div> : messages.length === 0 ? <div className="empty-state">Сообщений пока нет. Напишите по поводу решения задания.</div> : messages.map((message) => <div className={`conversation-message-row${message.is_mine ? " conversation-message-row--mine" : ""}`} key={message.id}><article className={`conversation-message${message.is_mine ? " conversation-message--mine" : ""}`}><p>{message.body}</p><time dateTime={message.created_at}>{new Date(message.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}</time></article></div>)}
      <div ref={bottomRef} />
    </div>
    <form className="conversation-composer" onSubmit={(event) => void send(event)}>
      <label htmlFor={`task-message-${submissionId}`}>Сообщение</label>
      <textarea id={`task-message-${submissionId}`} value={draft} maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Напишите сообщение…" rows={3} />
      <div><small>{draft.length}/4000</small><button className="button" type="submit" disabled={!draft.trim() || sending}>{sending ? "Отправляем…" : "Отправить"}</button></div>
    </form>
  </section>;
}
