// src/pages/Login.js
// Place this file at: src/pages/Login.js

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import './Auth.css';
import { post, setSession, ApiError } from '../api';

function Login() {
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]         = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const data = await post('/login', { email, password }, { auth: false });
      setSession(data);
      // Send counsellors straight to their portal
      if (data.role === 'counsellor' || data.role === 'admin') {
        navigate('/counsellor');
      } else {
        navigate('/');
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        // Account exists but email not yet verified
        navigate('/verify-otp', { state: { email } });
        return;
      }
      setError(err.detail || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    try {
      const data = await post('/auth/google', { token: credentialResponse.credential }, { auth: false });
      setSession(data);
      if (data.role === 'counsellor' || data.role === 'admin') {
        navigate('/counsellor');
      } else {
        navigate('/');
      }
    } catch (err) {
      setError(err.detail || 'Google sign-in failed');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Welcome Back</h1>
        <p className="auth-subtitle">Log in to continue your skill assessment</p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Your password"
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={submitting}>
            {submitting ? 'Logging in...' : 'Log In'}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <Link to="/signup">Sign up</Link>
        </p>

        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google sign-in failed')}
          />
        </div>
      </div>
    </div>
  );
}

export default Login;
