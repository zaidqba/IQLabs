-- ============================================================================
-- IQ-RAD: Master Tables
-- Schema Version: 1.0
-- Regulatory: 21 CFR Part 212, 21 CFR Part 11, 10 CFR Part 20
-- Description: Reference/configuration data. All changes versioned via
--              config_versions table (see 03_compliance_tables.sql).
-- ============================================================================

USE IQ_RAD;
GO

-- ─── Sites ───────────────────────────────────────────────────────────────────
CREATE TABLE sites (
    site_id         INT IDENTITY(1,1)   NOT NULL,
    site_code       NVARCHAR(20)        NOT NULL,   -- e.g. 'USA56'
    site_name       NVARCHAR(100)       NOT NULL,
    address         NVARCHAR(500)       NULL,
    nrc_license     NVARCHAR(50)        NULL,       -- NRC license number (10 CFR 20)
    timezone        NVARCHAR(50)        NOT NULL DEFAULT 'UTC',
    is_active       BIT                 NOT NULL DEFAULT 1,
    created_at      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by      INT                 NOT NULL,
    CONSTRAINT PK_sites PRIMARY KEY (site_id),
    CONSTRAINT UQ_sites_code UNIQUE (site_code)
);
GO

-- ─── Systems ──────────────────────────────────────────────────────────────────
-- Logical grouping of devices (e.g. STACK_MONITOR, AREA_MONITOR, PERSONNEL_MONITOR)
CREATE TABLE systems (
    system_id       INT IDENTITY(1,1)   NOT NULL,
    site_id         INT                 NOT NULL,
    system_code     NVARCHAR(30)        NOT NULL,
    system_name     NVARCHAR(100)       NOT NULL,
    system_type     NVARCHAR(50)        NOT NULL,   -- 'STACK', 'AREA', 'PERSONNEL'
    description     NVARCHAR(500)       NULL,
    is_active       BIT                 NOT NULL DEFAULT 1,
    created_at      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by      INT                 NOT NULL,
    CONSTRAINT PK_systems PRIMARY KEY (system_id),
    CONSTRAINT UQ_systems_code UNIQUE (system_code),
    CONSTRAINT FK_systems_site FOREIGN KEY (site_id) REFERENCES sites(site_id)
);
GO

-- ─── Vendors ──────────────────────────────────────────────────────────────────
CREATE TABLE vendors (
    vendor_id       INT IDENTITY(1,1)   NOT NULL,
    vendor_code     NVARCHAR(20)        NOT NULL,   -- 'ROTEM', 'COMECER', 'LUDLUM'
    vendor_name     NVARCHAR(100)       NOT NULL,
    support_contact NVARCHAR(200)       NULL,
    is_active       BIT                 NOT NULL DEFAULT 1,
    created_at      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_vendors PRIMARY KEY (vendor_id),
    CONSTRAINT UQ_vendors_code UNIQUE (vendor_code)
);
GO

-- ─── Devices ──────────────────────────────────────────────────────────────────
-- Physical hardware units (Rotem Stack, Rotem DPU3, future Comecer/Ludlum)
CREATE TABLE devices (
    device_id       INT IDENTITY(1,1)   NOT NULL,
    system_id       INT                 NOT NULL,
    vendor_id       INT                 NOT NULL,
    device_code     NVARCHAR(30)        NOT NULL,   -- 'ROTEM-STACK', 'ROTEM-DPU3'
    device_name     NVARCHAR(100)       NOT NULL,
    device_type     NVARCHAR(50)        NOT NULL,   -- 'STACK_DEVICE', 'DPU3', 'AREA_MONITOR'
    ip_address      NVARCHAR(45)        NULL,
    port            INT                 NULL,
    protocol        NVARCHAR(20)        NOT NULL,   -- 'TCP_POLLING', 'HTTP', 'MODBUS'
    poll_interval_s INT                 NOT NULL DEFAULT 10,
    connect_timeout_s DECIMAL(5,1)      NOT NULL DEFAULT 5.0,
    read_timeout_s  DECIMAL(5,1)        NOT NULL DEFAULT 8.0,
    firmware_ver    NVARCHAR(50)        NULL,
    serial_number   NVARCHAR(100)       NULL,
    model_number    NVARCHAR(100)       NULL,
    is_active       BIT                 NOT NULL DEFAULT 1,
    notes           NVARCHAR(500)       NULL,
    created_at      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by      INT                 NOT NULL,
    CONSTRAINT PK_devices PRIMARY KEY (device_id),
    CONSTRAINT UQ_devices_code UNIQUE (device_code),
    CONSTRAINT FK_devices_system FOREIGN KEY (system_id) REFERENCES systems(system_id),
    CONSTRAINT FK_devices_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);
