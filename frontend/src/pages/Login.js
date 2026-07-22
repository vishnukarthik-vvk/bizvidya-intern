import React , { useState } from 'react';
import { useNavigate , Link } from 'react-router-dom';
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
            const response = await fetch('http://127.0.0.1:8000/login', {
                method: "POST",
                headers: { 'Content-Type': 'application/json'},
                body : JSON.stringify({ email, password}),
            });

            const data = await response.json();
            if (!response.ok){
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
            </div>
        </div>
    )
}


export default Login;