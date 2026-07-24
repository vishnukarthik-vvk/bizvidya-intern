import React , { useState } from 'react';
import { useNavigate , Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import'./Auth.css';

function Login(){
    const[email,setEmail] = useState('');
    const[password, setPassword] = useState('');
    const [submitting , setSubmitting] = useState(false);
    const navigate = useNavigate();
    const [error, setError] = useState('');
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);

        try {
            const response = await fetch('https://bizvidya-intern.onrender.com/login', {
                method: "POST",
                headers: { 'Content-Type': 'application/json'},
                body : JSON.stringify({ email, password}),
            });

            const data = await response.json();
            if (!response.ok){
                if (response.status === 403) {
                    navigate('/verify-otp', { state: { email } });
                    return;
                }
                throw new Error (data.detail || 'failed to log in.');
            }
           localStorage.setItem('user_id', data.user_id);
           localStorage.setItem('user_email', data.email);

           navigate('/')
        } catch(err){
            console.error(err);
            setError(err.message || "something went wrong. please try again");

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
        <div className = 'auth-container'>
            <div className='auth-card'>
                <h1 className = 'auth-title'>Welcome Back</h1>
                <p className='auth-subtitle'>Log in to continue your skill assessment</p>

                {error && <div className='auth-error'>{error}</div>}

                <form onSubmit={handleSubmit} className='auth-form'>
                    <div className='auth-form-group'>
                        <label htmlFor='email'>Email</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            value={email}
                            onChange={(e)=> setEmail(e.target.value)}
                            placeholder='you@example.com'
                            required
                            />
                    </div>

                    <div className='auth-form-group'>
                        <label htmlFor = "password">Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={password}
                            onChange={(e)=>setPassword(e.target.value)}
                            placeholder='your password'
                            required
                            />
                    </div>

                    <button type='submit' className='auth-button' disabled={submitting}>
                        {submitting ? 'Logging in...':'Log In'}
                    </button>
                </form>

                <p className='auth-switch'>
                    dont have an account? <Link to ="/signup">Sign up</Link>
                </p>

                <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                    <GoogleLogin onSuccess={handleGoogleSuccess} onError={() => setError('Google sign-in failed')} />
                </div>
            </div>
        </div>
    )
}


export default Login;