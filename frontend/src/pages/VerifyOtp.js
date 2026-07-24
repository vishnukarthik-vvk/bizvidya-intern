import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Auth.css';

function VerifyOtp() {
    const location = useLocation();
    const navigate = useNavigate();
    const [email] = useState(location.state?.email || '');
    const [otp, setOtp] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [resending, setResending] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            const response = await fetch('http://127.0.0.1:8000/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'verification failed');

            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('user_email', data.email);
            navigate('/');
        } catch (err) {
            setError(err.message || 'something went wrong');
        } finally {
            setSubmitting(false);
        }
    };

    const handleResend = async () => {
        setError('');
        setResending(true);
        try {
            const response = await fetch('http://127.0.0.1:8000/resend-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'could not resend code');
        } catch (err) {
            setError(err.message || 'something went wrong');
        } finally {
            setResending(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h1 className="auth-title">Verify Your Email</h1>
                <p className="auth-subtitle">Enter the 6-digit code sent to {email}</p>

                {error && <div className="auth-error">{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-form-group">
                        <label htmlFor="otp">Verification Code</label>
                        <input
                            type="text"
                            id="otp"
                            value={otp}
                            onChange={(e) => setOtp(e.target.value)}
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
                    <button type="button" onClick={handleResend} disabled={resending} style={{ background: 'none', border: 'none', color: '#6d5bd0', cursor: 'pointer', textDecoration: 'underline' }}>
                        {resending ? 'Sending...' : 'Resend code'}
                    </button>
                </p>
            </div>
        </div>
    );
}

export default VerifyOtp;