GO

-- ─── Detectors ────────────────────────────────────────────────────────────────
-- Physical detector elements within a device
CREATE TABLE detectors (
    detector_id     INT IDENTITY(1,1)   NOT NULL,
    device_id       INT                 NOT NULL,
    detector_code   NVARCHAR(30)        NOT NULL,   -- 'PM11', 'GM42', 'W1'..'W5'
    detector_name   NVARCHAR(100)       NOT NULL,
    detector_type   NVARCHAR(50)        NOT NULL,   -- 'PHOTOMULTIPLIER', 'GEIGER_MUELLER', 'BETA', 'AIRFLOW'
    model_number    NVARCHAR(100)       NULL,
    serial_number   NVARCHAR(100)       NULL,
    manufacturer    NVARCHAR(100)       NULL,
    calibration_due DATE                NULL,       -- Populated from calibration_records
    is_active       BIT                 NOT NULL DEFAULT 1,
    notes           NVARCHAR(500)       NULL,
    created_at      DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by      INT                 NOT NULL,
    CONSTRAINT PK_detectors PRIMARY KEY (detector_id),
    CONSTRAINT UQ_detectors_code UNIQUE (detector_code),
    CONSTRAINT FK_detectors_device FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
GO

-- ─── Units of Measure ─────────────────────────────────────────────────────────
CREATE TABLE units_of_measure (
    uom_id          INT IDENTITY(1,1)   NOT NULL,
    uom_code        NVARCHAR(20)        NOT NULL,   -- 'CPS', 'MR_PER_HR', 'M3_PER_S', 'COUNT'
    uom_symbol      NVARCHAR(20)        NOT NULL,   -- 'cps', 'mR/h', 'm³/sec', 'COUNT'
    uom_name        NVARCHAR(100)       NOT NULL,   -- 'Counts Per Second', 'Milliroentgen per Hour'
    quantity_type   NVARCHAR(50)        NOT NULL,   -- 'ACTIVITY', 'DOSE_RATE', 'FLOW_RATE', 'COUNT'
    si_conversion   DECIMAL(20,10)      NULL,       -- Factor to convert to SI base unit
    si_unit         NVARCHAR(20)        NULL,       -- SI base unit symbol
    CONSTRAINT PK_uom PRIMARY KEY (uom_id),
    CONSTRAINT UQ_uom_code UNIQUE (uom_code)
);
GO

-- ─── Channels ─────────────────────────────────────────────────────────────────
-- Logical measurement channels; one channel per Rotem PointID
CREATE TABLE channels (
    channel_id          INT IDENTITY(1,1)   NOT NULL,
    device_id           INT                 NOT NULL,
    detector_id         INT                 NULL,
    channel_code        NVARCHAR(30)        NOT NULL,   -- 'STACK.PM11', 'STACK.GM42', 'STACK.W1'
    channel_name        NVARCHAR(100)       NOT NULL,
    rotem_point_id      INT                 NULL,       -- 1-9 from Rotem WebiSmarts
    rotem_point_name    NVARCHAR(50)        NULL,       -- 'StackPM11', 'W1', etc.
    rotem_adapter_id    INT                 NULL,       -- AdapterID from Rotem config
    uom_id              INT                 NOT NULL,
    is_stack_detector   BIT                 NOT NULL DEFAULT 0,
    display_rate        BIT                 NOT NULL DEFAULT 1,
    display_dose        BIT                 NOT NULL DEFAULT 0,
    expected_update_s   INT                 NOT NULL DEFAULT 15,  -- Expected reading interval
    stale_threshold_s   INT                 NOT NULL DEFAULT 60,  -- Mark stale after N seconds
    is_active           BIT                 NOT NULL DEFAULT 1,
    notes               NVARCHAR(500)       NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL,
    CONSTRAINT PK_channels PRIMARY KEY (channel_id),
    CONSTRAINT UQ_channels_code UNIQUE (channel_code),
    CONSTRAINT FK_channels_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT FK_channels_detector FOREIGN KEY (detector_id) REFERENCES detectors(detector_id),
    CONSTRAINT FK_channels_uom FOREIGN KEY (uom_id) REFERENCES units_of_measure(uom_id)
);
GO

-- ─── Alarm Profiles ───────────────────────────────────────────────────────────
-- Versioned threshold sets per channel (each change creates a new row)
CREATE TABLE alarm_profiles (
    profile_id              INT IDENTITY(1,1)   NOT NULL,
    channel_id              INT                 NOT NULL,
    profile_version         INT                 NOT NULL DEFAULT 1,
    low_threshold           DECIMAL(18,6)       NULL,       -- Below-minimum alert (detector failure)
    alert_threshold         DECIMAL(18,6)       NOT NULL,   -- First notification level
    alarm_threshold         DECIMAL(18,6)       NOT NULL,   -- Action required
    danger_threshold        DECIMAL(18,6)       NOT NULL,   -- Immediate action + e-signature
    high_dose_threshold     DECIMAL(18,6)       NULL,       -- Regulatory dose rate limit
    reset_dose_interval_hr  INT                 NOT NULL DEFAULT 24,
    effective_from          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    effective_to            DATETIME2(7)        NULL,
    is_current              BIT                 NOT NULL DEFAULT 1,
    change_reason           NVARCHAR(500)       NOT NULL,
    approved_by             INT                 NOT NULL,
    approval_signature_id   INT                 NULL,       -- FK set after electronic_signatures created
    created_at              DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by              INT                 NOT NULL,
    CONSTRAINT PK_alarm_profiles PRIMARY KEY (profile_id),
    CONSTRAINT UQ_profile_channel_version UNIQUE (channel_id, profile_version),
    CONSTRAINT FK_profiles_channel FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    CONSTRAINT CHK_threshold_order CHECK (
        alert_threshold < alarm_threshold AND alarm_threshold < danger_threshold
    )
);
GO

-- ─── Users ────────────────────────────────────────────────────────────────────
-- IQ-RAD internal users (separate from Rotem WebiSmarts users)
CREATE TABLE users (
    user_id             INT IDENTITY(1,1)   NOT NULL,
    username            NVARCHAR(50)        NOT NULL,
    email               NVARCHAR(200)       NOT NULL,
    full_name           NVARCHAR(200)       NOT NULL,
    hashed_password     NVARCHAR(200)       NOT NULL,
    role                NVARCHAR(20)        NOT NULL,   -- ADMIN, OPERATOR, VIEWER, EMISSIONS, DEVELOPER
    is_active           BIT                 NOT NULL DEFAULT 1,
    is_locked           BIT                 NOT NULL DEFAULT 0,
    failed_login_count  INT                 NOT NULL DEFAULT 0,
    last_login_at       DATETIME2(7)        NULL,
    last_login_ip       NVARCHAR(45)        NULL,
    password_changed_at DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL DEFAULT 1,
    CONSTRAINT PK_users PRIMARY KEY (user_id),
    CONSTRAINT UQ_users_username UNIQUE (username),
    CONSTRAINT UQ_users_email UNIQUE (email),
    CONSTRAINT CHK_users_role CHECK (role IN ('ADMIN', 'OPERATOR', 'VIEWER', 'EMISSIONS', 'DEVELOPER'))
);
GO

-- ─── Token Blacklist ──────────────────────────────────────────────────────────
-- Invalidated JWT session IDs (logout, lockout, forced expiry)
CREATE TABLE token_blacklist (
    blacklist_id    BIGINT IDENTITY(1,1) NOT NULL,
    session_id      NVARCHAR(36)        NOT NULL,
    user_id         INT                 NOT NULL,
    invalidated_at  DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    reason          NVARCHAR(50)        NOT NULL,   -- 'LOGOUT', 'LOCKOUT', 'ADMIN_REVOKE'
    expires_at      DATETIME2(7)        NOT NULL,   -- Purge after token natural expiry
    CONSTRAINT PK_token_blacklist PRIMARY KEY (blacklist_id),
    CONSTRAINT UQ_token_session UNIQUE (session_id)
);
GO
