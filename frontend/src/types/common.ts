export type SeverityLevel = 'NORMAL' | 'LOW' | 'ALERT' | 'ALARM' | 'DANGER' | 'HIGH_DOSE';
export type QualityFlag = 'GOOD' | 'SUSPECT' | 'BAD' | 'SIMULATED' | 'CORRECTED';
export type AlarmState = 'ACTIVE' | 'ACKNOWLEDGED' | 'SUPPRESSED' | 'CLEARED';
export type UserRole = 'ADMIN' | 'OPERATOR' | 'VIEWER' | 'EMISSIONS' | 'DEVELOPER';

export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  NORMAL: '#22c55e',
  LOW: '#3b82f6',
  ALERT: '#eab308',
  ALARM: '#f97316',
  DANGER: '#ef4444',
  HIGH_DOSE: '#a855f7',
};

export const SEVERITY_BG: Record<SeverityLevel, string> = {
  NORMAL: '#dcfce7',
  LOW: '#dbeafe',
  ALERT: '#fef9c3',
  ALARM: '#ffedd5',
  DANGER: '#fee2e2',
  HIGH_DOSE: '#f3e8ff',
};
