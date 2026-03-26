-- ============================================================================
-- IQ-RAD: Seed / Reference Data
-- Schema Version: 1.0
-- Description: Initial reference data — vendors, units of measure, system admin
--              user, Rotem site/device/channel configuration derived from
--              WebiSmarts system info (site: USA56, Stack: 10.0.0.160:4001)
-- ============================================================================

USE IQ_RAD;
GO

-- ─── System Admin User (bootstrap — change password immediately after install) ─
INSERT INTO users (username, email, full_name, hashed_password, role, created_by)
VALUES (
    'iqrad_admin',
    'admin@iqlabs.local',
    'IQ-RAD System Administrator',
    -- Placeholder hash — application startup will re-hash if IQRAD_ADMIN_PASSWORD env var is set
    '$2b$12$placeholder_change_on_first_login_xxxxxxxxxxxxxxxxxxxxxxx',
    'ADMIN',
    1
);
GO

-- ─── Vendors ──────────────────────────────────────────────────────────────────
INSERT INTO vendors (vendor_code, vendor_name, support_contact) VALUES
    ('ROTEM',   'Rotem Industries Ltd.',            'support@rotem.co.il'),
    ('COMECER', 'Comecer S.p.A.',                   'service@comecer.com'),
    ('LUDLUM',  'Ludlum Measurements Inc.',         'service@ludlums.com'),
    ('INTERNAL','IQ-RAD Internal/System',           NULL);
GO

-- ─── Units of Measure ─────────────────────────────────────────────────────────
INSERT INTO units_of_measure (uom_code, uom_symbol, uom_name, quantity_type, si_conversion, si_unit) VALUES
    ('CPS',       'cps',     'Counts Per Second',         'ACTIVITY',   NULL,       NULL),
    ('COUNT',     'COUNT',   'Cumulative Count',          'COUNT',      NULL,       NULL),
    ('MR_PER_HR', 'mR/h',   'Milliroentgen per Hour',    'DOSE_RATE',  2.58e-7,    'C/(kg·h)'),
    ('M3_PER_S',  'm³/sec', 'Cubic Metres per Second',   'FLOW_RATE',  1.0,        'm³/s'),
    ('MR',        'mR',     'Milliroentgen',              'DOSE',       2.58e-7,    'C/kg'),
    ('USIEVHR',   'μSv/h',  'Microsievert per Hour',     'DOSE_RATE',  1.0e-6,     'Sv/h'),
    ('MSIEVHR',   'mSv/h',  'Millisievert per Hour',     'DOSE_RATE',  1.0e-3,     'Sv/h'),
    ('MBQM3',     'mBq/m³', 'Millibecquerel per Cubic Metre', 'CONCENTRATION', 1.0e-3, 'Bq/m³');
GO

-- ─── Site: USA56 (from WebiSmarts siteName) ───────────────────────────────────
INSERT INTO sites (site_code, site_name, timezone, created_by) VALUES
    ('USA56', 'IQLabs USA Site 56', 'America/New_York', 1);
GO

-- ─── System: Rotem Stack Monitor ─────────────────────────────────────────────
INSERT INTO systems (site_id, system_code, system_name, system_type, description, created_by)
VALUES (
    (SELECT site_id FROM sites WHERE site_code = 'USA56'),
    'USA56-STACK',
    'Rotem Stack Radiation Monitor',
    'STACK',
    'Rotem WebiSmarts stack monitoring system. Connects to Rotem stack device at 10.0.0.160:4001 and DPU3 at :5000.',
    1
);
GO

-- ─── Devices ──────────────────────────────────────────────────────────────────
DECLARE @sys_id INT = (SELECT system_id FROM systems WHERE system_code = 'USA56-STACK');
DECLARE @vendor_id INT = (SELECT vendor_id FROM vendors WHERE vendor_code = 'ROTEM');

INSERT INTO devices (system_id, vendor_id, device_code, device_name, device_type,
                     ip_address, port, protocol, poll_interval_s, firmware_ver, created_by)
VALUES
    (@sys_id, @vendor_id, 'ROTEM-STACK', 'Rotem Stack Device',
     'STACK_DEVICE', '10.0.0.160', 4001, 'TCP_POLLING', 10, NULL, 1),
    (@sys_id, @vendor_id, 'ROTEM-DPU3', 'Rotem DPU3 Unit',
     'DPU3', '10.0.0.160', 5000, 'TCP_POLLING', 10, NULL, 1);
GO

-- ─── Detectors (from WebiSmarts Points) ──────────────────────────────────────
DECLARE @stack_dev_id INT = (SELECT device_id FROM devices WHERE device_code = 'ROTEM-STACK');
DECLARE @dpu3_dev_id  INT = (SELECT device_id FROM devices WHERE device_code = 'ROTEM-DPU3');

