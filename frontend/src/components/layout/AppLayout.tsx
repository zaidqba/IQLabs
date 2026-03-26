/**
 * Application shell: side navigation + top header + content area + status bar.
 */
import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { StatusBar } from './StatusBar';
import api from '../../services/api';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: '◉' },
  { path: '/trends', label: 'Trends', icon: '📈' },
  { path: '/alarms', label: 'Alarms', icon: '🔔' },
  { path: '/reports', label: 'Reports', icon: '📄' },
  { path: '/audit', label: 'Audit Trail', icon: '🔍' },
  { path: '/calibration', label: 'Calibration', icon: '⚖' },
  { path: '/users', label: 'Users', icon: '👥' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
];

const ROLE_NAV: Record<string, string[]> = {
  VIEWER: ['/', '/trends', '/alarms'],
  EMISSIONS: ['/', '/trends', '/alarms', '/calibration'],
  OPERATOR: ['/', '/trends', '/alarms', '/reports', '/audit', '/calibration', '/settings'],
  ADMIN: ['/', '/trends', '/alarms', '/reports', '/audit', '/calibration', '/users', '/settings'],
  DEVELOPER: ['/', '/trends', '/alarms', '/reports', '/audit', '/calibration', '/users', '/settings'],
};

interface Props { children: React.ReactNode; }

export const AppLayout: React.FC<Props> = ({ children }) => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const allowed = ROLE_NAV[user?.role || 'VIEWER'] || ['/'];

  const handleLogout = async () => {
    try { await api.post('/auth/logout'); } catch {}
    logout();
    navigate('/login');
  };

  const navW = collapsed ? 52 : 200;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f1f5f9' }}>
      {/* Sidebar */}
      <div style={{
        width: navW, minHeight: '100vh', background: '#1e293b',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        transition: 'width 0.2s',
      }}>
        {/* Logo */}
        <div style={{ padding: '16px 12px', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>☢</span>
          {!collapsed && <span style={{ color: '#f8fafc', fontWeight: 700, fontSize: 15 }}>IQ-RAD</span>}
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 16 }}
          >
            {collapsed ? '›' : '‹'}
          </button>
        </div>

        {/* Nav links */}
        <nav style={{ flex: 1, padding: '8px 0' }}>
          {NAV_ITEMS.filter(item => allowed.includes(item.path)).map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 14px', textDecoration: 'none',
                color: isActive ? '#f8fafc' : '#94a3b8',
                background: isActive ? '#0f172a' : 'transparent',
                borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
                fontSize: 13, fontWeight: isActive ? 600 : 400,
              })}
            >
              <span style={{ fontSize: 15, flexShrink: 0 }}>{item.icon}</span>
              {!collapsed && item.label}
            </NavLink>
          ))}
        </nav>

        {/* User / logout */}
        <div style={{ padding: '12px', borderTop: '1px solid #334155' }}>
          {!collapsed && (
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
              {user?.username} · {user?.role}
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              width: '100%', padding: '7px 10px', background: '#dc2626', color: '#fff',
              border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12,
            }}
          >
            {collapsed ? '↩' : 'Sign Out'}
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <main style={{ flex: 1, padding: '20px 24px', paddingBottom: 48 }}>
          {children}
        </main>
        <StatusBar />
      </div>
    </div>
  );
};
