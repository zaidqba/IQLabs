-- ============================================================================
-- IQ-RAD: Validation & Quality System Tables
-- Schema Version: 1.0
-- Regulatory: 21 CFR Part 11 §11.10 — validation of systems
--             21 CFR Part 212.60(d) — documentation of validation
-- Description: IQ/OQ/PQ evidence, requirements traceability, CAPA/deviation.
--              These tables constitute the machine-readable validation package.
-- ============================================================================

USE IQ_RAD;
GO

-- ─── Requirements Traceability ───────────────────────────────────────────────
-- Links business/regulatory requirements to code and test evidence
CREATE TABLE requirements_traceability (
    req_id              INT IDENTITY(1,1)   NOT NULL,
    req_code            NVARCHAR(20)        NOT NULL,   -- 'IQ-RAD-REQ-001'
    req_category        NVARCHAR(50)        NOT NULL,   -- 'FUNCTIONAL', 'GMP', 'SECURITY', 'PERFORMANCE'
    regulation_ref      NVARCHAR(200)       NULL,       -- '21 CFR 11.10(e)', '10 CFR 20.2102'
    description         NVARCHAR(1000)      NOT NULL,
    acceptance_criteria NVARCHAR(1000)      NOT NULL,
    test_script_ids     NVARCHAR(500)       NULL,       -- Comma-separated test script codes
    implementation_ref  NVARCHAR(500)       NULL,       -- 'app/rules_engine/threshold_evaluator.py'
    status              NVARCHAR(20)        NOT NULL DEFAULT 'OPEN',
    -- OPEN | IMPLEMENTED | VERIFIED | APPROVED | DEFERRED
    risk_level          NVARCHAR(10)        NOT NULL DEFAULT 'MEDIUM', -- HIGH | MEDIUM | LOW
    notes               NVARCHAR(MAX)       NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL,
    CONSTRAINT PK_requirements PRIMARY KEY (req_id),
    CONSTRAINT UQ_req_code UNIQUE (req_code),
    CONSTRAINT CHK_req_status CHECK (
        status IN ('OPEN', 'IMPLEMENTED', 'VERIFIED', 'APPROVED', 'DEFERRED')
    )
);
GO

-- ─── Test Scripts ─────────────────────────────────────────────────────────────
-- Formal test protocol definitions (IQ, OQ, PQ scripts)
CREATE TABLE test_scripts (
    script_id           INT IDENTITY(1,1)   NOT NULL,
    script_code         NVARCHAR(30)        NOT NULL,   -- 'IQ-001', 'OQ-012', 'PQ-003'
    script_type         NVARCHAR(10)        NOT NULL,   -- 'IQ', 'OQ', 'PQ', 'UAT'
    title               NVARCHAR(200)       NOT NULL,
    description         NVARCHAR(MAX)       NOT NULL,
    preconditions       NVARCHAR(MAX)       NULL,
    test_steps          NVARCHAR(MAX)       NOT NULL,   -- JSON array of steps
    expected_results    NVARCHAR(MAX)       NOT NULL,
    acceptance_criteria NVARCHAR(MAX)       NOT NULL,
    req_codes           NVARCHAR(500)       NULL,       -- Comma-separated requirement codes
    version             NVARCHAR(10)        NOT NULL DEFAULT '1.0',
    status              NVARCHAR(20)        NOT NULL DEFAULT 'DRAFT',
    -- DRAFT | APPROVED | OBSOLETE
    approved_by         INT                 NULL,
    approved_at_utc     DATETIME2(7)        NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL,
    CONSTRAINT PK_test_scripts PRIMARY KEY (script_id),
    CONSTRAINT UQ_script_code UNIQUE (script_code)
);
GO