INSERT INTO detectors (device_id, detector_code, detector_name, detector_type, created_by)
VALUES
    -- Stack device detectors (PointID 2-4)
    (@stack_dev_id, 'PM11',  'PM11 Photomultiplier',      'PHOTOMULTIPLIER', 1),
    (@stack_dev_id, 'GM42',  'GM-42 Geiger-Mueller',      'GEIGER_MUELLER',  1),
    (@stack_dev_id, 'AIR',   'Stack Air Flow Sensor',     'AIRFLOW',         1),
    -- DPU3 beta detectors (PointID 5-9, AdapterID 11-15)
    (@dpu3_dev_id,  'W1',    'Beta Detector Window 1',    'BETA',            1),
    (@dpu3_dev_id,  'W2',    'Beta Detector Window 2',    'BETA',            1),
    (@dpu3_dev_id,  'W3',    'Beta Detector Window 3',    'BETA',            1),
    (@dpu3_dev_id,  'W4',    'Beta Detector Window 4',    'BETA',            1),
    (@dpu3_dev_id,  'W5',    'Beta Detector Window 5',    'BETA',            1);
GO

-- ─── Channels (from WebiSmarts Points PointID 2-9) ────────────────────────────
-- PointID 1 (HyperLink) is a UI element, not a measurement channel — excluded
DECLARE @stack_dev_id INT = (SELECT device_id FROM devices WHERE device_code = 'ROTEM-STACK');
DECLARE @dpu3_dev_id  INT = (SELECT device_id FROM devices WHERE device_code = 'ROTEM-DPU3');

DECLARE @pm11_det   INT = (SELECT detector_id FROM detectors WHERE detector_code = 'PM11');
DECLARE @gm42_det   INT = (SELECT detector_id FROM detectors WHERE detector_code = 'GM42');
DECLARE @air_det    INT = (SELECT detector_id FROM detectors WHERE detector_code = 'AIR');
DECLARE @w1_det     INT = (SELECT detector_id FROM detectors WHERE detector_code = 'W1');
DECLARE @w2_det     INT = (SELECT detector_id FROM detectors WHERE detector_code = 'W2');
DECLARE @w3_det     INT = (SELECT detector_id FROM detectors WHERE detector_code = 'W3');
DECLARE @w4_det     INT = (SELECT detector_id FROM detectors WHERE detector_code = 'W4');
DECLARE @w5_det     INT = (SELECT detector_id FROM detectors WHERE detector_code = 'W5');

DECLARE @cps_uom    INT = (SELECT uom_id FROM units_of_measure WHERE uom_code = 'CPS');
DECLARE @mr_hr_uom  INT = (SELECT uom_id FROM units_of_measure WHERE uom_code = 'MR_PER_HR');
DECLARE @m3s_uom    INT = (SELECT uom_id FROM units_of_measure WHERE uom_code = 'M3_PER_S');

INSERT INTO channels (device_id, detector_id, channel_code, channel_name,
                      rotem_point_id, rotem_point_name, rotem_adapter_id,
                      uom_id, display_rate, display_dose, created_by)
VALUES
    -- PointID 2: StackPM11
    (@stack_dev_id, @pm11_det, 'STACK.PM11', 'Stack PM11 Count Rate',
     2, 'StackPM11', 0, @cps_uom, 1, 0, 1),
    -- PointID 3: StackGM42
    (@stack_dev_id, @gm42_det, 'STACK.GM42', 'Stack GM-42 Dose Rate',
     3, 'StackGM42', 1, @mr_hr_uom, 1, 0, 1),
    -- PointID 4: StackAir
    (@stack_dev_id, @air_det,  'STACK.AIR',  'Stack Air Flow',
     4, 'StackAir',  2, @m3s_uom, 1, 0, 1),
    -- PointID 5: W1 (BetaW1)
    (@dpu3_dev_id,  @w1_det,   'STACK.W1',   'Beta Detector W1',
     5, 'W1',        11, @cps_uom, 1, 0, 1),
    -- PointID 6: W2 (BetaW2)
    (@dpu3_dev_id,  @w2_det,   'STACK.W2',   'Beta Detector W2',
     6, 'W2',        12, @cps_uom, 1, 0, 1),
    -- PointID 7: W3 (BetaW3)
    (@dpu3_dev_id,  @w3_det,   'STACK.W3',   'Beta Detector W3',
     7, 'W3',        13, @cps_uom, 1, 0, 1),
    -- PointID 8: W4 (BetaW4)
    (@dpu3_dev_id,  @w4_det,   'STACK.W4',   'Beta Detector W4',
     8, 'W4',        14, @cps_uom, 1, 0, 1),
    -- PointID 9: W5 (BetaW5)
    (@dpu3_dev_id,  @w5_det,   'STACK.W5',   'Beta Detector W5',
     9, 'W5',        15, @cps_uom, 1, 0, 1);
