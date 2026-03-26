# IQ-RAD Requirements Traceability Matrix

**Document:** TM-IQ-RAD-001
**Version:** 1.0
**System:** IQ-RAD Radiation Monitoring System

---

## Requirements to Implementation to Test

| Req ID | Requirement | CFR Reference | Implementation | Test Script |
|--------|-------------|---------------|----------------|-------------|
| IQ-RAD-REQ-001 | Raw data must be immutable once stored | 21 CFR 11.10(e) | `database/schema/06_triggers.sql` — DDL triggers ROLLBACK on UPDATE/DELETE | `tests/integration/test_immutability.py` |
| IQ-RAD-REQ-002 | All normalized readings traceable to raw ingestion | 10 CFR 20.2103 | `normalized_readings.ingestion_id` FK → `raw_ingestion_log` | `tests/unit/test_normalizer.py::test_parse_single_good_point` |
| IQ-RAD-REQ-003 | NTP drift >500ms flags reading as SUSPECT | 21 CFR 11.10(b) | `app/core/ntp_sync.py`, `app/normalization/normalizer.py` | `tests/unit/test_normalizer.py::test_ntp_invalid_marks_suspect` |
| IQ-RAD-REQ-004 | PointID mapping covers all 8 Rotem channels | System design | `app/normalization/point_map.py` — ROTEM_POINT_MAP dict | `tests/validation/IQ_001::test_point_mapping` |
| IQ-RAD-REQ-005 | Threshold versioning preserves history | 21 CFR 11.10(e) | `alarm_profiles` table with `profile_version`, `is_current`; `threshold_change_log` | `tests/integration/test_immutability.py::test_threshold_change_log_immutable` |
| IQ-RAD-REQ-006 | Configuration changes require e-signature | 21 CFR 11.200 | `app/api/v1/devices.py` — PATCH thresholds calls `signature_service.create_signature()` | `tests/integration/test_api_auth.py` |
| IQ-RAD-REQ-007 | Threshold evaluation: 5 levels × 9 channels | 10 CFR 20.1201 | `app/rules_engine/threshold_evaluator.py` | `tests/unit/test_threshold_evaluator.py` — 45 parametrized tests |
| IQ-RAD-REQ-008 | Alarm state machine: ACTIVE→ACKNOWLEDGED→CLEARED | 10 CFR 20.1201 | `app/rules_engine/alarm_manager.py` | `tests/unit/test_alarm_manager.py` |
| IQ-RAD-REQ-009 | JWT + bcrypt + RBAC auth with lockout | 21 CFR 11.300 | `app/core/security.py`, `app/api/v1/auth.py` | `tests/unit/test_security.py`, `tests/integration/test_api_auth.py` |
| IQ-RAD-REQ-010 | Audit trail for every authenticated API call | 21 CFR 11.10(e) | `app/core/audit.py` — AuditMiddleware | `tests/validation/OQ_001::test_oq_004_audit_middleware_exists` |
| IQ-RAD-REQ-011 | Electronic signature: SHA-256 HMAC hash | 21 CFR 11.50, 11.70 | `app/services/signature_service.py`, `app/core/security.py` | `tests/unit/test_security.py::test_signature_hash_deterministic` |
| IQ-RAD-REQ-012 | Alarm DANGER/HIGH_DOSE require e-signature for ack | 21 CFR 11.200 | `app/api/v1/alarms.py` — threshold check before ack | `tests/validation/OQ_001::test_oq_003_hash_length` |
| IQ-RAD-REQ-013 | Report approval requires e-signature | 21 CFR 11.200 | `app/api/v1/reports.py::approve_report` | Manual PQ test |
| IQ-RAD-REQ-014 | Calibration records require e-signature | 21 CFR 11.200 | `app/api/v1/calibration.py::review_calibration` | Manual PQ test |
| IQ-RAD-REQ-015 | 30-day calibration due warning | 10 CFR 20.1501 | `app/rules_engine/compliance_checks.py` — `ComplianceWatchdog` | Manual PQ test |
| IQ-RAD-REQ-016 | WebSocket live feed within 2s latency | System performance | `app/services/websocket_service.py`, `app/services/ingestion_service.py` | `tests/validation/PQ_001` (TBD) |
| IQ-RAD-REQ-017 | Exponential backoff reconnect for device connectors | System resilience | `app/connectors/rotem_stack.py`, `rotem_dpu3.py` — `_backoff_delay()` | Manual network failure test |
| IQ-RAD-REQ-018 | Raw bytes preserved in `raw_ingestion_log` | 10 CFR 20.2103 | `app/services/ingestion_service.py::_process_packet()` | `tests/integration/test_ingestion_pipeline.py` (TBD) |
| IQ-RAD-REQ-019 | BAD quality reading triggers ALARM | 10 CFR 20.1201 | `app/rules_engine/threshold_evaluator.py::evaluate()` — BAD → ALARM | `tests/unit/test_threshold_evaluator.py::test_bad_quality_forces_alarm` |
| IQ-RAD-REQ-020 | All pages require authentication; RBAC enforced | 21 CFR 11.10(d) | `frontend/src/components/common/ProtectedRoute.tsx`, backend `require_permission()` | Manual UI test |

---

## Coverage Summary

| Phase | Total Requirements | Covered by Automated Tests | Covered by Manual Tests |
|-------|-------------------|---------------------------|------------------------|
| IQ | 5 | 5 | 0 |
| OQ | 10 | 8 | 2 |
| PQ | 5 | 1 | 4 |
| **Total** | **20** | **14 (70%)** | **6 (30%)** |

---

## Open Items

| Item | Description | Owner | Target |
|------|-------------|-------|--------|
| TM-OPEN-001 | Complete `tests/integration/test_ingestion_pipeline.py` | Developer | Sprint 6 |
| TM-OPEN-002 | Add PQ continuous-run test (24h) | QA | Sprint 6 |
| TM-OPEN-003 | Manual test: DANGER alarm e-signature round-trip | QA | Sprint 6 |
| TM-OPEN-004 | Manual test: Threshold change with wrong password → 401 | QA | Sprint 6 |
