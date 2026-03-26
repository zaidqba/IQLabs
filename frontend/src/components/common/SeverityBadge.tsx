import React from 'react';
import { SeverityLevel, SEVERITY_COLORS, SEVERITY_BG } from '../../types/common';

interface Props {
  severity: SeverityLevel;
  pulse?: boolean;
}

export const SeverityBadge: React.FC<Props> = ({ severity, pulse = false }) => {
  const color = SEVERITY_COLORS[severity];
  const bg = SEVERITY_BG[severity];

  return (
    <span
      style={{
        backgroundColor: bg,
        color,
        border: `1px solid ${color}`,
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        animation: pulse && severity !== 'NORMAL' ? 'pulse 1.5s infinite' : 'none',
      }}
    >
      {severity === 'HIGH_DOSE' && '⚠ '}
      {severity}
    </span>
  );
};
