-- ============================================================================
-- IQ-RAD: Runtime Data Tables
-- Schema Version: 1.0
-- Regulatory: 21 CFR Part 11 §11.10(e) — data immutability
--             10 CFR Part 20 Subpart L — radiation records
-- Description: Operational data. raw_ingestion_log, normalized_readings,
--              alarm_history, and heartbeat_log are IMMUTABLE (append-only).
--              Immutability enforced by DDL triggers in 06_triggers.sql.
-- ============================================================================

USE IQ_RAD;
GO

-- ─── Raw Ingestion Log ────────────────────────────────────────────────────────
-- IMMUTABLE. Exact bytes received from every device connection.
-- This is the legal record. Nothing is ever changed or deleted here.
CREATE TABLE raw_ingestion_log (
    ingestion_id        BIGINT IDENTITY(1,1)    NOT NULL,
    device_id           INT                     NOT NULL,
    received_at_utc     DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    source_ip           NVARCHAR(45)            NULL,
    source_port         INT                     NULL,
    session_id          NVARCHAR(36)            NULL,       -- TCP session UUID
    raw_payload         VARBINARY(MAX)          NOT NULL,   -- Exact bytes received
    payload_length      INT                     NOT NULL,
    parse_status        NVARCHAR(20)            NOT NULL DEFAULT 'PENDING',
    -- PENDING | PARSED | PARTIAL | FAILED
    parse_error         NVARCHAR(MAX)           NULL,
    packet_sequence     BIGINT                  NULL,       -- Connector sequence counter
    CONSTRAINT PK_raw_ingestion PRIMARY KEY (ingestion_id),
    CONSTRAINT FK_raw_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT CHK_raw_parse_status CHECK (
        parse_status IN ('PENDING', 'PARSED', 'PARTIAL', 'FAILED')
    )
);
GO

-- ─── Normalized Readings ──────────────────────────────────────────────────────
-- IMMUTABLE. Every normalized value with full traceability to source.
-- DO NOT UPDATE. Corrections create new rows with quality_flag = 'CORRECTED'.
CREATE TABLE normalized_readings (
    reading_id          BIGINT IDENTITY(1,1)    NOT NULL,
    ingestion_id        BIGINT                  NOT NULL,   -- Always traceable to raw
    channel_id          INT                     NOT NULL,
    measured_at_utc     DATETIME2(7)            NOT NULL,   -- Device-reported time
    received_at_utc     DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    raw_value           DECIMAL(18,6)           NOT NULL,   -- Value as parsed from device
    normalized_value    DECIMAL(18,6)           NOT NULL,   -- After unit conversion / correction factor
    uom_id              INT                     NOT NULL,
    quality_flag        NVARCHAR(20)            NOT NULL DEFAULT 'GOOD',
    -- GOOD | SUSPECT | BAD | SIMULATED | CORRECTED
    quality_detail      NVARCHAR(500)           NULL,
    alarm_profile_id    INT                     NULL,       -- Threshold set active at time of reading
    severity_level      NVARCHAR(20)            NOT NULL DEFAULT 'NORMAL',
    -- NORMAL | LOW | ALERT | ALARM | DANGER | HIGH_DOSE
    is_suppressed       BIT                     NOT NULL DEFAULT 0,
    ntp_offset_ms       INT                     NULL,       -- NTP drift at time of reading
    created_at          DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_normalized_readings PRIMARY KEY (reading_id),
    CONSTRAINT FK_readings_ingestion FOREIGN KEY (ingestion_id)
        REFERENCES raw_ingestion_log(ingestion_id),
    CONSTRAINT FK_readings_channel FOREIGN KEY (channel_id)
        REFERENCES channels(channel_id),
    CONSTRAINT FK_readings_uom FOREIGN KEY (uom_id)
        REFERENCES units_of_measure(uom_id),
    CONSTRAINT FK_readings_profile FOREIGN KEY (alarm_profile_id)
        REFERENCES alarm_profiles(profile_id),
    CONSTRAINT CHK_readings_quality CHECK (
        quality_flag IN ('GOOD', 'SUSPECT', 'BAD', 'SIMULATED', 'CORRECTED')
    ),
    CONSTRAINT CHK_readings_severity CHECK (
        severity_level IN ('NORMAL', 'LOW', 'ALERT', 'ALARM', 'DANGER', 'HIGH_DOSE')
    )
);
GO
-- Time-series query pattern: channel X from time A to B
CREATE CLUSTERED INDEX CIX_readings_channel_time
    ON normalized_readings (channel_id, measured_at_utc DESC);
GO

-- ─── Device Status ────────────────────────────────────────────────────────────
-- Append-only snapshots of device connectivity status
CREATE TABLE device_status (
    status_id       BIGINT IDENTITY(1,1)    NOT NULL,
    device_id       INT                     NOT NULL,
    status_at_utc   DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    status_code     NVARCHAR(20)            NOT NULL,
    -- ONLINE | OFFLINE | DEGRADED | FAULT | RECONNECTING
    status_detail   NVARCHAR(500)           NULL,
    tcp_latency_ms  INT                     NULL,
    retry_count     INT                     NULL,
    created_at      DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_device_status PRIMARY KEY (status_id),
    CONSTRAINT FK_dev_status_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT CHK_dev_status_code CHECK (
        status_code IN ('ONLINE', 'OFFLINE', 'DEGRADED', 'FAULT', 'RECONNECTING')
    )
);
GO

