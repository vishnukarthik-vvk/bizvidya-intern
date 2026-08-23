import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post, clearSession, API_BASE, getToken } from '../api';
import './Counsellor.css';

// W6 / Security / Privacy Controls — the consent screen.
//
// Two things this gets right that consent screens usually don't:
//  1. The required scope can't be toggled off — instead it points at deletion,
//     which is the honest option. A toggle that silently does nothing is worse
//     than no toggle.
//  2. Turning off AI Buddy actually archives the conversations server-side.

function PrivacySettings({ gate = false }) {
  const navigate = useNavigate();
  const [consents, setConsents] = useState([]);
  const [needsConsent, setNeedsConsent] = useState(false);
  const [pending, setPending] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    get('/privacy/consent')
      .then((d) => {
        setConsents(d.consents || []);
        setNeedsConsent(d.needs_consent);
        setPending(
          Object.fromEntries(
            (d.consents || []).map((c) => [
              c.scope,
              c.required ? true : c.granted
            ])
          )
        );
      })
      .catch((e) => setError(e.detail || 'Could not load your privacy settings.'))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setBusy(true);
    setError('');
    try {
      const d = await post('/privacy/consent', {
        consents: Object.entries(pending).map(([scope, granted]) => ({ scope, granted })),
      });
      setConsents(d.consents || []);
      setNeedsConsent(d.needs_consent);
      if (gate && !d.needs_consent) navigate('/');
    } catch (e) {
      setError(e.detail || 'Could not save your choices.');
    } finally {
      setBusy(false);
    }
  };

  const exportData = async () => {
    // Downloaded rather than rendered — the payload can be large and the point
    // is that the student ends up with a file they own.
    try {
      const res = await fetch(`${API_BASE}/privacy/export`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error('export failed');
      const blob = new Blob([JSON.stringify(await res.json(), null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'my-data.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Could not prepare your download. Try again.');
    }
  };

  const deleteEverything = async () => {
    setBusy(true);
    try {
      await post('/privacy/delete', { confirm_email: confirmEmail });
      clearSession();
      navigate('/signup');
    } catch (e) {
      setError(e.detail || 'Could not delete your data.');
      setBusy(false);
    }
  };

  if (loading) return <p className="cp-muted" style={{ padding: '3rem' }}>Loading…</p>;

  return (
    <div className="cp cp-narrow">
      <h1>{gate ? 'Before you start' : 'Privacy'}</h1>
      <p className="cp-muted">
        {gate
          ? 'Choose what you are comfortable with. You can change any of this later.'
          : 'Change what you share, download everything we hold, or delete your account.'}
      </p>

      {error && <div className="cp-error">{error}</div>}

      <ul className="cp-consents">
        {consents.map((c) => (
          <li key={c.scope}>
            <label>
              <input
                type="checkbox"
                checked={!!pending[c.scope]}
                disabled={c.required}
                onChange={(e) =>
                  setPending((p) => ({ ...p, [c.scope]: e.target.checked }))
                }
              />
              <span>
                <strong>{c.label}</strong>
                {c.required && <em className="cp-required"> required</em>}
                <p>{c.description}</p>
              </span>
            </label>
          </li>
        ))}
      </ul>

      {/* The required scope is checked and locked. Rather than pretending it's a
          choice, point at the option that actually exists. */}
      <button className="cp-primary" onClick={save} disabled={busy}>
        {gate ? 'Agree and continue' : 'Save changes'}
      </button>

      {needsConsent && (
        <p className="cp-muted" style={{ marginTop: '0.6rem' }}>
          You can't take the assessment until you agree to results being stored.
        </p>
      )}

      {!gate && (
        <section className="cp-panel" style={{ marginTop: '2rem' }}>
          <h3>Your data</h3>
          <button className="cp-secondary" onClick={exportData}>
            Download everything we hold
          </button>

          <h3 style={{ marginTop: '1.5rem' }}>Delete my account</h3>
          <p className="cp-muted">
            This removes your assessment results, Buddy conversations, projects and
            profile. It can't be undone.
          </p>
          {!showDelete ? (
            <button className="cp-danger" onClick={() => setShowDelete(true)}>
              Delete my data
            </button>
          ) : (
            <div className="cp-note-controls">
              <input
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder="Type your email to confirm"
              />
              <button className="cp-danger" onClick={deleteEverything} disabled={busy}>
                Permanently delete
              </button>
              <button className="cp-link" onClick={() => setShowDelete(false)}>
                Cancel
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default PrivacySettings;
