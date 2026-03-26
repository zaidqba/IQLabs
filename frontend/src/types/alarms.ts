import { AlarmState, SeverityLevel } from './common';

export interface Alarm {
  alarm_id: number;
  channel_id: number;
  channel_code: string;
  channel_name: string;
  alarm_type: string;
  severity_level: SeverityLevel;
  triggered_at_utc: string;
  trigger_value?: string;
  alarm_state: AlarmState;
  alarm_message?: string;
  requires_signature: boolean;
  acknowledged_at_utc?: string;
  acknowledged_by_username?: string;
  ack_comment?: string;
}

export interface AcknowledgeRequest {
  comment: string;
  signature_password: string;
  meaning: string;
}
