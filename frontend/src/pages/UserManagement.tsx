/**
 * User Management — ADMIN only. Create, enable/disable users, reset passwords.
 * All changes written to audit_trail automatically by AuditMiddleware.
 */
import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { format } from 'date-fns';

interface User {
  user_id: number;
  username: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  failed_login_count: number;
}

const ROLES = ['VIEWER', 'EMISSIONS', 'OPERATOR', 'ADMIN', 'DEVELOPER'];

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({ username: '', full_name: '', email: '', role: 'VIEWER', password: '' });
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchUsers = async () => {
    const resp = await api.get<User[]>('/users');
    setUsers(resp.data);
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await api.post('/users', createForm);
      setShowCreateForm(false);
      setCreateForm({ username: '', full_name: '', email: '', role: 'VIEWER', password: '' });
      await fetchUsers();
    } catch (err: any) {
      setCreateError(err?.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    await api.patch(`/users/${u.user_id}`, { is_active: !u.is_active });
    await fetchUsers();
  };

  const handleUnlock = async (u: User) => {
    await api.post(`/users/${u.user_id}/unlock`);
    await fetchUsers();
  };

  const roleColor: Record<string, string> = {
    ADMIN: '#7c3aed', DEVELOPER: '#0891b2', OPERATOR: '#1e40af',
    EMISSIONS: '#059669', VIEWER: '#64748b',
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 20, color: '#1e293b' }}>User Management</h1>
        <button onClick={() => setShowCreateForm(!showCreateForm)}
          style={{ padding: '8px 16px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
          + Create User
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} style={{
          background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20, marginBottom: 20,
        }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 14 }}>New User</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { key: 'username', label: 'Username', type: 'text' },
              { key: 'full_name', label: 'Full Name', type: 'text' },
              { key: 'email', label: 'Email', type: 'email' },
              { key: 'password', label: 'Initial Password', type: 'password' },
            ].map(f => (
              <div key={f.key}>
                <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>{f.label}</label>
                <input type={f.type} value={(createForm as any)[f.key]}
                  onChange={e => setCreateForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                  required
                  style={{ width: '100%', padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13, boxSizing: 'border-box' }} />
              </div>
            ))}
            <div>
              <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Role</label>
              <select value={createForm.role} onChange={e => setCreateForm(prev => ({ ...prev, role: e.target.value }))}
                style={{ width: '100%', padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          {createError && <div style={{ color: '#ef4444', fontSize: 12, marginTop: 8 }}>{createError}</div>}
          <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
            <button type="submit" disabled={creating}
              style={{ padding: '8px 18px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
              {creating ? 'Creating…' : 'Create User'}
            </button>
            <button type="button" onClick={() => setShowCreateForm(false)}
              style={{ padding: '8px 14px', background: '#e2e8f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              {['Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login', 'Actions'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.user_id} style={{ borderBottom: '1px solid #f1f5f9', opacity: u.is_active ? 1 : 0.6 }}>
                <td style={{ padding: '9px 12px', fontWeight: 600 }}>{u.username}</td>
                <td style={{ padding: '9px 12px' }}>{u.full_name}</td>
                <td style={{ padding: '9px 12px', color: '#64748b' }}>{u.email}</td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{
                    background: `${roleColor[u.role]}20`, color: roleColor[u.role],
                    padding: '2px 7px', borderRadius: 3, fontSize: 11, fontWeight: 600,
                  }}>
                    {u.role}
                  </span>
                </td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{ color: u.is_active ? '#16a34a' : '#dc2626', fontWeight: 600, fontSize: 11 }}>
                    {u.is_active ? 'ACTIVE' : 'DISABLED'}
                  </span>
                  {u.failed_login_count >= 5 && (
                    <span style={{ marginLeft: 6, color: '#d97706', fontSize: 10 }}>LOCKED</span>
                  )}
                </td>
                <td style={{ padding: '9px 12px', color: '#64748b', fontSize: 12 }}>
                  {u.last_login_at ? format(new Date(u.last_login_at), 'yyyy-MM-dd HH:mm') : '—'}
                </td>
                <td style={{ padding: '9px 12px', display: 'flex', gap: 6 }}>
                  <button onClick={() => handleToggleActive(u)}
                    style={{
                      padding: '3px 8px', border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: 11,
                      background: u.is_active ? '#fee2e2' : '#dcfce7',
                      color: u.is_active ? '#dc2626' : '#16a34a',
                    }}>
                    {u.is_active ? 'Disable' : 'Enable'}
                  </button>
                  {u.failed_login_count >= 5 && (
                    <button onClick={() => handleUnlock(u)}
                      style={{ padding: '3px 8px', background: '#fef3c7', color: '#d97706', border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: 11 }}>
                      Unlock
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
