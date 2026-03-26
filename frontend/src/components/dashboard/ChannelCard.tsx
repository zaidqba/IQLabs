/**
 * Channel Card — live radiation measurement display.
 * Shows current value, severity color band, UOM, channel name, and stale indicator.
 * Updated in real-time via WebSocket.
 */
import React from 'react';
import { LatestReading } from '../../types/readings';
import { SEVERITY_COLORS, SEVERITY_BG } from '../../types/common';
import { SeverityBadge } from '../common/SeverityBadge';

interface Props {
  reading: LatestReading;
}

export const ChannelCard: React.FC<Props> = ({ reading }) => {
  const borderColor = SEVERITY_COLORS[reading.severity_level];
  const bgColor = reading.severity_level !== 'NORMAL' ? SEVERITY_BG[reading.severity_level] : '#ffffff';
  const isHighSeverity = ['DANGER', 'HIGH_DOSE'].includes(reading.severity_level);

  const lastUpdate = reading.measured_at_utc
    ? new Date(reading.measured_at_utc).toLocaleTimeString()
    : 'No data';

  return (
    <div style={{
      border: `2px solid ${borderColor}`,
      borderRadius: 8,
      padding: 16,
      background: bgColor,
      animation: isHighSeverity ? 'pulse-border 1s infinite' : 'none',
      minWidth: 180,
      position: 'relative',
    }}>
      {reading.is_stale && (
        <div style={{
          position: 'absolute', top: 4, right: 4,
          background: '#fef3c7', color: '#92400e',
          fontSize: 10, padding: '1px 4px', borderRadius: 2,
        }}>
          STALE
        </div>
      )}

      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>
        {reading.channel_code}
      </div>

      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
        {reading.channel_name}
      </div>

      <div style={{ fontSize: 32, fontWeight: 700, color: borderColor, lineHeight: 1 }}>
        {reading.normalized_value
          ? parseFloat(reading.normalized_value).toFixed(2)
          : '---'}
      </div>
      <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
        {reading.uom_symbol}
      </div>

      <div style={{ marginTop: 8 }}>
        <SeverityBadge severity={reading.severity_level} pulse={isHighSeverity} />
      </div>

      {reading.alarm_threshold && (
        <div style={{ marginTop: 8, fontSize: 11, color: '#9ca3af' }}>
          Alarm: {reading.alarm_threshold} | Danger: {reading.danger_threshold}
        </div>
      )}

      <div style={{ marginTop: 4, fontSize: 10, color: '#9ca3af' }}>
        {lastUpdate}
      </div>
    </div>
  );
};
