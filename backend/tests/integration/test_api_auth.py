"""
Integration tests for authentication endpoints.
Uses httpx AsyncClient against the FastAPI app with a test DB.
Requires: TEST_DATABASE_URL environment variable pointing to a test SQL Server.

Requirement: IQ-RAD-REQ-009 (Authentication)
21 CFR Part 11 §11.300 — electronic signature security controls.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# These tests are marked integration and skipped unless TEST_DATABASE_URL is set.
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def app():
    """Import app only when running integration tests."""
    import os
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")
    from app.main import app
    return app


@pytest.mark.asyncio
async def test_login_valid_credentials(app):
    """Valid credentials → 200 with access_token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPassword123!"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(app):
    """Wrong password → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "WrongPassword"
        })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(app):
    """Non-existent user → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={
            "username": "does_not_exist",
            "password": "Password123!"
        })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(app):
    """Accessing a protected endpoint without JWT → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/alarms/active")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_user_info(app):
    """Authenticated /auth/me returns current user info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPassword123!"
        })
        token = login.json()["access_token"]
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_logout_invalidates_token(app):
    """After logout, token is blacklisted and further requests → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPassword123!"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 401