-- ─── Channel Status ───────────────────────────────────────────────────────────
-- Append-only snapshots of per-channel health
CREATE TABLE channel_status (
    cs_id           BIGINT IDENTITY(1,1)    NOT NULL,
    channel_id      INT                     NOT NULL,
    status_at_utc   DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    status_code     NVARCHAR(20)            NOT NULL,
    -- OK | NO_DATA | STALE | SATURATED | FAULT
    last_value      DECIMAL(18,6)           NULL,
    last_severity   NVARCHAR(20)            NULL,
    last_reading_id BIGINT                  NULL,
    created_at      DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_channel_status PRIMARY KEY (cs_id),
    CONSTRAINT FK_ch_status_channel FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    CONSTRAINT CHK_ch_status_code CHECK (
        status_code IN ('OK', 'NO_DATA', 'STALE', 'SATURATED', 'FAULT')
    )
);
GO

-- ─── Active Alarms ────────────────────────────────────────────────────────────
-- Current alarm state per channel. State transitions only via stored procedure.
-- All transitions are also written to alarm_history (immutable).
CREATE TABLE active_alarms (
    alarm_id                INT IDENTITY(1,1)   NOT NULL,
    channel_id              INT                 NOT NULL,
    alarm_type              NVARCHAR(20)        NOT NULL,
    -- LOW | ALERT | ALARM | DANGER | HIGH_DOSE | SYSTEM | STALE | COMM_FAIL
    severity_level          NVARCHAR(20)        NOT NULL,
    triggered_at_utc        DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    trigger_value           DECIMAL(18,6)       NULL,
    trigger_reading_id      BIGINT              NULL,
    alarm_state             NVARCHAR(20)        NOT NULL DEFAULT 'ACTIVE',
    -- ACTIVE | ACKNOWLEDGED | SUPPRESSED | CLEARED
    alarm_message           NVARCHAR(500)       NULL,
    requires_signature      BIT                 NOT NULL DEFAULT 0,
    acknowledged_at_utc     DATETIME2(7)        NULL,
    acknowledged_by         INT                 NULL,
    ack_comment             NVARCHAR(1000)      NULL,
    ack_signature_id        INT                 NULL,
    cleared_at_utc          DATETIME2(7)        NULL,
    escalated_at_utc        DATETIME2(7)        NULL,
    CONSTRAINT PK_active_alarms PRIMARY KEY (alarm_id),
    CONSTRAINT FK_alarm_channel FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    CONSTRAINT FK_alarm_reading FOREIGN KEY (trigger_reading_id)
        REFERENCES normalized_readings(reading_id),
    CONSTRAINT FK_alarm_ack_user FOREIGN KEY (acknowledged_by) REFERENCES users(user_id),
    CONSTRAINT CHK_alarm_type CHECK (
        alarm_type IN ('LOW', 'ALERT', 'ALARM', 'DANGER', 'HIGH_DOSE', 'SYSTEM', 'STALE', 'COMM_FAIL')
    ),
    CONSTRAINT CHK_alarm_state CHECK (
        alarm_state IN ('ACTIVE', 'ACKNOWLEDGED', 'SUPPRESSED', 'CLEARED')
    )
);
GO

-- ─── Alarm History ────────────────────────────────────────────────────────────
-- IMMUTABLE. Every alarm state transition recorded here permanently.
CREATE TABLE alarm_history (
    history_id          BIGINT IDENTITY(1,1)    NOT NULL,
    alarm_id            INT                     NOT NULL,
    channel_id          INT                     NOT NULL,
    event_type          NVARCHAR(30)            NOT NULL,
    -- TRIGGERED | ACKNOWLEDGED | CLEARED | SUPPRESSED | ESCALATED | AUTO_CLEARED
    event_at_utc        DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    previous_state      NVARCHAR(20)            NULL,
    new_state           NVARCHAR(20)            NOT NULL,
    actor_user_id       INT                     NULL,
    actor_username      NVARCHAR(50)            NULL,   -- Denormalized for audit integrity
    comment             NVARCHAR(1000)          NULL,
    reading_value       DECIMAL(18,6)           NULL,
    severity_level      NVARCHAR(20)            NULL,
    signature_id        INT                     NULL,
    created_at          DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_alarm_history PRIMARY KEY (history_id),
    CONSTRAINT FK_hist_alarm FOREIGN KEY (alarm_id) REFERENCES active_alarms(alarm_id)
);
GO

-- ─── Heartbeat Log ────────────────────────────────────────────────────────────
-- Device connectivity heartbeats with NTP offset tracking
CREATE TABLE heartbeat_log (
    heartbeat_id    BIGINT IDENTITY(1,1)    NOT NULL,
    device_id       INT                     NOT NULL,
    beat_at_utc     DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    latency_ms      INT                     NULL,
    ntp_offset_ms   INT                     NULL,       -- System clock vs NTP delta
    is_ntp_valid    BIT                     NOT NULL DEFAULT 1,
    sequence_num    BIGINT                  NULL,
    session_id      NVARCHAR(36)            NULL,
    created_at      DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_heartbeat PRIMARY KEY (heartbeat_id),
    CONSTRAINT FK_heartbeat_device FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
GO
