"""Agent endpoint tests."""
import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_create_agent(async_client, async_session):
    payload = {
        "token": "emb_test123",
        "endpoint": "https://talk-api.jeffmeridian.com",
        "environment": "local",
        "js_source": "https://talk.jeffmeridian.com/embed/dograh-widget.js",
        "script": "dograh-widget",
        "category": "test",
        "language": "en",
        "name": "test agent",
        "finger_hole": "assets/test.png",
        "scrollable_agent_card": "assets/test.png",
        "info": "A test agent",
        "is_active": True,
    }
    response = await async_client.post("/api/agents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test agent"
    assert data["is_active"] is True
    assert data["token"] == "emb_test123"


@pytest.mark.asyncio
async def test_list_agents(async_client, async_session, sample_agent):
    response = await async_client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_agent(async_client, async_session, sample_agent):
    response = await async_client.get(f"/api/agents/{sample_agent.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_agent.id


@pytest.mark.asyncio
async def test_update_agent(async_client, async_session, sample_agent):
    response = await async_client.patch(
        f"/api/agents/{sample_agent.id}",
        json={"name": "updated agent", "is_active": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated agent"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_agent_status(async_client, async_session, sample_agent):
    response = await async_client.patch(
        f"/api/agents/{sample_agent.id}/status",
        json={"is_active": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_agent(async_client, async_session, sample_agent):
    response = await async_client.post(f"/api/agents/{sample_agent.id}/duplicate")
    assert response.status_code == 201
    data = response.json()
    assert "(copy)" in data["name"]


@pytest.mark.asyncio
async def test_delete_agent(async_client, async_session, sample_agent):
    response = await async_client.delete(f"/api/agents/{sample_agent.id}")
    assert response.status_code == 204
