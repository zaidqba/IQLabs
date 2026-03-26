/**
 * Alarm Console — active and historical alarms with acknowledgement workflow.
 * DANGER/HIGH_DOSE acknowledgement requires electronic signature (21 CFR Part 11).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Alarm } from '../types/alarms';
import { useAlarmStore } from '../store/alarmStore';
import { SEVERITY_COLORS } from '../types/common';
import { AcknowledgeForm } from '../components/alarms/AcknowledgeForm';
import api from '../services/api';
import { format } from 'date-fns';

type Tab = 'active' | 'history';

export const AlarmConsole: React.FC = () => {
  const { activeAlarms, setActiveAlarms } = useAlarmStore();
  const [tab, setTab] = useState<Tab>('active');
  const [history, setHistory] = useState<Alarm[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [ackTarget, setAckTarget] = useState<Alarm | null>(null);
  const [severityFilter, setSeverityFilter] = useState('ALL');

  const fetchActive = useCallback(async () => {
    const resp = await api.get<Alarm[]>('/alarms/active');
    setActiveAlarms(resp.data);
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const resp = await api.get<Alarm[]>('/alarms/history?limit=200');
      setHistory(resp.data);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => { fetchActive(); }, []);
  useEffect(() => { if (tab === 'history') fetchHistory(); }, [tab]);

  const displayed = (tab === 'active' ? activeAlarms : history).filter(a =>
    severityFilter === 'ALL' || a.severity_level === severityFilter
  );

  const severities = ['ALL', 'HIGH_DOSE', 'DANGER', 'ALARM', 'ALERT', 'LOW'];

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, color: '#1e293b' }}>Alarm Console</h1>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, borderBottom: '1px solid #e2e8f0' }}>
        {(['active', 'history'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 18px', border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: tab === t ? '2px solid #3b82f6' : '2px solid transparent',
              color: tab === t ? '#1e40af' : '#64748b', fontWeight: tab === t ? 600 : 400,
              fontSize: 14, textTransform: 'capitalize',
            }}
          >
            {t === 'active' ? `Active (${activeAlarms.filter(a => a.alarm_state === 'ACTIVE').length})` : 'History'}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <label style={{ fontSize: 12, color: '#64748b' }}>Severity:</label>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            style={{ fontSize: 12, padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 4 }}
          >
            {severities.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              {['Channel', 'Severity', 'Message', 'State', 'Triggered', 'Actions'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loadingHistory && (
              <tr><td colSpan={6} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>Loading…</td></tr>
            )}
            {!loadingHistory && displayed.length === 0 && (
              <tr><td colSpan={6} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>No alarms</td></tr>
            )}
            {displayed.map(alarm => (
              <tr key={alarm.alarm_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '9px 12px', fontWeight: 600 }}>{alarm.channel_code}</td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{
                    background: SEVERITY_COLORS[alarm.severity_level],
                    color: '#fff', padding: '2px 7px', borderRadius: 3, fontSize: 11, fontWeight: 600,
                  }}>
                    {alarm.severity_level}
                  </span>
                </td>
                <td style={{ padding: '9px 12px', color: '#374151', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {alarm.alarm_message}
                </td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{
                    color: alarm.alarm_state === 'ACTIVE' ? '#dc2626' : alarm.alarm_state === 'ACKNOWLEDGED' ? '#d97706' : '#16a34a',
                    fontWeight: 600, fontSize: 11,
                  }}>
                    {alarm.alarm_state}
                  </span>
                </td>
                <td style={{ padding: '9px 12px', color: '#64748b', fontSize: 12 }}>
                  {format(new Date(alarm.triggered_at), 'yyyy-MM-dd HH:mm:ss')}
                </td>
                <td style={{ padding: '9px 12px' }}>
                  {alarm.alarm_state === 'ACTIVE' && (
                    <button
                      onClick={() => setAckTarget(alarm)}
                      style={{
                        padding: '4px 10px', background: '#1e40af', color: '#fff',
                        border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: 11,
                      }}
                    >
                      Acknowledge
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {ackTarget && (
        <AcknowledgeForm
          alarm={ackTarget}
          onClose={() => setAckTarget(null)}
          onAcknowledged={() => { setAckTarget(null); fetchActive(); }}
        />
      )}
    </div>
  );
};
