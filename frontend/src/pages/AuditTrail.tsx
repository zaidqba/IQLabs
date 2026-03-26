/**
 * Audit Trail page — immutable record of all user and system actions.
 * Read-only. Supports filtering by user, action type, and date range.
 * Satisfies 21 CFR Part 11 §11.10(e) audit trail requirements.
 */
import React, { useEffect, useState, useCallback } from 'react';
import api from '../services/api';
import { format } from 'date-fns';

interface AuditEntry {
  audit_id: number;
  timestamp_utc: string;
  user_id: number | null;
  username: string | null;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  http_method: string | null;
  endpoint: string | null;
  response_status: number | null;
  change_summary: string | null;
}

const ACTION_COLORS: Record<string, string> = {
  LOGIN: '#3b82f6',
  LOGOUT: '#6b7280',
  CREATE: '#16a34a',
  UPDATE: '#d97706',
  DELETE: '#dc2626',
  SIGN: '#7c3aed',
  EXPORT: '#0891b2',
  READ: '#9ca3af',
};

export const AuditTrail: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [filters, setFilters] = useState({
    username: '',
    action_type: '',
    resource_type: '',
    start: '',
    end: '',
  });

  const PAGE_SIZE = 100;

  const fetchAudit = useCallback(async (p = 1, reset = false) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: PAGE_SIZE, offset: (p - 1) * PAGE_SIZE };
      if (filters.username) params.username = filters.username;
      if (filters.action_type) params.action_type = filters.action_type;
      if (filters.resource_type) params.resource_type = filters.resource_type;
      if (filters.start) params.start = filters.start;
      if (filters.end) params.end = filters.end;

      const resp = await api.get<AuditEntry[]>('/audit', { params });
      const data = resp.data;
      setHasMore(data.length === PAGE_SIZE);
      setEntries(prev => reset ? data : [...prev, ...data]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { setPage(1); fetchAudit(1, true); }, [filters]);

  const handleLoadMore = () => {
    const next = page + 1;
    setPage(next);
    fetchAudit(next);
  };

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, color: '#1e293b' }}>Audit Trail</h1>

      <div style={{
        background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6,
        padding: '8px 14px', marginBottom: 16, fontSize: 12, color: '#92400e',
      }}>
        Audit trail is immutable — records cannot be modified or deleted (21 CFR Part 11 §11.10(e))
      </div>

      {/* Filters */}
      <div style={{
        background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0',
        padding: '14px 16px', marginBottom: 16, display: 'flex', gap: 10, flexWrap: 'wrap',
      }}>
        {[
          { key: 'username', placeholder: 'Username' },
          { key: 'action_type', placeholder: 'Action Type' },
          { key: 'resource_type', placeholder: 'Resource Type' },
        ].map(f => (
          <input
            key={f.key}
            placeholder={f.placeholder}
            value={(filters as any)[f.key]}
            onChange={e => setFilters(prev => ({ ...prev, [f.key]: e.target.value }))}
            style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 12, width: 150 }}
          />
        ))}
        <input type="datetime-local" value={filters.start}
          onChange={e => setFilters(prev => ({ ...prev, start: e.target.value }))}
          style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 12 }} />
        <input type="datetime-local" value={filters.end}
          onChange={e => setFilters(prev => ({ ...prev, end: e.target.value }))}
          style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 12 }} />
        <button
          onClick={() => setFilters({ username: '', action_type: '', resource_type: '', start: '', end: '' })}
          style={{ padding: '6px 12px', background: '#e2e8f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
        >
          Clear
        </button>
      </div>

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              {['Timestamp (UTC)', 'User', 'Action', 'Resource', 'Endpoint', 'Status', 'Summary'].map(h => (
                <th key={h} style={{ padding: '9px 10px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 11 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map(e => (
              <tr key={e.audit_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 11 }}>
                  {format(new Date(e.timestamp_utc), 'yyyy-MM-dd HH:mm:ss')}
                </td>
                <td style={{ padding: '7px 10px' }}>{e.username || '—'}</td>
                <td style={{ padding: '7px 10px' }}>
                  <span style={{
                    color: ACTION_COLORS[e.action_type] || '#64748b',
                    fontWeight: 600, fontSize: 10,
                    background: `${ACTION_COLORS[e.action_type]}18`,
                    padding: '2px 5px', borderRadius: 2,
                  }}>
                    {e.action_type}
                  </span>
                </td>
                <td style={{ padding: '7px 10px', color: '#374151' }}>{e.resource_type}</td>
                <td style={{ padding: '7px 10px', color: '#64748b', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.http_method && `${e.http_method} `}{e.endpoint}
                </td>
                <td style={{ padding: '7px 10px' }}>
                  <span style={{
                    color: e.response_status && e.response_status < 400 ? '#16a34a' : '#dc2626',
                    fontWeight: 600,
                  }}>
                    {e.response_status}
                  </span>
                </td>
                <td style={{ padding: '7px 10px', color: '#64748b', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.change_summary}
                </td>
              </tr>
            ))}
            {loading && (
              <tr><td colSpan={7} style={{ padding: 16, textAlign: 'center', color: '#9ca3af' }}>Loading…</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {hasMore && !loading && (
        <div style={{ textAlign: 'center', marginTop: 12 }}>
          <button
            onClick={handleLoadMore}
            style={{ padding: '8px 20px', background: '#e2e8f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
};
