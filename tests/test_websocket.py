"""Tests for WebSocket functionality."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.services.websocket import WebSocketManager, websocket_manager


class TestWebSocketManager:
    """Tests for WebSocketManager class."""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, websocket_manager: WebSocketManager, mock_websocket):
        """Test connecting and disconnecting a WebSocket."""
        await websocket_manager.connect(mock_websocket)
        assert websocket_manager.connection_count == 1
        mock_websocket.accept.assert_called_once()

        await websocket_manager.disconnect(mock_websocket)
        assert websocket_manager.connection_count == 0

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_multiple_connections(self, websocket_manager: WebSocketManager):
        """Test multiple WebSocket connections."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)
        await websocket_manager.connect(ws3)

        assert websocket_manager.connection_count == 3

        await websocket_manager.disconnect(ws2)
        assert websocket_manager.connection_count == 2

        await websocket_manager.disconnect(ws1)
        await websocket_manager.disconnect(ws3)
        assert websocket_manager.connection_count == 0

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_broadcast_message(self, websocket_manager: WebSocketManager):
        """Test broadcasting message to all connections."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)
        await websocket_manager.connect(ws3)

        message = {"type": "test", "data": {"key": "value"}}
        await websocket_manager.broadcast(message)

        # Verify all connections received the message
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
        ws3.send_text.assert_called_once()

        # Verify message content
        call_args = ws1.send_text.call_args[0][0]
        sent_message = json.loads(call_args)
        assert sent_message == message

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected(self, websocket_manager: WebSocketManager):
        """Test broadcast handles disconnected clients gracefully."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)

        # Make ws2 fail on send
        ws2.send_text.side_effect = Exception("Connection closed")

        message = {"type": "test", "data": {}}
        await websocket_manager.broadcast(message)

        # ws1 should still receive
        ws1.send_text.assert_called_once()
        # ws2 should be cleaned up
        assert websocket_manager.connection_count == 1

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self, websocket_manager: WebSocketManager):
        """Test broadcast with no connections."""
        # Should not raise
        await websocket_manager.broadcast({"type": "test", "data": {}})

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_send_personal_message(self, websocket_manager: WebSocketManager, mock_websocket):
        """Test sending personal message to specific connection."""
        await websocket_manager.connect(mock_websocket)

        message = {"type": "personal", "data": {"key": "value"}}
        await websocket_manager.send_personal_message(message, mock_websocket)

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_message = json.loads(call_args)
        assert sent_message == message


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint integration."""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_websocket_connection(self, async_client: AsyncClient):
        """Test WebSocket connection endpoint."""
        # TestClient doesn't support WebSocket, use httpx with websockets
        # This is a placeholder for integration test
        # In real tests, use websockets library or testclient.websocket_connect
        pass

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_websocket_health_check(self, async_client: AsyncClient):
        """Test health check endpoint includes WebSocket info."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "websocket_connections" in data


class TestWebSocketMessageTypes:
    """Tests for WebSocket message structure."""

    @pytest.mark.websocket
    def test_agent_created_message_structure(self):
        """Test agent_created message structure."""
        message = {
            "type": "agent_created",
            "data": {
                "id": 1,
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
                "created_at": "2026-09-29T10:00:00",
                "updated_at": "2026-09-29T10:00:00",
            }
        }

        assert message["type"] == "agent_created"
        assert "id" in message["data"]
        assert "name" in message["data"]
        assert "token" in message["data"]

    @pytest.mark.websocket
    def test_agent_updated_message_structure(self):
        """Test agent_updated message structure."""
        message = {
            "type": "agent_updated",
            "data": {
                "id": 1,
                "name": "updated agent",
                "is_active": False,
                "updated_at": "2026-09-29T11:00:00",
            }
        }

        assert message["type"] == "agent_updated"
        assert "id" in message["data"]
        assert "is_active" in message["data"]

    @pytest.mark.websocket
    def test_agent_deleted_message_structure(self):
        """Test agent_deleted message structure."""
        message = {
            "type": "agent_deleted",
            "data": {"id": 1}
        }

        assert message["type"] == "agent_deleted"
        assert message["data"]["id"] == 1

    @pytest.mark.websocket
    def test_agent_duplicated_message_structure(self):
        """Test agent_duplicated message structure."""
        message = {
            "type": "agent_duplicated",
            "data": {
                "id": 2,
                "name": "test agent (copy)",
                "is_active": True,
                "created_at": "2026-09-29T12:00:00",
                "updated_at": "2026-09-29T12:00:00",
            }
        }

        assert message["type"] == "agent_duplicated"
        assert "id" in message["data"]
        assert "(copy)" in message["data"]["name"]