-- ─── Test Execution Log ───────────────────────────────────────────────────────
-- Machine-readable test execution results (pytest writes here via validation fixtures)
CREATE TABLE test_execution_log (
    exec_id             BIGINT IDENTITY(1,1)    NOT NULL,
    script_code         NVARCHAR(30)            NOT NULL,
    executed_at_utc     DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    executed_by         INT                     NOT NULL,
    environment         NVARCHAR(20)            NOT NULL,   -- 'DEV', 'QA', 'STAGING', 'PROD'
    system_version      NVARCHAR(50)            NOT NULL,
    result              NVARCHAR(10)            NOT NULL,   -- 'PASS', 'FAIL', 'BLOCKED', 'N_A'
    actual_result       NVARCHAR(MAX)           NULL,
    deviation_ref       NVARCHAR(20)            NULL,       -- FK to deviation_log.dev_code
    evidence_path       NVARCHAR(500)           NULL,       -- Path to screenshot/log evidence
    notes               NVARCHAR(MAX)           NULL,
    signature_id        INT                     NULL,
    created_at          DATETIME2(7)            NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_test_execution PRIMARY KEY (exec_id),
    CONSTRAINT FK_exec_user FOREIGN KEY (executed_by) REFERENCES users(user_id),
    CONSTRAINT FK_exec_signature FOREIGN KEY (signature_id)
        REFERENCES electronic_signatures(signature_id),
    CONSTRAINT CHK_exec_result CHECK (result IN ('PASS', 'FAIL', 'BLOCKED', 'N_A'))
);
GO

-- ─── Deviation Log ───────────────────────────────────────────────────────────
-- Formal deviation records for validation failures or GMP deviations
CREATE TABLE deviation_log (
    deviation_id        INT IDENTITY(1,1)   NOT NULL,
    dev_code            NVARCHAR(20)        NOT NULL,   -- 'DEV-2025-001'
    title               NVARCHAR(200)       NOT NULL,
    description         NVARCHAR(MAX)       NOT NULL,
    deviation_type      NVARCHAR(30)        NOT NULL,   -- 'VALIDATION', 'OPERATIONAL', 'DATA_QUALITY'
    severity            NVARCHAR(10)        NOT NULL,   -- 'CRITICAL', 'MAJOR', 'MINOR'
    detected_at_utc     DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    detected_by         INT                 NOT NULL,
    status              NVARCHAR(20)        NOT NULL DEFAULT 'OPEN',
    -- OPEN | UNDER_REVIEW | CAPA_PENDING | CLOSED | ESCALATED
    root_cause          NVARCHAR(MAX)       NULL,
    impact_assessment   NVARCHAR(MAX)       NULL,
    immediate_action    NVARCHAR(MAX)       NULL,
    capa_id             INT                 NULL,
    closed_at_utc       DATETIME2(7)        NULL,
    closed_by           INT                 NULL,
    closure_signature_id INT                NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_deviations PRIMARY KEY (deviation_id),
    CONSTRAINT UQ_dev_code UNIQUE (dev_code),
    CONSTRAINT FK_dev_detected_by FOREIGN KEY (detected_by) REFERENCES users(user_id)
);
GO

-- ─── CAPA Log ────────────────────────────────────────────────────────────────
-- Corrective and Preventive Actions
CREATE TABLE capa_log (
    capa_id             INT IDENTITY(1,1)   NOT NULL,
    capa_code           NVARCHAR(20)        NOT NULL,   -- 'CAPA-2025-001'
    title               NVARCHAR(200)       NOT NULL,
    description         NVARCHAR(MAX)       NOT NULL,
    capa_type           NVARCHAR(20)        NOT NULL,   -- 'CORRECTIVE', 'PREVENTIVE'
    deviation_id        INT                 NULL,
    assigned_to         INT                 NOT NULL,
    due_date            DATE                NOT NULL,
    status              NVARCHAR(20)        NOT NULL DEFAULT 'OPEN',
    -- OPEN | IN_PROGRESS | COMPLETED | VERIFIED | CLOSED
    completion_evidence NVARCHAR(MAX)       NULL,
    completed_at_utc    DATETIME2(7)        NULL,
    completed_by        INT                 NULL,
    verified_by         INT                 NULL,
    verified_at_utc     DATETIME2(7)        NULL,
    verification_signature_id INT           NULL,
    created_at          DATETIME2(7)        NOT NULL DEFAULT SYSUTCDATETIME(),
    created_by          INT                 NOT NULL,
    CONSTRAINT PK_capa PRIMARY KEY (capa_id),
    CONSTRAINT UQ_capa_code UNIQUE (capa_code),
    CONSTRAINT FK_capa_deviation FOREIGN KEY (deviation_id) REFERENCES deviation_log(deviation_id),
    CONSTRAINT FK_capa_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(user_id)
);
GO
