// src/pages/VerifyOtp.js
// Place this file at: src/pages/VerifyOtp.js

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Auth.css';
import { post, setSession } from '../api';

function VerifyOtp() {
  const location = useLocation();
  const navigate = useNavigate();

  const [email]         = useState(location.state?.email || '');
  const [otp, setOtp]   = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending]   = useState(false);
  const [notice, setNotice]         = useState('');
  const [error, setError]           = useState(
    location.state?.emailSent === false
      ? "We couldn't send your verification email. Tap 'Resend code' below to try again."
      : ''
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    setSubmitting(true);
    try {
      const data = await post('/verify-otp', { email, otp }, { auth: false });
      setSession(data);
      // Go to consent gate before the app
      navigate('/privacy-setup');
    } catch (err) {
      setError(err.detail || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setNotice('');
    setResending(true);
    try {
      await post('/resend-otp', { email }, { auth: false });
      setNotice('New code sent. Check your inbox.');
    } catch (err) {
      setError(err.detail || 'Could not resend code. Try again in a moment.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Verify Your Email</h1>
        <p className="auth-subtitle">Enter the 6-digit code sent to {email}</p>

        {error  && <div className="auth-error">{error}</div>}
        {notice && <div className="auth-error" style={{ background: '#eaf6f0', color: '#2f6b52', borderColor: '#a8d5c2' }}>{notice}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-form-group">
            <label htmlFor="otp">Verification Code</label>
            <input
              type="text"
              id="otp"
              value={otp}
              onChange={e => setOtp(e.target.value)}
              placeholder="6-digit code"
              maxLength={6}
              required
            />
          </div>
          <button type="submit" className="auth-button" disabled={submitting}>
            {submitting ? 'Verifying...' : 'Verify'}
          </button>
        </form>

        <p className="auth-switch">
          Didn't get a code?{' '}
          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            style={{
              background: 'none',
              border: 'none',
              color: '#6d5bd0',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            {resending ? 'Sending...' : 'Resend code'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default VerifyOtp;
