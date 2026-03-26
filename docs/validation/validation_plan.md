# IQ-RAD Validation Plan

**Document:** VP-IQ-RAD-001
**Version:** 1.0
**Status:** DRAFT — Pending Review
**System:** IQ-RAD Radiation Monitoring System
**Facility:** Ionetix PET Drug Facility, Site USA56
**Date:** 2026-03-26

---

## 1. Purpose and Scope

This Validation Plan establishes the strategy, approach, and responsibilities for validating the IQ-RAD Radiation Monitoring System. IQ-RAD is a computerized system used to monitor environmental radiation levels in the PET drug production facility at Site USA56, connecting to Rotem WebiSmarts devices (Stack at 10.0.0.160:4001, DPU3 at :5000).

IQ-RAD is subject to:
- **21 CFR Part 212** — Current Good Manufacturing Practice for Positron Emission Tomography Drugs
- **21 CFR Part 11** — Electronic Records; Electronic Signatures
- **10 CFR Part 20** — Standards for Protection Against Radiation

---

## 2. System Description

IQ-RAD implements a five-layer architecture:

| Layer | Component | Purpose |
|-------|-----------|---------|
| 1 | TCP Connectors | Async polling of Rotem WebiSmarts devices |
| 2 | Normalization | Convert raw bytes → NormalizedEvent (vendor-agnostic) |
| 3 | Rules Engine | Threshold evaluation, alarm state machine, compliance watchdog |
| 4 | SQL Historian | Immutable storage (SQL Server 2022, Ionetix3/SQLEXPRESS) |
| 5 | Application | FastAPI REST + WebSocket + React dashboard |

**Monitored Channels:**

| PointID | IQ-RAD Code | Type | Units |
|---------|-------------|------|-------|
| 2 | STACK.PM11 | PM11 Gamma | CPS |
| 3 | STACK.GM42 | GM-42 Gamma | mR/h |
| 4 | STACK.AIR | Air Flow | m³/sec |
| 5–9 | STACK.W1–W5 | Beta detectors | CPS |

---

## 3. Validation Approach

### 3.1 Risk-Based Validation (GAMP 5)

IQ-RAD is classified as **Category 5** (Custom Software) per GAMP 5, requiring full IQ/OQ/PQ. Risk assessment focuses on:

| Risk | Impact | Control |
|------|--------|---------|
| Incorrect threshold evaluation | Patient/worker radiation exposure | Unit tests (45 parametrized), OQ test scripts |
| Data tampering | Regulatory non-compliance | DDL immutability triggers, verified in OQ |
| Unauthorized access | 21 CFR Part 11 violation | RBAC, JWT, account lockout |
| Clock drift | Incorrect timestamps on records | NTP monitoring, SUSPECT flag |
| Missing calibration | Inaccurate readings | Calibration watchdog, 30-day warning |

### 3.2 Qualification Phases

1. **Installation Qualification (IQ)** — Verify correct installation of all components
2. **Operational Qualification (OQ)** — Verify correct operation under normal/boundary conditions
3. **Performance Qualification (PQ)** — Verify sustained performance under production load

---

## 4. Acceptance Criteria

| ID | Criterion | Phase |
|----|-----------|-------|
| AC-001 | All 26 required database tables exist with correct schema | IQ |
| AC-002 | All 8 Rotem PointID → channel code mappings are correct | IQ |
| AC-003 | JWT secret rejects placeholders | IQ |
| AC-004 | All 5 severity levels evaluate correctly for all 9 channels (45 tests pass) | OQ |
| AC-005 | BAD quality forces ALARM regardless of value | OQ |
| AC-006 | Immutability triggers prevent UPDATE/DELETE on 5 protected tables | OQ |
| AC-007 | Electronic signature hash is 64 hex chars and unique per input | OQ |
| AC-008 | RBAC matrix enforces correct permissions for all 5 roles × 9 test cases | OQ |
| AC-009 | System sustains 60s continuous polling without error | PQ |
| AC-010 | Alarm state machine transitions NORMAL→ALERT→ALARM→ACKNOWLEDGED→CLEARED correctly | OQ |
| AC-011 | AuditMiddleware writes to audit_trail for every authenticated API call | OQ |
| AC-012 | NTP drift >500ms flags readings as SUSPECT | OQ |

---

## 5. Test Execution

All test results are recorded in `test_execution_log` table with:
- `test_script_id` (FK to `test_scripts`)
- `executed_at_utc`
- `executed_by_user_id`
- `result` (PASS/FAIL/ERROR)
- `actual_result` (text)
- `deviation_id` (FK to `deviation_log` if FAIL)

---

## 6. Responsibilities

| Role | Responsibility |
|------|---------------|
| System Owner (Physics) | Approve validation plan and final summary |
| QA | Review/approve all qualification documents |
| IT | Execute IQ protocols, verify infrastructure |
| End Users | Execute OQ/PQ protocols |

---

## 7. Change Control

After validation, any system change requires:
1. Change impact assessment
2. Re-execution of affected test scripts
3. Updated summary report
4. QA approval with electronic signature

All configuration changes are tracked in `config_versions` and `threshold_change_log` (immutable).

---

## 8. References

- IQ-RAD-IQ-001: Installation Qualification Protocol
- IQ-RAD-OQ-001: Operational Qualification Protocol
- IQ-RAD-PQ-001: Performance Qualification Protocol
- IQ-RAD-TM-001: Requirements Traceability Matrix
- GAMP 5 Guide, ISPE 2008
- 21 CFR Part 11
- 21 CFR Part 212
- 10 CFR Part 20
