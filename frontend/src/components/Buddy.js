import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post, del, ApiError } from '../api';
import './Buddy.css';

// W5 / AI Buddy / Chat UI.
//
// Behaviour worth keeping if you refactor:
//  - a crisis reply is rendered differently and is never collapsed into the
//    normal message stream styling; it needs to be impossible to skim past
//  - the composer stays enabled while a reply is in flight so the student can
//    keep typing, but sending is blocked until the reply lands
//  - conversations are loaded lazily; only the selected session fetches messages

const SUGGESTIONS = [
  'What should I work on first this week?',
  'I\'m stuck on the discover phase — what does "good" look like?',
  'Explain my weakest category in plain terms',
  'Give me a harder version of my current project',
];

function Buddy() {
  const navigate = useNavigate();

  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [error, setError] = useState('');
  const [consentBlocked, setConsentBlocked] = useState(false);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  // ---------------------------------------------------------------- loading

  const loadSessions = useCallback(async () => {
    try {
      const data = await get('/buddy/sessions');
      setSessions(data || []);
      if (data && data.length && activeId === null) setActiveId(data[0].id);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setConsentBlocked(true);
        return;
      }
      setError(e.detail || 'Could not load your conversations.');
    }
  }, [activeId]);

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeId === null) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingThread(true);
    get(`/buddy/sessions/${activeId}/messages`)
      .then((rows) => {
        if (!cancelled) setMessages(rows || []);
      })
      .catch((e) => {
        if (!cancelled) setError(e.detail || 'Could not open that conversation.');
      })
      .finally(() => {
        if (!cancelled) setLoadingThread(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending]);

  // ---------------------------------------------------------------- actions

  const send = async (text) => {
    const content = (text ?? draft).trim();
    if (!content || sending) return;

    setError('');
    setDraft('');
    setSending(true);

    // Optimistic echo so the UI doesn't feel dead while the model thinks.
    const tempId = `tmp-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tempId, role: 'user', content }]);

    try {
      const res = await post('/buddy/chat', {
        session_id: activeId ?? undefined,
        message: content,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: res.reply,
          guardrail_flag: res.guardrail_flag,
        },
      ]);

      if (activeId !== res.session_id) {
        setActiveId(res.session_id);
        loadSessions();
      } else {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === res.session_id ? { ...s, message_count: (s.message_count || 0) + 2 } : s
          )
        );
      }
    } catch (e) {
      // Roll the optimistic message back and put the text in the box so the
      // student doesn't lose what they typed.
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      setDraft(content);
      if (e instanceof ApiError && e.status === 403) {
        setConsentBlocked(true);
      } else {
        setError(e.detail || 'That message did not go through. Try again.');
      }
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  };

  const startNew = () => {
    setActiveId(null);
    setMessages([]);
    setError('');
    textareaRef.current?.focus();
  };

  const archive = async (id, e) => {
    e.stopPropagation();
    try {
      await del(`/buddy/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) startNew();
    } catch (err) {
      setError(err.detail || 'Could not archive that conversation.');
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  // ---------------------------------------------------------------- render

  if (consentBlocked) {
    return (
      <div className="buddy-gate">
        <h2>AI Buddy is switched off</h2>
        <p>
          Buddy stores your conversations so it remembers what you're working on
          between sessions. That needs your permission first.
        </p>
        <button className="buddy-primary" onClick={() => navigate('/privacy')}>
          Open privacy settings
        </button>
      </div>
    );
  }

  return (
    <div className="buddy">
      <aside className="buddy-sidebar">
        <button className="buddy-new" onClick={startNew}>
          + New conversation
        </button>
        <div className="buddy-session-list">
          {sessions.length === 0 && (
            <p className="buddy-empty-note">No conversations yet.</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              onClick={() => setActiveId(s.id)}
              onKeyDown={(e) => e.key === 'Enter' && setActiveId(s.id)}
              className={`buddy-session ${s.id === activeId ? 'active' : ''}`}
            >
              <span className="buddy-session-title">{s.title || 'Untitled'}</span>
              <button
                className="buddy-archive"
                aria-label="Archive conversation"
                onClick={(e) => archive(s.id, e)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="buddy-main">
        <header className="buddy-header">
          <h1>Buddy</h1>
          <p>Your project and career companion. It knows your scores and your projects.</p>
        </header>

        <div className="buddy-thread" ref={scrollRef}>
          {loadingThread && <div className="buddy-status">Opening…</div>}

          {!loadingThread && messages.length === 0 && (
            <div className="buddy-welcome">
              <p>Ask me something about your results or your current project.</p>
              <div className="buddy-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} disabled={sending}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div
              key={m.id}
              className={`buddy-msg ${m.role} ${
                m.guardrail_flag === 'crisis' ? 'crisis' : ''
              }`}
            >
              <div className="buddy-msg-body">{m.content}</div>
            </div>
          ))}

          {sending && (
            <div className="buddy-msg assistant">
              <div className="buddy-msg-body buddy-typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
        </div>

        {error && <div className="buddy-error">{error}</div>}

        <div className="buddy-composer">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about your results, your project, or what to do next…"
            rows={2}
            maxLength={4000}
          />
          <button
            className="buddy-primary"
            onClick={() => send()}
            disabled={sending || !draft.trim()}
          >
            {sending ? 'Thinking…' : 'Send'}
          </button>
        </div>
        <p className="buddy-disclaimer">
          Buddy is an AI. It won't write graded work, and it isn't a substitute for a
          counsellor or a doctor.
        </p>
      </section>
    </div>
  );
}

export default Buddy;
