import React from 'react';
import { useAlarmStore } from '../../store/alarmStore';
import { SEVERITY_COLORS } from '../../types/common';

export const AlarmBanner: React.FC = () => {
  const { activeAlarms } = useAlarmStore();
  const active = activeAlarms.filter((a) => a.alarm_state === 'ACTIVE');
  if (active.length === 0) return null;

  return (
    <div style={{
      background: '#7f1d1d', color: '#fecaca',
      padding: '8px 16px', borderRadius: 4, marginBottom: 16,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <span style={{ fontSize: 18 }}>⚠</span>
      <strong>{active.length} ACTIVE ALARM{active.length !== 1 ? 'S' : ''}</strong>
      <span style={{ marginLeft: 8 }}>
        {active.slice(0, 3).map((a) => (
          <span key={a.alarm_id} style={{
            background: SEVERITY_COLORS[a.severity_level],
            color: '#fff', padding: '2px 6px', borderRadius: 3,
            marginRight: 4, fontSize: 12,
          }}>
            {a.channel_code}: {a.severity_level}
          </span>
        ))}
        {active.length > 3 && <span>+{active.length - 3} more</span>}
      </span>
      <a href="/alarms" style={{ marginLeft: 'auto', color: '#fca5a5', fontSize: 12 }}>
        View all →
      </a>
    </div>
  );
};
