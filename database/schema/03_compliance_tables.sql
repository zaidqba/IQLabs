-- ============================================================================
-- IQ-RAD: Compliance & Quality Tables
-- Schema Version: 1.0
-- Regulatory: 21 CFR Part 11 §11.10(b)(c)(d)(e) — audit trail, access,
--             operational system checks, authority/responsibility control
--             21 CFR Part 212.60 — GMP records
--             10 CFR Part 20.2102 — record retention
-- Description: audit_trail is IMMUTABLE. All other tables are append-only
--              by design (corrections create new records, not updates).
-- ============================================================================

USE IQ_RAD;
GO

-- ─── Audit Trail ─────────────────────────────────────────────────────────────
-- IMMUTABLE. Every system action logged here.
-- Satisfies 21 CFR Part 11 §11.10(e) — computer-generated, time-stamped audit trail
CREATE TABLE audit_trail (
    audit_id            BIGINT IDENTITY(1,1)    NOT NULL,
    event_at_utc        DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    user_id             INT                     NULL,       -- NULL for system/anonymous actions
    user_name           NVARCHAR(100)           NULL,       -- Denormalized (immutable snapshot)
    user_role           NVARCHAR(50)            NULL,       -- Denormalized
    session_id          NVARCHAR(36)            NULL,
    ip_address          NVARCHAR(45)            NULL,
    http_method         NVARCHAR(10)            NULL,       -- GET, POST, PATCH, DELETE
    endpoint            NVARCHAR(500)           NULL,       -- Normalized path
    action_type         NVARCHAR(50)            NOT NULL,
    -- LOGIN | LOGOUT | READ | CREATE | UPDATE | DELETE | APPROVE | SIGN | EXPORT | CONFIG_CHANGE
    -- ACK_ALARM | THRESHOLD_CHANGE | CALIBRATION | REVIEW | REPORT_GENERATE | REPORT_APPROVE
    resource_type       NVARCHAR(50)            NULL,       -- 'alarm', 'threshold', 'reading', 'report'
    resource_id         NVARCHAR(100)           NULL,       -- ID of affected resource
    action_detail       NVARCHAR(MAX)           NULL,       -- JSON: {before: {...}, after: {...}}
    result_code         INT                     NULL,       -- HTTP status code
    result_status       NVARCHAR(20)            NULL,       -- SUCCESS | FAILURE | DENIED
    failure_reason      NVARCHAR(500)           NULL,
    duration_ms         INT                     NULL,
    request_id          NVARCHAR(36)            NOT NULL,   -- X-Request-ID (correlation)
    CONSTRAINT PK_audit_trail PRIMARY KEY (audit_id)
);
GO
CREATE INDEX IX_audit_event_time ON audit_trail (event_at_utc DESC);
CREATE INDEX IX_audit_user ON audit_trail (user_id, event_at_utc DESC);
CREATE INDEX IX_audit_resource ON audit_trail (resource_type, resource_id);
GO

