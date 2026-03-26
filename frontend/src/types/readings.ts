import { QualityFlag, SeverityLevel } from './common';

export interface Reading {
  reading_id: number;
  ingestion_id: number;
  channel_id: number;
  channel_code: string;
  channel_name: string;
  measured_at_utc: string;
  received_at_utc: string;
  normalized_value: string;
  uom_symbol: string;
  quality_flag: QualityFlag;
  severity_level: SeverityLevel;
  ntp_offset_ms?: number;
}

export interface LatestReading {
  channel_id: number;
  channel_code: string;
  channel_name: string;
  normalized_value?: string;
  uom_symbol: string;
  severity_level: SeverityLevel;
  quality_flag: QualityFlag;
  measured_at_utc?: string;
  is_stale: boolean;
  alarm_profile_id?: number;
  alert_threshold?: string;
  alarm_threshold?: string;
  danger_threshold?: string;
}
