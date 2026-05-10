import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { jwtDecode } from 'jwt-decode';

export default function LoginPage() {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegistering) {
        await register(email, password);
      }
      // Log in immediately after register (or if just logging in)
      const { data } = await login(email, password);
      const decoded = jwtDecode(data.access_token);
      signIn(data.access_token, { id: decoded.sub, role: decoded.role, email });
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || (isRegistering ? 'Registration failed. Email might be in use.' : 'Login failed. Please check your credentials.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <img src="https://techkraftinc.com/wp-content/uploads/2024/05/TechKraft-Logo.svg" alt="TechKraft Logo" className="logo-img" />
          <h1>Recruitment Dashboard</h1>
          <p>Internal Candidate Review System</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="alert alert-error">{error}</div>}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@techkraft.com"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <span className="spinner-sm" /> : (isRegistering ? 'Create Account' : 'Sign In')}
          </button>
        </form>
        
        <div className="login-toggle">
          {isRegistering ? "Already have an account?" : "Don't have an account?"}
          <button className="login-toggle-btn" onClick={() => { setIsRegistering(!isRegistering); setError(''); }}>
            {isRegistering ? "Sign In" : "Sign Up"}
          </button>
        </div>

        <p className="login-hint">
          {isRegistering ? (
            <><strong>Note:</strong> New accounts are automatically assigned the <strong>reviewer</strong> role per system policy.</>
          ) : (
            <>
              <strong>Demo credentials:</strong><br />
              Admin: admin@techkraft.com / Admin1234!<br />
              Reviewer: reviewer@techkraft.com / Review1234!
            </>
          )}
        </p>
      </div>
    </div>
  );
}
