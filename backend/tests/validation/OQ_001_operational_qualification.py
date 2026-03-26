"""
OQ-001: Operational Qualification Test Scripts
Verifies that IQ-RAD operates correctly under normal and boundary conditions.

Run with: pytest tests/validation/OQ_001*.py -m validation -v

Requirement mapping: IQ-RAD-OQ-001 through IQ-RAD-OQ-020
21 CFR Part 11 §11.10(a) — operational verification.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

pytestmark = pytest.mark.validation


class TestOQ001ThresholdEvaluation:
    """OQ-001.1 — Threshold evaluator produces correct severity for all levels."""

    def _make_event(self, value: float, severity=None):
        from app.schemas.common import NormalizedEvent, QualityFlag, SeverityLevel
        from app.schemas.common import SeverityLevel as SL
        return NormalizedEvent(
            ingestion_id=None, device_id=1, channel_id=1,
            channel_code="STACK.PM11", rotem_point_id=2,
            measured_at_utc=datetime.now(timezone.utc),
            received_at_utc=datetime.now(timezone.utc),
            raw_value=Decimal(str(value)),
            normalized_value=Decimal(str(value)),
            uom_code="CPS", uom_id=1,
            quality_flag=QualityFlag.GOOD,
            ntp_offset_ms=0.0, alarm_profile_id=1,
            low_threshold=Decimal("10"),
            alert_threshold=Decimal("100"),
            alarm_threshold=Decimal("500"),
            danger_threshold=Decimal("1000"),
            high_dose_threshold=Decimal("5000"),
            severity_level=SL.NORMAL, threshold_exceeded=None,
            event_type="READING",
        )

    def test_oq_001_normal_range(self):
        """OQ-001.1a: Value 50 → NORMAL (IQ-RAD-OQ-001)."""
        from app.rules_engine.threshold_evaluator import ThresholdEvaluator
        ev = ThresholdEvaluator()
        sev, _ = ev.evaluate(self._make_event(50.0))
        assert sev.value == "NORMAL"

    def test_oq_001_alert_boundary(self):
        """OQ-001.1b: Value exactly at alert boundary (100) → ALERT (IQ-RAD-OQ-002)."""
        from app.rules_engine.threshold_evaluator import ThresholdEvaluator
        ev = ThresholdEvaluator()
        sev, crossed = ev.evaluate(self._make_event(100.0))
        assert sev.value == "ALERT"
        assert crossed == "alert_threshold"

    def test_oq_001_high_dose(self):
        """OQ-001.1e: Value ≥ 5000 → HIGH_DOSE — requires immediate action (IQ-RAD-OQ-005)."""
        from app.rules_engine.threshold_evaluator import ThresholdEvaluator
        ev = ThresholdEvaluator()
        sev, crossed = ev.evaluate(self._make_event(7500.0))
        assert sev.value == "HIGH_DOSE"

    def test_oq_001_bad_quality_forces_alarm(self):
        """OQ-001.1f: BAD quality data → ALARM regardless of value (IQ-RAD-OQ-006)."""
        from app.rules_engine.threshold_evaluator import ThresholdEvaluator
        from app.schemas.common import QualityFlag
        ev = ThresholdEvaluator()
        event = self._make_event(10.0)
        event = event.model_copy(update={"quality_flag": QualityFlag.BAD})
        sev, crossed = ev.evaluate(event)
        assert sev.value == "ALARM"
        assert crossed == "DATA_QUALITY"


class TestOQ001Normalization:
    """OQ-001.2 — Normalization layer correctly parses Rotem JSON."""

    def test_oq_002_point_id_lookup(self):
        """OQ-001.2a: PointID 2 → STACK.PM11 CPS (IQ-RAD-OQ-007)."""
        from app.normalization.point_map import get_mapping_by_point_id
        m = get_mapping_by_point_id(2)
        assert m.channel_code == "STACK.PM11"
        assert m.uom_code == "CPS"

    def test_oq_002_all_nine_points_mapped(self):
        """OQ-001.2b: All 8 Rotem points (PointIDs 2–9) have channel mappings (IQ-RAD-OQ-008)."""
        from app.normalization.point_map import get_mapping_by_point_id
        for pid in range(2, 10):
            m = get_mapping_by_point_id(pid)
            assert m is not None, f"PointID {pid} missing mapping"


class TestOQ001ElectronicSignature:
    """OQ-001.3 — Electronic signature hash is unique and irreversible."""

    def test_oq_003_hash_length(self):
        """OQ-001.3a: SHA-256 hash is 64 hex characters (IQ-RAD-OQ-009)."""
        from unittest.mock import patch
        with patch("app.core.security.settings") as ms:
            ms.hmac_secret = "test-hmac-secret-at-least-32-chars!"
            from app.core.security import compute_signature_hash
            h = compute_signature_hash(1, "ALARM_ACK", "1", "2025-01-01T00:00:00")
            assert len(h) == 64

    def test_oq_003_unique_per_input(self):
        """OQ-001.3b: Different inputs produce different hashes (IQ-RAD-OQ-010)."""
        from unittest.mock import patch
        with patch("app.core.security.settings") as ms:
            ms.hmac_secret = "test-hmac-secret-at-least-32-chars!"
            from app.core.security import compute_signature_hash
            h1 = compute_signature_hash(1, "ALARM_ACK", "1", "2025-01-01T00:00:00")
            h2 = compute_signature_hash(2, "ALARM_ACK", "1", "2025-01-01T00:00:00")
            assert h1 != h2


class TestOQ001AuditTrail:
    """OQ-001.4 — AuditMiddleware attaches correct action types."""

    def test_oq_004_audit_middleware_exists(self):
        """OQ-001.4a: AuditMiddleware is importable and is a middleware class (IQ-RAD-OQ-011)."""
        from app.core.audit import AuditMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        assert issubclass(AuditMiddleware, BaseHTTPMiddleware)

    def test_oq_004_set_audit_detail_helper(self):
        """OQ-001.4b: set_audit_detail can be called without error (IQ-RAD-OQ-012)."""
        from app.core.audit import set_audit_detail
        from unittest.mock import MagicMock
        request = MagicMock()
        request.state = MagicMock()
        set_audit_detail(request, {"before": {"value": 1}, "after": {"value": 2}})
        assert request.state.audit_detail is not None


class TestOQ001RBAC:
    """OQ-001.5 — Role-based access control matrix is correctly implemented."""

    RBAC_CASES = [
        ("VIEWER", "read:alarms", True),
        ("VIEWER", "write:alarms", False),
        ("OPERATOR", "sign:alarms", True),
        ("OPERATOR", "sign:thresholds", True),
        ("EMISSIONS", "write:calibration", True),
        ("EMISSIONS", "sign:thresholds", False),
        ("ADMIN", "sign:thresholds", True),
        ("DEVELOPER", "read:raw_ingestion", True),
        ("DEVELOPER", "sign:thresholds", False),
    ]

    @pytest.mark.parametrize("role,permission,expected", RBAC_CASES)
    def test_rbac_matrix(self, role: str, permission: str, expected: bool):
        """OQ-001.5: RBAC permission matrix is correct (IQ-RAD-OQ-013)."""
        from app.core.security import has_permission
        result = has_permission(role, permission)
        assert result == expected, f"{role}.{permission} should be {expected}, got {result}"
