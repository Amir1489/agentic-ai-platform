import { useCallback, useEffect, useState } from 'react';
import { MessageCircle, Plus, Send, Trash2, LoaderCircle, MessagesSquare } from 'lucide-react';
import './chat.css';

type Lang = 'fa' | 'en';
type Conversation = { id: number; title: string; created: string; updated: string; message_count: number };
type Message = { id: number; role: 'user' | 'assistant'; content: string; created: string };

const copy = {
  fa: {
    title: 'گفتگوهای من', new: 'گفتگوی جدید', empty: 'هنوز گفتگویی نداری',
    select: 'یک گفتگو را انتخاب کن یا گفتگوی تازه‌ای بساز.', placeholder: 'پیامت را اینجا بنویس...',
    send: 'ارسال', loading: 'در حال بارگذاری...', error: 'خطا در ارتباط با سرور',
    saved: 'پاسخ هوش مصنوعی دریافت شد.', notConfigured: 'مدل هوش مصنوعی هنوز روی سرور پیکربندی نشده است.',
    notice: 'گفتگوها در حساب شما ذخیره می‌شوند.', delete: 'حذف گفتگو',
    you: 'شما', assistant: 'دستیار', deleteConfirm: 'این گفتگو حذف شود؟'
  },
  en: {
    title: 'My conversations', new: 'New conversation', empty: 'No conversations yet',
    select: 'Choose a conversation or start a new one.', placeholder: 'Write your message...',
    send: 'Send', loading: 'Loading...', error: 'Could not connect to the server',
    saved: 'AI response received.', notConfigured: 'The AI model is not configured on the server yet.',
    notice: 'Your conversations are stored in your account.', delete: 'Delete conversation',
    you: 'You', assistant: 'Assistant', deleteConfirm: 'Delete this conversation?'
  }
};

export default function ChatPanel({ lang, token }: { lang: Lang; token?: string | null }) {
  const t = copy[lang];
  const api = import.meta.env.VITE_API_URL?.replace(/\/$/, '');
  const [items, setItems] = useState<Conversation[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [loadingList, setLoadingList] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const headers = { Authorization: 'Bearer ' + (token || ''), 'Content-Type': 'application/json' };

  const load = useCallback(async () => {
    if (!api || !token) return;
    setLoadingList(true);
    setError('');
    try {
      const response = await fetch(api + '/api/conversations', { headers });
      if (!response.ok) throw new Error('Conversation list request failed');
      const data: Conversation[] = await response.json();
      setItems(data);
      setActive(current => current && data.some(item => item.id === current) ? current : null);
    } catch {
      setError(t.error);
    } finally {
      setLoadingList(false);
    }
  }, [api, token, t.error]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (!api || !token || active === null) {
      setMessages([]);
      return;
    }
    let current = true;
    setMessages([]);
    fetch(api + '/api/conversations/' + active + '/messages', { headers })
      .then(async response => {
        if (!response.ok) throw new Error('Message history request failed');
        return response.json();
      })
      .then((data: Message[]) => { if (current) setMessages(data); })
      .catch(() => { if (current) setError(t.error); });
    return () => { current = false; };
  }, [api, token, active, t.error]);

  async function create() {
    if (!api || !token || creating || sending) return;
    setCreating(true);
    setError('');
    try {
      const response = await fetch(api + '/api/conversations', {
        method: 'POST', headers,
        body: JSON.stringify({ title: lang === 'fa' ? 'گفتگوی جدید' : 'New conversation' })
      });
      if (!response.ok) throw new Error('Conversation creation failed');
      const row: Conversation = await response.json();
      setItems(previous => [row, ...previous]);
      setActive(row.id);
      setMessages([]);
      setNotice('');
    } catch {
      setError(t.error);
    } finally {
      setCreating(false);
    }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || active === null || !api || !token || sending || creating) return;
    setSending(true);
    setError('');
    setNotice('');
    try {
      const response = await fetch(api + '/api/conversations/' + active + '/messages', {
        method: 'POST', headers, body: JSON.stringify({ content })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        if (response.status === 503) {
          setError(t.notConfigured);
          return;
        }
        throw new Error(typeof body.detail === 'string' ? body.detail : 'Message request failed');
      }
      const data = await response.json();
      setMessages(previous => [...previous, data.user_message, data.assistant_message]);
      setDraft('');
      setNotice(t.saved);
      void load();
    } catch {
      setError(t.error);
    } finally {
      setSending(false);
    }
  }

  async function remove(id: number) {
    if (!api || !token || deletingId !== null || sending || creating) return;
    if (!window.confirm(t.deleteConfirm)) return;
    setDeletingId(id);
    setError('');
    try {
      const response = await fetch(api + '/api/conversations/' + id, { method: 'DELETE', headers });
      if (!response.ok) throw new Error('Conversation deletion failed');
      setItems(previous => previous.filter(item => item.id !== id));
      if (active === id) {
        setActive(null);
        setMessages([]);
      }
    } catch {
      setError(t.error);
    } finally {
      setDeletingId(null);
    }
  }

  const busy = creating || sending || deletingId !== null;

  return (
    <section className="chat-shell" aria-label={t.title}>
      <aside className="chat-list">
        <div className="chat-list-head">
          <h2>{t.title}</h2>
          <button onClick={() => void create()} disabled={busy} aria-label={t.new} title={t.new}>
            {creating ? <LoaderCircle className="chat-spin" size={18} /> : <Plus size={18} />}
          </button>
        </div>
        {loadingList && items.length === 0 ? <p className="chat-muted">{t.loading}</p> :
          items.length === 0 ? <p className="chat-muted">{t.empty}</p> :
          items.map(item => (
            <div className={'chat-item ' + (active === item.id ? 'active' : '')} key={item.id}>
              <button className="chat-item-main" onClick={() => setActive(item.id)} disabled={busy}>
                <MessageCircle size={17} /><span>{item.title}</span>
              </button>
              <button className="chat-remove" onClick={() => void remove(item.id)}
                disabled={busy} aria-label={t.delete} title={t.delete}>
                {deletingId === item.id ? <LoaderCircle className="chat-spin" size={15} /> : <Trash2 size={15} />}
              </button>
            </div>
          ))}
      </aside>
      <div className="chat-room">
        {active === null ?
          <div className="chat-welcome">
            <MessagesSquare size={42} /><h3>{t.select}</h3>
            <button className="dash-create" onClick={() => void create()} disabled={busy}>
              <Plus size={17} />{t.new}
            </button>
          </div> :
          <>
            <div className="chat-messages" aria-live="polite">
              {messages.length === 0 ? <p className="chat-muted">{loadingList ? t.loading : t.select}</p> :
                messages.map(message => (
                  <article className={'chat-bubble ' + (message.role === 'user' ? 'user' : 'assistant')} key={message.id}>
                    <small>{message.role === 'user' ? t.you : t.assistant}</small>
                    <p>{message.content}</p>
                  </article>
                ))}
              {sending && <p className="chat-muted">{t.loading}</p>}
            </div>
            <form className="chat-compose" onSubmit={send}>
              <textarea value={draft} onChange={event => setDraft(event.target.value)}
                placeholder={t.placeholder} maxLength={12000} rows={2} disabled={busy} />
              <button className="dash-create" type="submit" disabled={busy || !draft.trim()} aria-label={t.send}>
                {sending ? <LoaderCircle className="chat-spin" size={18} /> : <Send size={18} />}
              </button>
            </form>
          </>
        }
        <p className="chat-notice">{notice || t.notice}</p>
        {error && <p className="chat-error" role="alert">{error}</p>}
      </div>
    </section>
  );
}
