"""Tests for settings API endpoints."""
import pytest
from httpx import AsyncClient


class TestSettingsAPI:
    """Tests for /api/settings endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_settings_list(self, async_client: AsyncClient, sample_settings):
        """Test getting all settings."""
        response = await async_client.get("/api/settings")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3

        keys = {s["key"] for s in data}
        assert keys == {"webhook_host", "webhook_port", "webhook_path"}

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_setting_by_key(self, async_client: AsyncClient, sample_settings):
        """Test getting a specific setting by key."""
        response = await async_client.get("/api/settings/webhook_host")

        assert response.status_code == 200
        data = response.json()

        assert data["key"] == "webhook_host"
        assert data["value"] == "0.0.0.0"
        assert data["description"] == "IP address to bind webhook server"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_nonexistent_setting(self, async_client: AsyncClient):
        """Test getting a non-existent setting returns 404."""
        response = await async_client.get("/api/settings/nonexistent")

        assert response.status_code == 404

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_existing_setting(self, async_client: AsyncClient, sample_settings):
        """Test updating an existing setting."""
        response = await async_client.put(
            "/api/settings/webhook_port",
            json={"value": "8080", "description": "Updated port"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["key"] == "webhook_port"
        assert data["value"] == "8080"
        assert data["description"] == "Updated port"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_new_setting(self, async_client: AsyncClient):
        """Test creating a new setting."""
        response = await async_client.put(
            "/api/settings/custom_setting",
            json={"value": "custom_value", "description": "Custom setting"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["key"] == "custom_setting"
        assert data["value"] == "custom_value"
        assert data["description"] == "Custom setting"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_setting_without_description(self, async_client: AsyncClient, sample_settings):
        """Test updating setting without providing description."""
        response = await async_client.put(
            "/api/settings/webhook_host",
            json={"value": "127.0.0.1"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["value"] == "127.0.0.1"
        assert data["description"] == "IP address to bind webhook server"  # Unchanged

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_webhook_url(self, async_client: AsyncClient, sample_settings):
        """Test getting the full webhook URL."""
        response = await async_client.get("/api/settings/webhook-url")

        assert response.status_code == 200
        data = response.json()

        assert data["webhook_url"] == "http://localhost:5687/webhook/agents"
        assert data["host"] == "0.0.0.0"
        assert data["port"] == 5687
        assert data["path"] == "/webhook/agents"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_webhook_url_with_custom_host(self, async_client: AsyncClient, sample_settings):
        """Test getting webhook URL with custom host."""
        # Update host
        await async_client.put(
            "/api/settings/webhook_host",
            json={"value": "100.66.60.70"},
        )

        response = await async_client.get("/api/settings/webhook-url")

        assert response.status_code == 200
        data = response.json()

        assert data["webhook_url"] == "http://100.66.60.70:5687/webhook/agents"
        assert data["host"] == "100.66.60.70"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_initialize_defaults(self, async_client: AsyncClient):
        """Test initializing default settings."""
        response = await async_client.post("/api/settings/initialize-defaults")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3

        keys = {s["key"] for s in data}
        assert keys == {"webhook_host", "webhook_port", "webhook_path"}