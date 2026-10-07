"""Dashboard authentication tests."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, settings


@pytest.mark.asyncio
async def test_dashboard_requires_valid_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_page = await client.get("/")
        assert login_page.status_code == 200
        assert "Agents Hotline Login" in login_page.text
        assert (await client.get("/static/index.html")).status_code == 303
        assert (await client.get("/api/agents")).status_code == 401

        wrong_login = await client.post(
            "/auth/login",
            json={"username": "wrong-user", "password": "wrong-password"},
        )
        assert wrong_login.status_code == 401
        assert (await client.get("/")).status_code == 200
        assert "Agents Hotline Login" in (await client.get("/")).text

        valid_login = await client.post(
            "/auth/login",
            json={"username": "test-user", "password": "test-password"},
        )
        assert valid_login.status_code == 200
        assert "agents-table" in (await client.get("/")).text

        assert (await client.post("/auth/logout")).status_code == 200
        assert (await client.get("/api/agents")).status_code == 401
        assert (await client.get("/static/index.html")).status_code == 303


@pytest.mark.asyncio
async def test_login_fails_closed_without_configuration(monkeypatch):
    monkeypatch.setattr(settings, "login_username", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"username": "test-user", "password": "test-password"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Login credentials are not configured"


@pytest.mark.asyncio
async def test_api_only_credentials_are_limited_to_active_agents(async_client, sample_agent):
    async_client.cookies.clear()

    response = await async_client.get(
        "/api/agents?is_active=true",
        auth=("agents-reader-test", "agents-reader-test-password"),
    )
    assert response.status_code == 200
    assert all(agent["is_active"] for agent in response.json()["items"])

    assert (await async_client.get("/")).status_code == 200
    assert "Agents Hotline Login" in (await async_client.get("/")).text
    assert (await async_client.get("/static/index.html")).status_code == 303
    assert (await async_client.get("/api/agents", auth=("agents-reader-test", "agents-reader-test-password"))).status_code == 401
    assert (await async_client.get("/api/agents?is_active=false", auth=("agents-reader-test", "agents-reader-test-password"))).status_code == 401
    assert (await async_client.get("/api/settings", auth=("agents-reader-test", "agents-reader-test-password"))).status_code == 401

    dashboard_login = await async_client.post(
        "/auth/login",
        json={"username": "agents-reader-test", "password": "agents-reader-test-password"},
    )
    assert dashboard_login.status_code == 401