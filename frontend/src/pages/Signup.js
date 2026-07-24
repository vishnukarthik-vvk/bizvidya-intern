import React , { useState } from "react";
import { useNavigate,Link } from 'react-router-dom';
import './Auth.css';
import { GoogleLogin } from '@react-oauth/google';

function Signup(){
    const [email, setEmail] = useState('');
    const[password, setPassword] = useState('');
    const[confirmPassword, setConfirmPassword] = useState('');
    const[error ,setError] = useState('');
    const[submitting, setSubmitting] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async(e) => {
        e.preventDefault()
        setError('');

        if (password.length < 8){
            setError('password must be atleast 8 characters long.');
            return;
        }
        if (password !== confirmPassword){
            setError('passwords do not match.');
            return;
        }
        

        setSubmitting(true);
        try {
            const response = await fetch('https://bizvidya-intern.onrender.com/signup',{
                method : 'POST',
                headers: {'Content-Type': 'application/json'},
                body : JSON.stringify({email, password}),

            });

            const data = await response.json();
            if(!response.ok) {
                throw new Error(data.detail || 'failed to create account');

            }

            navigate('/verify-otp', { state: { email } });
        } catch (err) {
            console.error(err);
            setError(err.message || 'Something went wrong. Please try again.');

        } finally {
            setSubmitting(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse) => {
        setError('');
        try {
            const response = await fetch('http://127.0.0.1:8000/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: credentialResponse.credential }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Google sign-in failed');
            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('user_email', data.email);
            navigate('/');
        } catch (err) {
            setError(err.message || 'Google sign-in failed');
        }
    };


      return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Create Your Account</h1>
        <p className="auth-subtitle">Sign up to start your skill assessment</p>
 
        {error && <div className="auth-error">{error}</div>}
 
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              minLength={8}
            />
          </div>
 
          <div className="auth-form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              required
              minLength={8}
            />
          </div>
 
          <button type="submit" className="auth-button" disabled={submitting}>
            {submitting ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>
 
        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>

        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <GoogleLogin onSuccess={handleGoogleSuccess} onError={() => setError('Google sign-in failed')} />
        </div>
      </div>
    </div>
  );
}
 
export default Signup;
