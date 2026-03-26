-- ============================================================================
-- IQ-RAD: Performance Indexes
-- Schema Version: 1.0
-- Description: Additional indexes for common query patterns.
--              The clustered index on normalized_readings is in 02_runtime_tables.sql.
-- ============================================================================

USE IQ_RAD;
GO

-- ─── raw_ingestion_log ────────────────────────────────────────────────────────
CREATE INDEX IX_raw_device_time ON raw_ingestion_log (device_id, received_at_utc DESC);
CREATE INDEX IX_raw_parse_status ON raw_ingestion_log (parse_status) WHERE parse_status = 'PENDING';
GO

-- ─── normalized_readings ──────────────────────────────────────────────────────
-- Composite for dashboard "latest per channel" query
CREATE INDEX IX_readings_severity ON normalized_readings (severity_level, channel_id, measured_at_utc DESC)
    WHERE severity_level <> 'NORMAL';
CREATE INDEX IX_readings_quality ON normalized_readings (quality_flag, channel_id)
    WHERE quality_flag <> 'GOOD';
GO

-- ─── device_status ────────────────────────────────────────────────────────────
CREATE INDEX IX_devstatus_device_time ON device_status (device_id, status_at_utc DESC);
GO

-- ─── channel_status ───────────────────────────────────────────────────────────
CREATE INDEX IX_chstatus_channel_time ON channel_status (channel_id, status_at_utc DESC);
GO

-- ─── active_alarms ────────────────────────────────────────────────────────────
CREATE INDEX IX_alarms_state ON active_alarms (alarm_state, channel_id)
    WHERE alarm_state IN ('ACTIVE', 'ACKNOWLEDGED');
CREATE INDEX IX_alarms_channel ON active_alarms (channel_id, triggered_at_utc DESC);
GO

-- ─── alarm_history ────────────────────────────────────────────────────────────
CREATE INDEX IX_hist_alarm ON alarm_history (alarm_id, event_at_utc DESC);
CREATE INDEX IX_hist_channel_time ON alarm_history (channel_id, event_at_utc DESC);
GO

-- ─── heartbeat_log ────────────────────────────────────────────────────────────
CREATE INDEX IX_heartbeat_device_time ON heartbeat_log (device_id, beat_at_utc DESC);
GO

-- ─── audit_trail ──────────────────────────────────────────────────────────────
-- Already has indexes from 03_compliance_tables.sql
-- Additional composite for user action history
CREATE INDEX IX_audit_action_resource ON audit_trail (action_type, resource_type, event_at_utc DESC);
GO

-- ─── calibration_records ──────────────────────────────────────────────────────
CREATE INDEX IX_cal_detector ON calibration_records (detector_id, calibration_date DESC);
CREATE INDEX IX_cal_due_date ON calibration_records (next_due_date) WHERE pass_fail = 'PASS';
GO

-- ─── review_records ───────────────────────────────────────────────────────────
CREATE INDEX IX_review_state ON review_records (review_state, review_period_start DESC)
    WHERE review_state <> 'APPROVED';
GO

-- ─── token_blacklist ──────────────────────────────────────────────────────────
CREATE INDEX IX_token_blacklist_session ON token_blacklist (session_id);
CREATE INDEX IX_token_blacklist_expires ON token_blacklist (expires_at);
GO