-- ─── Electronic Signatures ───────────────────────────────────────────────────
-- 21 CFR Part 11 §11.50 — Signature manifestations
-- §11.200(a)(1) — two distinct identification components (JWT session + password re-entry)
CREATE TABLE electronic_signatures (
    signature_id            INT IDENTITY(1,1)   NOT NULL,
    user_id                 INT                 NOT NULL,
    user_name               NVARCHAR(100)       NOT NULL,   -- Denormalized
    user_role               NVARCHAR(50)        NOT NULL,   -- Denormalized
    signed_at_utc           DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    meaning                 NVARCHAR(500)       NOT NULL,   -- e.g. "I approve this threshold change"
    signed_item_type        NVARCHAR(50)        NOT NULL,   -- 'THRESHOLD_CHANGE', 'ALARM_ACK', 'REPORT_APPROVAL'
    signed_item_id          NVARCHAR(100)       NOT NULL,
    authentication_method   NVARCHAR(20)        NOT NULL DEFAULT 'PASSWORD',
    -- PASSWORD | BIOMETRIC (future)
    ip_address              NVARCHAR(45)        NULL,
    session_id              NVARCHAR(36)        NULL,
    signature_hash          NVARCHAR(64)        NOT NULL,   -- SHA-256(user_id|item_type|item_id|timestamp|HMAC_SECRET)
    is_valid                BIT                 NOT NULL DEFAULT 1,
    revoked_at_utc          DATETIME2(7)        NULL,       -- If signature later invalidated
    revoke_reason           NVARCHAR(500)       NULL,
    created_at              DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_esignatures PRIMARY KEY (signature_id),
    CONSTRAINT FK_esig_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

-- ─── Config Versions ─────────────────────────────────────────────────────────
-- Every configuration change creates a new immutable version record.
-- Satisfies 21 CFR Part 11 — computer-generated audit entries for all operator changes
CREATE TABLE config_versions (
    version_id          INT IDENTITY(1,1)   NOT NULL,
    config_type         NVARCHAR(50)        NOT NULL,   -- 'ALARM_PROFILE', 'CHANNEL', 'DEVICE', 'SYSTEM', 'USER'
    config_key          NVARCHAR(100)       NOT NULL,   -- e.g. channel_id, device_id
    version_number      INT                 NOT NULL,
    config_snapshot     NVARCHAR(MAX)       NOT NULL,   -- Full JSON of config at this version
    change_summary      NVARCHAR(1000)      NOT NULL,   -- Human-readable description
    change_reason       NVARCHAR(500)       NOT NULL,
    changed_by          INT                 NOT NULL,
    changed_at_utc      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    approved_by         INT                 NULL,
    approval_at_utc     DATETIME2(7)        NULL,
    signature_id        INT                 NULL,
    is_current          BIT                 NOT NULL DEFAULT 1,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_config_versions PRIMARY KEY (version_id),
    CONSTRAINT UQ_config_key_version UNIQUE (config_type, config_key, version_number),
    CONSTRAINT FK_config_changed_by FOREIGN KEY (changed_by) REFERENCES users(user_id),
    CONSTRAINT FK_config_approved_by FOREIGN KEY (approved_by) REFERENCES users(user_id),
    CONSTRAINT FK_config_signature FOREIGN KEY (signature_id)
        REFERENCES electronic_signatures(signature_id)
);
GO

-- ─── Threshold Change Log ────────────────────────────────────────────────────
-- Dedicated log for alarm threshold changes (high-risk config action)
CREATE TABLE threshold_change_log (
    change_id               BIGINT IDENTITY(1,1)    NOT NULL,
    channel_id              INT                     NOT NULL,
    changed_at_utc          DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    old_profile_id          INT                     NULL,
    new_profile_id          INT                     NOT NULL,
    change_reason           NVARCHAR(500)           NOT NULL,
    risk_assessment         NVARCHAR(1000)          NULL,
    changed_by              INT                     NOT NULL,
    approved_by             INT                     NOT NULL,
    approval_signature_id   INT                     NOT NULL,
    created_at              DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_threshold_change PRIMARY KEY (change_id),
    CONSTRAINT FK_thresh_channel FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    CONSTRAINT FK_thresh_old_profile FOREIGN KEY (old_profile_id) REFERENCES alarm_profiles(profile_id),
    CONSTRAINT FK_thresh_new_profile FOREIGN KEY (new_profile_id) REFERENCES alarm_profiles(profile_id),
    CONSTRAINT FK_thresh_changed_by FOREIGN KEY (changed_by) REFERENCES users(user_id),
    CONSTRAINT FK_thresh_approved_by FOREIGN KEY (approved_by) REFERENCES users(user_id),
    CONSTRAINT FK_thresh_signature FOREIGN KEY (approval_signature_id)
        REFERENCES electronic_signatures(signature_id)
);
GO

-- ─── Calibration Records ──────────────────────────────────────────────────────
-- Detector calibration history (10 CFR Part 20 / NIST traceability)
CREATE TABLE calibration_records (
    cal_id                  INT IDENTITY(1,1)   NOT NULL,
    detector_id             INT                 NOT NULL,
    calibration_date        DATE                NOT NULL,
    next_due_date           DATE                NOT NULL,
    calibration_source      NVARCHAR(200)       NULL,       -- 'NIST traceable Cs-137'
    source_activity_bq      DECIMAL(18,4)       NULL,
    source_cert_number      NVARCHAR(100)       NULL,
    as_found_reading        DECIMAL(18,6)       NULL,
    as_left_reading         DECIMAL(18,6)       NULL,
    correction_factor       DECIMAL(10,6)       NOT NULL DEFAULT 1.0,
    pass_fail               NVARCHAR(15)        NOT NULL,   -- 'PASS', 'FAIL', 'CONDITIONAL'
    performed_by_name       NVARCHAR(100)       NOT NULL,   -- External or internal tech name
    performed_by_user_id    INT                 NULL,
    reviewed_by             INT                 NULL,
    review_signature_id     INT                 NULL,
    certificate_ref         NVARCHAR(100)       NULL,       -- Calibration certificate number
    notes                   NVARCHAR(MAX)       NULL,
    created_at              DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by              INT                 NOT NULL,
    CONSTRAINT PK_calibrations PRIMARY KEY (cal_id),
    CONSTRAINT FK_cal_detector FOREIGN KEY (detector_id) REFERENCES detectors(detector_id),
    CONSTRAINT FK_cal_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id),
    CONSTRAINT FK_cal_signature FOREIGN KEY (review_signature_id)
        REFERENCES electronic_signatures(signature_id),
    CONSTRAINT CHK_cal_pass_fail CHECK (pass_fail IN ('PASS', 'FAIL', 'CONDITIONAL'))
);
GO

