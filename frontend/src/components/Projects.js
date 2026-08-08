import React, { useCallback, useEffect, useState } from 'react';
import { get, post, ApiError } from '../api';
import './Projects.css';

// W6 / Project Module — lifecycle, progress logs, self-chosen ideas, references.
//
// The phase gate is the point of this screen: Build stays locked until Design
// is submitted. Students left to themselves skip straight to building, which is
// the behaviour the module exists to change, so don't "helpfully" unlock them.

const PHASE_HELP = {
  discover: 'Understand the problem before you decide what to make.',
  design: 'Decide the approach and what you are deliberately leaving out.',
  build: 'Make the thing. Log progress weekly, including bad weeks.',
  present: 'Put it in front of someone and say what you would change.',
};

function Projects() {
  const [projects, setProjects] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const [references, setReferences] = useState(null);
  const [loadingRefs, setLoadingRefs] = useState(false);
  const [logs, setLogs] = useState(null);
  const [ideas, setIdeas] = useState(null);
  const [ideasDomain, setIdeasDomain] = useState('');

  const [submitNote, setSubmitNote] = useState('');
  const [submitUrl, setSubmitUrl] = useState('');
  const [logForm, setLogForm] = useState({
    hours_spent: '',
    what_i_did: '',
    what_blocked_me: '',
    confidence: 3,
  });

  const selected = projects.find((p) => p.id === selectedId) || null;

  // ---------------------------------------------------------------- load

  const loadProjects = useCallback(async () => {
    try {
      const data = await get('/projects');
      setProjects(data.projects || []);
      setSelectedId((prev) =>
        prev && data.projects.some((p) => p.id === prev)
          ? prev
          : data.projects?.[0]?.id ?? null
      );
    } catch (e) {
      setError(e.detail || 'Could not load your projects.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    setReferences(null);
    setLogs(null);
    setSubmitNote('');
    setSubmitUrl('');
    if (selectedId) {
      get(`/projects/${selectedId}/logs`)
        .then(setLogs)
        .catch(() => setLogs(null));
    }
  }, [selectedId]);

  // ---------------------------------------------------------------- actions

  const assign = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await post('/projects/assign', { count: 2 });
      await loadProjects();
      setSelectedId(res.assigned?.[0]?.id ?? null);
    } catch (e) {
      setError(e.detail || 'Could not assign a project.');
    } finally {
      setBusy(false);
    }
  };

  const submitPhase = async (phaseName) => {
    if (!submitNote.trim()) {
      setError('Write a line about what you actually did before submitting.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const updated = await post(
        `/projects/${selectedId}/phase/${phaseName}/submit`,
        { note: submitNote.trim(), url: submitUrl.trim() || null }
      );
      setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setSubmitNote('');
      setSubmitUrl('');
      setReferences(null);
    } catch (e) {
      setError(e.detail || 'Could not submit that phase.');
    } finally {
      setBusy(false);
    }
  };

  const loadReferences = async (refresh = false) => {
    setLoadingRefs(true);
    setError('');
    try {
      const res = await post('/buddy/references', {
        project_id: selectedId,
        phase: selected.current_phase,
        refresh,
      });
      setReferences(res.references || []);
    } catch (e) {
      setError(e.detail || 'Could not fetch resources right now.');
    } finally {
      setLoadingRefs(false);
    }
  };

  const saveLog = async () => {
    setBusy(true);
    setError('');
    try {
      await post(`/projects/${selectedId}/logs`, {
        hours_spent: logForm.hours_spent === '' ? null : Number(logForm.hours_spent),
        what_i_did: logForm.what_i_did || null,
        what_blocked_me: logForm.what_blocked_me || null,
        confidence: Number(logForm.confidence),
      });
      setLogs(await get(`/projects/${selectedId}/logs`));
      setLogForm({ hours_spent: '', what_i_did: '', what_blocked_me: '', confidence: 3 });
    } catch (e) {
      setError(e.detail || 'Could not save this week\'s log.');
    } finally {
      setBusy(false);
    }
  };

  const fetchIdeas = async () => {
    if (!ideasDomain.trim()) {
      setError('Pick a domain first.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await post('/projects/ideas', { domain: ideasDomain.trim() });
      setIdeas(res.ideas || []);
    } catch (e) {
      setError(e.detail || 'Could not generate ideas.');
    } finally {
      setBusy(false);
    }
  };

  const adopt = async (idea) => {
    setBusy(true);
    setError('');
    try {
      const created = await post('/projects/adopt', {
        title: idea.title,
        summary: idea.summary,
        difficulty: idea.difficulty || 'core',
        estimated_hours: idea.estimated_hours || 12,
        skills_built: idea.skills_built || [],
        deliverable: idea.deliverable || null,
        first_step: idea.first_step || null,
      });
      setIdeas(null);
      await loadProjects();
      setSelectedId(created.id);
    } catch (e) {
      setError(e.detail || 'Could not start that project.');
    } finally {
      setBusy(false);
    }
  };

  // ---------------------------------------------------------------- render

  if (loading) return <div className="pj-status">Loading your projects…</div>;

  return (
    <div className="pj">
      <header className="pj-header">
        <div>
          <h1>Projects</h1>
          <p>Assigned from your three weakest areas. Four phases, in order.</p>
        </div>
        <button className="pj-primary" onClick={assign} disabled={busy}>
          Assign me a project
        </button>
      </header>

      {error && <div className="pj-error">{error}</div>}

      {projects.length === 0 && (
        <div className="pj-empty">
          <p>
            You don't have any projects yet. Assign one from your assessment results,
            or generate ideas in a domain you choose.
          </p>
        </div>
      )}

      {projects.length > 0 && (
        <div className="pj-body">
          <nav className="pj-list">
            {projects.map((p) => (
              <button
                key={p.id}
                className={`pj-card ${p.id === selectedId ? 'active' : ''} ${p.status}`}
                onClick={() => setSelectedId(p.id)}
              >
                <span className="pj-card-title">{p.title}</span>
                <span className="pj-card-meta">
                  {p.origin === 'self' ? 'Your idea' : p.focus_category}
                </span>
                <span className="pj-bar" aria-hidden="true">
                  <span className="pj-bar-fill" style={{ width: `${p.completion_pct}%` }} />
                </span>
                <span className="pj-card-meta">{p.completion_pct}% · {p.status.replace('_', ' ')}</span>
              </button>
            ))}
          </nav>

          {selected && (
            <main className="pj-detail">
              <h2>{selected.title}</h2>
              <p className="pj-summary">{selected.summary}</p>

              {selected.assignment_rationale && (
                <p className="pj-rationale">{selected.assignment_rationale}</p>
              )}

              {/* ---- lifecycle ---- */}
              <ol className="pj-phases">
                {selected.phases.map((ph) => (
                  <li key={ph.name} className={`pj-phase ${ph.status}`}>
                    <div className="pj-phase-head">
                      <span className="pj-phase-name">{ph.label}</span>
                      <span className="pj-phase-status">{ph.status}</span>
                    </div>
                    {ph.status !== 'locked' && (
                      <>
                        <p className="pj-phase-help">{PHASE_HELP[ph.name]}</p>
                        <ul className="pj-checklist">
                          {ph.checklist.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {ph.status === 'complete' && ph.deliverable_note && (
                      <p className="pj-delivered">
                        Submitted: {ph.deliverable_note}
                        {ph.deliverable_url && (
                          <>
                            {' '}
                            <a href={ph.deliverable_url} target="_blank" rel="noreferrer">
                              link
                            </a>
                          </>
                        )}
                      </p>
                    )}
                  </li>
                ))}
              </ol>

              {/* ---- submit current phase ---- */}
              {selected.status !== 'completed' && selected.status !== 'abandoned' && (
                <section className="pj-panel">
                  <h3>Finish the {selected.current_phase} phase</h3>
                  <textarea
                    value={submitNote}
                    onChange={(e) => setSubmitNote(e.target.value)}
                    placeholder="What did you actually do? Be specific — this is what your counsellor sees."
                    rows={3}
                  />
                  <input
                    type="url"
                    value={submitUrl}
                    onChange={(e) => setSubmitUrl(e.target.value)}
                    placeholder="Link to the deliverable (optional)"
                  />
                  <button
                    className="pj-primary"
                    onClick={() => submitPhase(selected.current_phase)}
                    disabled={busy}
                  >
                    Submit and unlock the next phase
                  </button>
                </section>
              )}

              {/* ---- references (W5) ---- */}
              <section className="pj-panel">
                <div className="pj-panel-head">
                  <h3>Resources for this phase</h3>
                  <button
                    className="pj-secondary"
                    onClick={() => loadReferences(references !== null)}
                    disabled={loadingRefs}
                  >
                    {loadingRefs
                      ? 'Finding…'
                      : references === null
                      ? 'Get resources'
                      : 'Get different ones'}
                  </button>
                </div>
                {references && references.length === 0 && (
                  <p className="pj-muted">Nothing came back. Try again in a moment.</p>
                )}
                {references && references.length > 0 && (
                  <ul className="pj-refs">
                    {references.map((r, i) => (
                      <li key={i}>
                        <span className="pj-ref-type">{r.type}</span>
                        {r.link ? (
                          <a href={r.link} target="_blank" rel="noreferrer">
                            {r.title}
                          </a>
                        ) : (
                          <span className="pj-ref-title">{r.title}</span>
                        )}
                        <span className="pj-ref-effort">{r.effort}</span>
                        <p>{r.why}</p>
                        {!r.link && r.how_to_find && (
                          <p className="pj-muted">Search for: {r.how_to_find}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* ---- weekly log ---- */}
              <section className="pj-panel">
                <div className="pj-panel-head">
                  <h3>This week</h3>
                  {logs && (
                    <span className="pj-muted">
                      {logs.weeks_logged} week{logs.weeks_logged === 1 ? '' : 's'} logged ·{' '}
                      {logs.total_hours} hrs · {logs.current_streak_weeks}-week streak
                    </span>
                  )}
                </div>
                <div className="pj-log-form">
                  <label>
                    Hours this week
                    <input
                      type="number"
                      min="0"
                      max="80"
                      step="0.5"
                      value={logForm.hours_spent}
                      onChange={(e) => setLogForm({ ...logForm, hours_spent: e.target.value })}
                    />
                  </label>
                  <label>
                    Confidence (1–5)
                    <input
                      type="range"
                      min="1"
                      max="5"
                      value={logForm.confidence}
                      onChange={(e) => setLogForm({ ...logForm, confidence: e.target.value })}
                    />
                    <span className="pj-muted">{logForm.confidence}</span>
                  </label>
                  <textarea
                    rows={2}
                    placeholder="What did you get done?"
                    value={logForm.what_i_did}
                    onChange={(e) => setLogForm({ ...logForm, what_i_did: e.target.value })}
                  />
                  <textarea
                    rows={2}
                    placeholder="What blocked you? (this is the useful part)"
                    value={logForm.what_blocked_me}
                    onChange={(e) => setLogForm({ ...logForm, what_blocked_me: e.target.value })}
                  />
                  <button className="pj-secondary" onClick={saveLog} disabled={busy}>
                    Save this week
                  </button>
                </div>

                {logs && logs.logs.length > 0 && (
                  <ul className="pj-log-history">
                    {[...logs.logs].reverse().map((l) => (
                      <li key={l.week_key}>
                        <strong>{l.week_key}</strong>
                        <span className="pj-muted">
                          {' '}
                          {l.hours_spent ?? 0} hrs · {l.phase}
                        </span>
                        {l.what_i_did && <p>{l.what_i_did}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </main>
          )}
        </div>
      )}

      {/* ---- self-chosen ---- */}
      <section className="pj-panel pj-ideas">
        <h3>Or bring your own</h3>
        <p className="pj-muted">
          Pick a domain and get five buildable ideas shaped around your weakest areas.
        </p>
        <div className="pj-ideas-row">
          <input
            value={ideasDomain}
            onChange={(e) => setIdeasDomain(e.target.value)}
            placeholder="e.g. embedded systems, quantum hardware, marketing"
          />
          <button className="pj-secondary" onClick={fetchIdeas} disabled={busy}>
            Generate ideas
          </button>
        </div>

        {ideas && (
          <ul className="pj-idea-list">
            {ideas.map((idea, i) => (
              <li key={i}>
                <div className="pj-idea-head">
                  <strong>{idea.title}</strong>
                  <span className="pj-tag">{idea.difficulty}</span>
                  <span className="pj-muted">~{idea.estimated_hours} hrs</span>
                </div>
                <p>{idea.summary}</p>
                {idea.first_step && (
                  <p className="pj-muted">First step: {idea.first_step}</p>
                )}
                <button className="pj-secondary" onClick={() => adopt(idea)} disabled={busy}>
                  Start this
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default Projects;