GO

-- ─── Initial Alarm Profiles (from WebiSmarts thresholds) ─────────────────────
-- NOTE: These initial thresholds match the WebiSmarts defaults exactly.
-- Operational thresholds must be reviewed and updated by qualified personnel
-- before production use, with full change control and e-signature.
DECLARE @pm11_ch  INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.PM11');
DECLARE @gm42_ch  INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.GM42');
DECLARE @air_ch   INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.AIR');
DECLARE @w1_ch    INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.W1');
DECLARE @w2_ch    INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.W2');
DECLARE @w3_ch    INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.W3');
DECLARE @w4_ch    INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.W4');
DECLARE @w5_ch    INT = (SELECT channel_id FROM channels WHERE channel_code = 'STACK.W5');
DECLARE @admin_id INT = (SELECT user_id FROM users WHERE username = 'iqrad_admin');

-- PM11: Alert=999, Alarm=999999, Danger=999999999 (Rotem defaults — must be updated)
INSERT INTO alarm_profiles (channel_id, profile_version, low_threshold,
    alert_threshold, alarm_threshold, danger_threshold, high_dose_threshold,
    change_reason, approved_by, created_by)
VALUES
    (@pm11_ch, 1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@gm42_ch, 1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@air_ch,  1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@w1_ch,   1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@w2_ch,   1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@w3_ch,   1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@w4_ch,   1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id),
    (@w5_ch,   1, 0,   999, 999999, 999999999, 999999,
     'Initial seed from Rotem WebiSmarts defaults. MUST be reviewed and updated before production use.',
     @admin_id, @admin_id);
GO

-- ─── Requirements Traceability (Core regulatory requirements) ─────────────────
INSERT INTO requirements_traceability
    (req_code, req_category, regulation_ref, description, acceptance_criteria, risk_level, created_by)
VALUES
    ('IQ-RAD-REQ-001', 'GMP', '21 CFR 11.10(e)',
     'System shall maintain a computer-generated, time-stamped audit trail for all operator actions.',
     'Every API mutation writes to audit_trail within the same transaction. audit_trail is append-only (immutability trigger verified).',
     'HIGH', 1),
    ('IQ-RAD-REQ-002', 'GMP', '21 CFR 11.10(e)',
     'Raw device data shall be preserved exactly as received and never modified.',
     'raw_ingestion_log rows cannot be updated or deleted (trigger test passes). normalized_readings link back to ingestion_id.',
     'HIGH', 1),
    ('IQ-RAD-REQ-003', 'GMP', '21 CFR 11.200(a)(1)',
     'Electronic signatures shall use two distinct identification components.',
     'Password re-authentication required at signing time; JWT session_id serves as second component.',
     'HIGH', 1),
    ('IQ-RAD-REQ-004', 'GMP', '21 CFR 11.10(d)',
     'System shall limit access to authorized individuals.',
     'RBAC enforced on all endpoints. Account lockout after 5 failures. Session blacklist on logout.',
     'HIGH', 1),
    ('IQ-RAD-REQ-005', 'FUNCTIONAL', '10 CFR 20.1501',
     'System shall monitor all required radiation survey points continuously.',
     'All 8 Rotem channels (PM11, GM42, AIR, W1-W5) receive readings at configured poll interval with <120s gap.',
     'HIGH', 1),
    ('IQ-RAD-REQ-006', 'FUNCTIONAL', 'Internal',
     'System shall alarm within one poll cycle of threshold breach.',
     'Threshold evaluation occurs synchronously in ingestion pipeline. Active alarm created before ingestion_service loop completes.',
     'HIGH', 1),
    ('IQ-RAD-REQ-007', 'GMP', '21 CFR 212.60(d)',
     'All configuration changes shall be versioned with full audit trail.',
     'alarm_profiles table is versioned. config_versions snapshot created for every change. threshold_change_log populated.',
     'HIGH', 1),
    ('IQ-RAD-REQ-008', 'FUNCTIONAL', 'Internal',
     'System time shall be synchronised to NTP.',
     'heartbeat_log records ntp_offset_ms. Readings with abs(ntp_offset_ms) > 500 flagged SUSPECT.',
     'MEDIUM', 1),
    ('IQ-RAD-REQ-009', 'FUNCTIONAL', 'Internal',
     'System shall detect stale/offline detector conditions and alarm.',
     'STALE channel alarm generated if no reading received within stale_threshold_s. COMM_FAIL alarm if device offline.',
     'HIGH', 1),
    ('IQ-RAD-REQ-010', 'GMP', '10 CFR 20.2102',
     'Calibration status of each detector shall be tracked and overdue calibration shall alert.',
     'calibration_records table maintained. ComplianceWatchdog generates advisory if next_due_date within 30 days.',
     'MEDIUM', 1);
GO
