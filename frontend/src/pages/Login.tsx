import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuthStore } from '../store/authStore';
import { TokenResponse } from '../types/auth';

export const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post<TokenResponse>('/auth/login', { username, password });
      const data = resp.data;
      setUser({ user_id: data.user_id, username: data.username, role: data.role },
               data.access_token, data.refresh_token);
      navigate('/');
    } catch (err: unknown) {
      const msg = (err as any)?.response?.data?.detail || 'Login failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f1f5f9' }}>
      <div style={{ background: '#fff', padding: 32, borderRadius: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.1)', width: 360 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 32, marginBottom: 4 }}>☢</div>
          <h2 style={{ margin: 0, color: '#1e293b' }}>IQ-RAD</h2>
          <p style={{ color: '#64748b', fontSize: 13, margin: '4px 0 0' }}>Radiation Monitoring System</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Username</label>
            <input
              type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 4, boxSizing: 'border-box' }}
              autoFocus required
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Password</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 4, boxSizing: 'border-box' }}
              required
            />
          </div>

          {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{error}</div>}

          <button
            type="submit" disabled={loading}
            style={{ width: '100%', padding: '10px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={{ fontSize: 11, color: '#9ca3af', textAlign: 'center', marginTop: 16 }}>
          21 CFR Part 11 compliant • All sessions logged
        </p>
      </div>
    </div>
  );
};