-- ─── Maintenance Records ──────────────────────────────────────────────────────
CREATE TABLE maintenance_records (
    maint_id            INT IDENTITY(1,1)   NOT NULL,
    device_id           INT                 NOT NULL,
    detector_id         INT                 NULL,
    maintenance_date    DATE                NOT NULL,
    maintenance_type    NVARCHAR(50)        NOT NULL,   -- 'PREVENTIVE', 'CORRECTIVE', 'INSPECTION'
    description         NVARCHAR(MAX)       NOT NULL,
    performed_by_name   NVARCHAR(100)       NOT NULL,
    performed_by_user_id INT                NULL,
    reviewed_by         INT                 NULL,
    review_signature_id INT                 NULL,
    next_due_date       DATE                NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL,
    CONSTRAINT PK_maintenance PRIMARY KEY (maint_id),
    CONSTRAINT FK_maint_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT FK_maint_detector FOREIGN KEY (detector_id) REFERENCES detectors(detector_id),
    CONSTRAINT FK_maint_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
);
GO

-- ─── Review Records ───────────────────────────────────────────────────────────
-- GMP periodic data review workflow
-- States: PENDING_REVIEW → REVIEWED → APPROVED → SUPERSEDED
CREATE TABLE review_records (
    review_id               INT IDENTITY(1,1)   NOT NULL,
    review_type             NVARCHAR(50)        NOT NULL,
    -- 'DAILY_DATA', 'WEEKLY_SUMMARY', 'MONTHLY_REPORT', 'INCIDENT_REVIEW'
    review_period_start     DATE                NOT NULL,
    review_period_end       DATE                NOT NULL,
    site_id                 INT                 NOT NULL,
    review_state            NVARCHAR(30)        NOT NULL DEFAULT 'PENDING_REVIEW',
    -- PENDING_REVIEW | REVIEWED | APPROVED | SUPERSEDED
    reviewer_id             INT                 NULL,
    reviewed_at_utc         DATETIME2(7)        NULL,
    reviewer_comment        NVARCHAR(MAX)       NULL,
    reviewer_signature_id   INT                 NULL,
    approver_id             INT                 NULL,
    approved_at_utc         DATETIME2(7)        NULL,
    approver_comment        NVARCHAR(MAX)       NULL,
    approver_signature_id   INT                 NULL,
    data_completeness_pct   DECIMAL(5,2)        NULL,
    total_readings_expected INT                 NULL,
    total_readings_received INT                 NULL,
    anomaly_count           INT                 NOT NULL DEFAULT 0,
    alarm_count             INT                 NOT NULL DEFAULT 0,
    created_at              DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by              INT                 NOT NULL,
    CONSTRAINT PK_reviews PRIMARY KEY (review_id),
    CONSTRAINT FK_review_site FOREIGN KEY (site_id) REFERENCES sites(site_id),
    CONSTRAINT FK_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(user_id),
    CONSTRAINT FK_review_approver FOREIGN KEY (approver_id) REFERENCES users(user_id),
    CONSTRAINT FK_review_rev_sig FOREIGN KEY (reviewer_signature_id)
        REFERENCES electronic_signatures(signature_id),
    CONSTRAINT FK_review_app_sig FOREIGN KEY (approver_signature_id)
        REFERENCES electronic_signatures(signature_id),
    CONSTRAINT CHK_review_state CHECK (
        review_state IN ('PENDING_REVIEW', 'REVIEWED', 'APPROVED', 'SUPERSEDED')
    )
);
GO

-- ─── Report Archive ───────────────────────────────────────────────────────────
-- Signed, archived compliance reports (immutable once approved)
CREATE TABLE report_archive (
    report_id           INT IDENTITY(1,1)   NOT NULL,
    report_type         NVARCHAR(50)        NOT NULL,   -- 'DAILY', 'WEEKLY', 'MONTHLY', 'INCIDENT', 'CALIBRATION'
    report_title        NVARCHAR(200)       NOT NULL,
    period_start        DATE                NOT NULL,
    period_end          DATE                NOT NULL,
    site_id             INT                 NOT NULL,
    generated_at_utc    DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    generated_by        INT                 NOT NULL,
    report_state        NVARCHAR(20)        NOT NULL DEFAULT 'DRAFT',
    -- DRAFT | REVIEWED | APPROVED | ARCHIVED | SUPERSEDED
    file_path           NVARCHAR(500)       NULL,       -- Relative path to stored PDF
    file_hash_sha256    NVARCHAR(64)        NULL,       -- Integrity check
    approved_by         INT                 NULL,
    approved_at_utc     DATETIME2(7)        NULL,
    approval_signature_id INT               NULL,
    review_record_id    INT                 NULL,       -- Links to associated review
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_report_archive PRIMARY KEY (report_id),
    CONSTRAINT FK_report_site FOREIGN KEY (site_id) REFERENCES sites(site_id),
    CONSTRAINT FK_report_generated_by FOREIGN KEY (generated_by) REFERENCES users(user_id),
    CONSTRAINT FK_report_approved_by FOREIGN KEY (approved_by) REFERENCES users(user_id),
    CONSTRAINT FK_report_signature FOREIGN KEY (approval_signature_id)
        REFERENCES electronic_signatures(signature_id)
);
GO
