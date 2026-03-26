-- ============================================================================
-- IQ-RAD: Immutability Enforcement Triggers
-- Schema Version: 1.0
-- Regulatory: 21 CFR Part 11 §11.10(e) — records protected from deletion
--             and alteration
-- Description: DDL triggers that ROLLBACK any UPDATE or DELETE attempt on
--              immutable tables. This provides defense-in-depth beyond
--              application-layer controls. These triggers survive application
--              bugs, rogue SQL sessions, and accidental admin actions.
-- ============================================================================

USE IQ_RAD;
GO

-- ─── raw_ingestion_log — IMMUTABLE ───────────────────────────────────────────
CREATE TRIGGER trg_raw_ingestion_immutable
ON raw_ingestion_log
AFTER UPDATE, DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: raw_ingestion_log is immutable (21 CFR Part 11 §11.10(e)). UPDATE and DELETE operations are prohibited.',
        16, 1
    );
END;
GO

-- ─── normalized_readings — IMMUTABLE ─────────────────────────────────────────
CREATE TRIGGER trg_normalized_readings_immutable
ON normalized_readings
AFTER UPDATE, DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: normalized_readings is immutable (21 CFR Part 11 §11.10(e)). UPDATE and DELETE operations are prohibited.',
        16, 1
    );
END;
GO

-- ─── audit_trail — IMMUTABLE ─────────────────────────────────────────────────
CREATE TRIGGER trg_audit_trail_immutable
ON audit_trail
AFTER UPDATE, DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: audit_trail is immutable (21 CFR Part 11 §11.10(e)). UPDATE and DELETE operations are prohibited.',
        16, 1
    );
END;
GO

-- ─── alarm_history — IMMUTABLE ───────────────────────────────────────────────
CREATE TRIGGER trg_alarm_history_immutable
ON alarm_history
AFTER UPDATE, DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: alarm_history is immutable (21 CFR Part 11 §11.10(e)). UPDATE and DELETE operations are prohibited.',
        16, 1
    );
END;
GO

-- ─── electronic_signatures — RESTRICT DELETE ─────────────────────────────────
-- Signatures can be revoked (is_valid=0) but never deleted
CREATE TRIGGER trg_esignatures_no_delete
ON electronic_signatures
AFTER DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: electronic_signatures cannot be deleted (21 CFR Part 11 §11.50). Set is_valid=0 to revoke.',
        16, 1
    );
END;
GO

-- ─── threshold_change_log — IMMUTABLE ────────────────────────────────────────
CREATE TRIGGER trg_threshold_change_immutable
ON threshold_change_log
AFTER UPDATE, DELETE
AS
BEGIN
    ROLLBACK TRANSACTION;
    RAISERROR(
        'IQ-RAD COMPLIANCE VIOLATION: threshold_change_log is immutable. UPDATE and DELETE operations are prohibited.',
        16, 1
    );
END;
GO
