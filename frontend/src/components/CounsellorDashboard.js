import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post, del, getRole } from '../api';
import './Counsellor.css';

// W6 / Counsellor Portal — roster, student detail, notes.
//
// The roster deliberately sorts flagged students first and low scorers second.
// A dashboard that sorts alphabetically is a dashboard nobody triages from.
//
// When a student hasn't granted `counsellor_sharing`, the backend returns a
// masked name and withholds their written answers. That's shown explicitly
// rather than hidden — the counsellor needs to know they're seeing a partial
// picture, and the student needs the option to mean something.

function CounsellorDashboard() {
  const navigate = useNavigate();

  const [students, setStudents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [notes, setNotes] = useState([]);
  const [noteDraft, setNoteDraft] = useState('');
  const [noteVisibility, setNoteVisibility] = useState('private');
  const [noteTag, setNoteTag] = useState('');
  const [onlyAttention, setOnlyAttention] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!['counsellor', 'admin'].includes(getRole())) navigate('/');
  }, [navigate]);

  const loadRoster = useCallback(async () => {
    setLoading(true);
    try {
      const data = await get(`/counsellor/students?needs_attention=${onlyAttention}`);
      setStudents(data.students || []);
    } catch (e) {
      setError(e.detail || 'Could not load your students.');
    } finally {
      setLoading(false);
    }
  }, [onlyAttention]);

  useEffect(() => {
    loadRoster();
  }, [loadRoster]);

  const openStudent = async (id) => {
    setSelectedId(id);
    setDetail(null);
    setNotes([]);
    setError('');
    try {
      const [d, n] = await Promise.all([
        get(`/counsellor/students/${id}`),
        get(`/counsellor/students/${id}/notes`),
      ]);
      setDetail(d);
      setNotes(n.notes || []);
    } catch (e) {
      setError(e.detail || 'Could not open that student.');
    }
  };

  const addNote = async () => {
    if (!noteDraft.trim()) return;
    setBusy(true);
    try {
      await post(`/counsellor/students/${selectedId}/notes`, {
        body: noteDraft.trim(),
        visibility: noteVisibility,
        tag: noteTag || null,
      });
      const n = await get(`/counsellor/students/${selectedId}/notes`);
      setNotes(n.notes || []);
      setNoteDraft('');
      setNoteTag('');
    } catch (e) {
      setError(e.detail || 'Could not save that note.');
    } finally {
      setBusy(false);
    }
  };

  const removeNote = async (id) => {
    try {
      await del(`/counsellor/notes/${id}`);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (e) {
      setError(e.detail || 'Could not delete that note.');
    }
  };

  const markReviewed = async (messageId) => {
    try {
      await post(`/counsellor/messages/${messageId}/reviewed`, {});
      setDetail((d) => ({
        ...d,
        flagged_messages: d.flagged_messages.map((m) =>
          m.id === messageId ? { ...m, reviewed: true } : m
        ),
      }));
      loadRoster();
    } catch (e) {
      setError(e.detail || 'Could not update that flag.');
    }
  };

  return (
    <div className="cp">
      <header className="cp-header">
        <div>
          <h1>Students</h1>
          <p>{students.length} in your institution</p>
        </div>
        <label className="cp-toggle">
          <input
            type="checkbox"
            checked={onlyAttention}
            onChange={(e) => setOnlyAttention(e.target.checked)}
          />
          Only those needing attention
        </label>
      </header>

      {error && <div className="cp-error">{error}</div>}

      <div className="cp-body">
        <nav className="cp-roster">
          {loading && <p className="cp-muted">Loading…</p>}
          {!loading && students.length === 0 && (
            <p className="cp-muted">No students match this view.</p>
          )}
          {students.map((s) => (
            <button
              key={s.student_id}
              className={`cp-row ${s.student_id === selectedId ? 'active' : ''}`}
              onClick={() => openStudent(s.student_id)}
            >
              <span className="cp-row-name">
                {s.display_name}
                {!s.identified && <span className="cp-lock" title="Identity withheld">🔒</span>}
              </span>
              <span className="cp-row-meta">
                {s.assessment_complete
                  ? `${s.overall_score ?? '—'}% overall`
                  : 'assessment not finished'}
              </span>
              {s.flagged_messages > 0 && (
                <span className="cp-flag">{s.flagged_messages} to review</span>
              )}
            </button>
          ))}
        </nav>

        <main className="cp-detail">
          {!detail && <p className="cp-muted">Pick a student to see their report.</p>}

          {detail && (
            <>
              <h2>{detail.student.display_name}</h2>
              <p className="cp-muted">
                {detail.student.education_level || '—'} · {detail.student.domain || '—'} ·
                goal: {detail.student.career_goal || '—'}
              </p>

              {!detail.consent.counsellor_sharing && (
                <div className="cp-consent-note">{detail.consent.note}</div>
              )}

              {detail.flagged_messages.length > 0 && (
                <section className="cp-panel cp-alert">
                  <h3>Flagged by the safety layer</h3>
                  <p className="cp-muted">
                    The message text isn't shown — reach out to the student directly
                    rather than reading their conversation.
                  </p>
                  <ul className="cp-flags">
                    {detail.flagged_messages.map((m) => (
                      <li key={m.id} className={m.reviewed ? 'reviewed' : ''}>
                        <span className={`cp-flag-tag ${m.flag}`}>{m.flag}</span>
                        <span>{m.reason}</span>
                        <span className="cp-muted">
                          {m.created_at ? new Date(m.created_at).toLocaleString() : ''}
                        </span>
                        {!m.reviewed && (
                          <button className="cp-secondary" onClick={() => markReviewed(m.id)}>
                            Mark reviewed
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="cp-panel">
                <h3>Scores</h3>
                {detail.scores.length === 0 && (
                  <p className="cp-muted">No assessment results yet.</p>
                )}
                <ul className="cp-scores">
                  {detail.scores.map((s) => (
                    <li key={s.category}>
                      <span className="cp-score-label">{s.category}</span>
                      <span className="cp-score-bar">
                        <span
                          className={`cp-score-fill ${s.score < 45 ? 'low' : s.score < 70 ? 'mid' : 'high'}`}
                          style={{ width: `${Math.min(100, s.score)}%` }}
                        />
                      </span>
                      <span className="cp-score-val">{s.score}%</span>
                    </li>
                  ))}
                </ul>
              </section>

              {detail.projects.length > 0 && (
                <section className="cp-panel">
                  <h3>Projects</h3>
                  <ul className="cp-projects">
                    {detail.projects.map((p) => (
                      <li key={p.id}>
                        <strong>{p.title}</strong>
                        <span className="cp-muted">
                          {' '}
                          {p.origin === 'self' ? 'self-chosen' : p.focus_category} ·{' '}
                          {p.current_phase} · {p.completion_pct}%
                        </span>
                        {p.recent_logs.length > 0 && (
                          <ul className="cp-loglist">
                            {p.recent_logs.map((l) => (
                              <li key={l.week_key}>
                                {l.week_key}: {l.hours_spent ?? 0} hrs, confidence{' '}
                                {l.confidence ?? '—'}
                                {l.what_blocked_me && ` — blocked: ${l.what_blocked_me}`}
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {detail.narrative?.assessment_summary && (
                <section className="cp-panel">
                  <h3>Assessment summary</h3>
                  <p className="cp-narrative">{detail.narrative.assessment_summary}</p>
                  {detail.narrative.reflection_summary && (
                    <>
                      <h3>Reflection</h3>
                      <p className="cp-narrative">{detail.narrative.reflection_summary}</p>
                    </>
                  )}
                </section>
              )}

              <section className="cp-panel">
                <h3>Notes</h3>
                <textarea
                  rows={3}
                  value={noteDraft}
                  onChange={(e) => setNoteDraft(e.target.value)}
                  placeholder="What you observed, what you agreed, what to follow up on."
                />
                <div className="cp-note-controls">
                  <select value={noteTag} onChange={(e) => setNoteTag(e.target.value)}>
                    <option value="">No tag</option>
                    <option value="followup">Follow up</option>
                    <option value="concern">Concern</option>
                    <option value="win">Win</option>
                    <option value="plan">Plan</option>
                  </select>
                  <select
                    value={noteVisibility}
                    onChange={(e) => setNoteVisibility(e.target.value)}
                  >
                    <option value="private">Only counsellors</option>
                    <option value="shared">Visible to the student</option>
                  </select>
                  <button className="cp-primary" onClick={addNote} disabled={busy}>
                    Save note
                  </button>
                </div>

                <ul className="cp-notes">
                  {notes.map((n) => (
                    <li key={n.id}>
                      <div className="cp-note-head">
                        {n.tag && <span className="cp-tag">{n.tag}</span>}
                        <span className={`cp-vis ${n.visibility}`}>
                          {n.visibility === 'shared' ? 'shared with student' : 'private'}
                        </span>
                        <span className="cp-muted">
                          {n.author} ·{' '}
                          {n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}
                        </span>
                        {n.is_mine && (
                          <button className="cp-link" onClick={() => removeNote(n.id)}>
                            Delete
                          </button>
                        )}
                      </div>
                      <p>{n.body}</p>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default CounsellorDashboard;
