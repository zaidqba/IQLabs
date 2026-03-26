"""
Unit tests for core/security.py — JWT creation/decoding and RBAC.
No DB or network calls.

Requirement: IQ-RAD-REQ-009 (Authentication & Authorization)
21 CFR Part 11 §11.300 — controls for identification codes/passwords.
"""
import pytest
import time
from unittest.mock import patch

from app.core.security import (
    compute_signature_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    has_permission,
    ROLE_PERMISSIONS,
)
from app.core.exceptions import AuthenticationError


# ──────────────────────────── Permission matrix tests ─────────────────────────

def test_admin_has_all_permissions():
    """ADMIN role has wildcard access to all permissions."""
    assert has_permission("ADMIN", "read:alarms") is True
    assert has_permission("ADMIN", "sign:thresholds") is True
    assert has_permission("ADMIN", "write:reports") is True


def test_viewer_read_only():
    """VIEWER can read but cannot write or sign."""
    assert has_permission("VIEWER", "read:alarms") is True
    assert has_permission("VIEWER", "sign:thresholds") is False
    assert has_permission("VIEWER", "write:reports") is False


def test_operator_can_sign_alarms():
    """OPERATOR can sign alarm acknowledgements."""
    assert has_permission("OPERATOR", "sign:alarms") is True


def test_operator_cannot_access_developer_data():
    """OPERATOR cannot read raw ingestion data (developer-only)."""
    assert has_permission("OPERATOR", "read:raw_ingestion") is False


def test_developer_can_read_raw_ingestion():
    """DEVELOPER can access raw_ingestion_log for debugging."""
    assert has_permission("DEVELOPER", "read:raw_ingestion") is True


def test_emissions_calibration_write():
    """EMISSIONS role can write calibration records."""
    assert has_permission("EMISSIONS", "write:calibration") is True


def test_unknown_role_denied():
    """Unknown role has no permissions."""
    assert has_permission("UNKNOWN_ROLE", "read:alarms") is False


# ──────────────────────────── JWT token tests ──────────────────────────────────

@patch("app.core.security.settings")
def test_create_and_decode_access_token(mock_settings):
    mock_settings.jwt_secret = "test-secret-iq-rad-unit-test-32chars"
    mock_settings.jwt_algorithm = "HS256"
    mock_settings.access_token_expire_minutes = 15

    token, session_id = create_access_token(user_id=42, username="testuser", role="OPERATOR")
    assert token
    assert len(session_id) == 36  # UUID format

    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["username"] == "testuser"
    assert payload["role"] == "OPERATOR"
    assert payload["session_id"] == session_id
    assert payload["token_type"] == "access"


@patch("app.core.security.settings")
def test_create_and_decode_refresh_token(mock_settings):
    mock_settings.jwt_secret = "test-secret-iq-rad-unit-test-32chars"
    mock_settings.jwt_algorithm = "HS256"
    mock_settings.refresh_token_expire_hours = 8

    token = create_refresh_token(user_id=42)
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["token_type"] == "refresh"


@patch("app.core.security.settings")
def test_expired_token_raises(mock_settings):
    mock_settings.jwt_secret = "test-secret-iq-rad-unit-test-32chars"
    mock_settings.jwt_algorithm = "HS256"
    mock_settings.access_token_expire_minutes = -1  # Already expired

    token, _ = create_access_token(user_id=1, username="u", role="VIEWER")
    with pytest.raises(AuthenticationError, match="expired"):
        decode_token(token)


@patch("app.core.security.settings")
def test_tampered_token_raises(mock_settings):
    mock_settings.jwt_secret = "test-secret-iq-rad-unit-test-32chars"
    mock_settings.jwt_algorithm = "HS256"
    mock_settings.access_token_expire_minutes = 15

    token, _ = create_access_token(user_id=1, username="u", role="VIEWER")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(AuthenticationError):
        decode_token(tampered)


# ──────────────────────────── Signature hash tests ────────────────────────────

@patch("app.core.security.settings")
def test_signature_hash_deterministic(mock_settings):
    """Same inputs → same hash."""
    mock_settings.hmac_secret = "test-hmac-secret-32-chars-minimum!"

    h1 = compute_signature_hash(user_id=1, item_type="ALARM_ACK", item_id="42", timestamp="2025-03-12T10:00:00")
    h2 = compute_signature_hash(user_id=1, item_type="ALARM_ACK", item_id="42", timestamp="2025-03-12T10:00:00")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


@patch("app.core.security.settings")
def test_signature_hash_different_inputs(mock_settings):
    """Different inputs → different hashes."""
    mock_settings.hmac_secret = "test-hmac-secret-32-chars-minimum!"

    h1 = compute_signature_hash(user_id=1, item_type="ALARM_ACK", item_id="42", timestamp="2025-03-12T10:00:00")
    h2 = compute_signature_hash(user_id=2, item_type="ALARM_ACK", item_id="42", timestamp="2025-03-12T10:00:00")
    assert h1 != h2
