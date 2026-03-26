"""
Integration tests for immutability triggers.
Verifies that DDL triggers prevent UPDATE/DELETE on immutable tables.

These tests require a live SQL Server connection with the schema applied.
Run with: pytest tests/integration/test_immutability.py -m integration

Requirement: IQ-RAD-REQ-001 (Data Immutability)
21 CFR Part 11 §11.10(e) — audit trail records must be unalterable.
"""
import pytest
import os

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_engine():
    """SQLAlchemy sync engine for trigger tests (triggers need DDL-level testing)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")

    from sqlalchemy import create_engine
    engine = create_engine(url.replace("+aioodbc", "").replace("+pyodbc", ""), echo=False)
    yield engine
    engine.dispose()


def test_raw_ingestion_log_immutable(db_engine):
    """Attempt UPDATE on raw_ingestion_log → exception raised by trigger."""
    from sqlalchemy import text, exc

    with db_engine.connect() as conn:
        with pytest.raises(exc.DBAPIError):
            conn.execute(text(
                "UPDATE raw_ingestion_log SET device_id = 99 WHERE 1=0"
            ))


def test_audit_trail_immutable(db_engine):
    """Attempt DELETE on audit_trail → exception raised by trigger."""
    from sqlalchemy import text, exc

    with db_engine.connect() as conn:
        with pytest.raises(exc.DBAPIError):
            conn.execute(text(
                "DELETE FROM audit_trail WHERE 1=0"
            ))


def test_normalized_readings_immutable(db_engine):
    """Attempt UPDATE on normalized_readings → exception."""
    from sqlalchemy import text, exc

    with db_engine.connect() as conn:
        with pytest.raises(exc.DBAPIError):
            conn.execute(text(
                "UPDATE normalized_readings SET normalized_value = 0 WHERE 1=0"
            ))


def test_alarm_history_immutable(db_engine):
    """Attempt DELETE on alarm_history → exception."""
    from sqlalchemy import text, exc

    with db_engine.connect() as conn:
        with pytest.raises(exc.DBAPIError):
            conn.execute(text(
                "DELETE FROM alarm_history WHERE 1=0"
            ))


def test_threshold_change_log_immutable(db_engine):
    """Attempt UPDATE on threshold_change_log → exception."""
    from sqlalchemy import text, exc

    with db_engine.connect() as conn:
        with pytest.raises(exc.DBAPIError):
            conn.execute(text(
                "UPDATE threshold_change_log SET change_reason = 'tampered' WHERE 1=0"
            ))
