/**
 * Status Bar — persistent indicator of NTP sync, active alarms, user info.
 * Visible on all pages. NTP status is a GMP critical indicator.
 */
import React from 'react';
import { useReadingsStore } from '../../store/readingsStore';
import { useAlarmStore } from '../../store/alarmStore';
import { useAuthStore } from '../../store/authStore';

export const StatusBar: React.FC = () => {
  const { ntpValid, ntpOffsetMs } = useReadingsStore();
  const { activeAlarms } = useAlarmStore();
  const { user } = useAuthStore();

  const unackedCount = activeAlarms.filter((a) => a.alarm_state === 'ACTIVE').length;

  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, height: 32,
      background: '#1e293b', color: '#e2e8f0', display: 'flex',
      alignItems: 'center', padding: '0 16px', gap: 16, fontSize: 12,
      zIndex: 100, borderTop: '1px solid #334155',
    }}>
      {/* NTP Status */}
      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: ntpValid ? '#22c55e' : '#ef4444',
            display: 'inline-block',
          }}
        />
        NTP: {ntpValid ? `Synced (${ntpOffsetMs ?? '?'}ms)` : `DRIFT DETECTED (${ntpOffsetMs}ms)`}
      </span>

      <span style={{ color: '#475569' }}>|</span>

      {/* Active Alarms */}
      {unackedCount > 0 ? (
        <span style={{ color: '#f97316', fontWeight: 600 }}>
          ⚠ {unackedCount} ACTIVE ALARM{unackedCount !== 1 ? 'S' : ''} UNACKNOWLEDGED
        </span>
      ) : (
        <span style={{ color: '#22c55e' }}>No active alarms</span>
      )}

      <span style={{ marginLeft: 'auto' }}>
        IQ-RAD v1.0.0 | {user?.username} ({user?.role})
      </span>
    </div>
  );
};
