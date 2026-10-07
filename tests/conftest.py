"""Pytest configuration and fixtures."""
import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["LOGIN_USERNAME"] = "test-user"
os.environ["LOGIN_PASSWORD"] = "test-password"
os.environ["SESSION_SECRET"] = "test-session-secret-that-is-long-enough"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["AGENTS_API_USERNAME"] = "agents-reader-test"
os.environ["AGENTS_API_PASSWORD"] = "agents-reader-test-password"

from app.config import Settings, get_settings
from app.database import Base, get_async_db
from app.main import app
from app.models.setting import Setting
from app.models.agent import Agent
from app.schemas.agent import AgentCreate
from app.services.websocket import WebSocketManager

fake = Faker()


# Override settings for testing
class TestSettings(Settings):
    app_env: str = "test"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./test.db"
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 5687
    webhook_path: str = "/webhook/agents"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Test settings instance."""
    return TestSettings()


@pytest.fixture(scope="function")
def sync_engine():
    """Create synchronous test engine with SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create synchronous test session."""
    SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create asynchronous test engine with SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create asynchronous test session."""
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="function")
def override_get_db(sync_session):
    """Override database dependency for sync tests."""
    def _get_db():
        try:
            yield sync_session
        finally:
            pass

    app.dependency_overrides[get_async_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def override_get_async_db(async_session):
    """Override database dependency for async tests."""
    async def _get_db():
        yield async_session

    app.dependency_overrides[get_async_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create test client."""
    test_client = TestClient(app)
    test_client.post("/auth/login", json={"username": "test-user", "password": "test-password"})
    return test_client


@pytest.fixture(scope="function")
async def async_client(override_get_async_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/auth/login", json={"username": "test-user", "password": "test-password"})
        yield client


@pytest.fixture(scope="function")
def websocket_manager() -> WebSocketManager:
    """Create WebSocket manager instance."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    from unittest.mock import AsyncMock
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.fixture(scope="function")
async def sample_settings(async_session) -> list[Setting]:
    """Create sample settings."""
    settings_data = [
        {"key": "webhook_host", "value": "0.0.0.0", "description": "IP address to bind webhook server"},
        {"key": "webhook_port", "value": "5687", "description": "Port for webhook server"},
        {"key": "webhook_path", "value": "/webhook/agents", "description": "Webhook endpoint path for agents"},
    ]
    settings = [Setting(**data) for data in settings_data]
    async_session.add_all(settings)
    await async_session.commit()
    for s in settings:
        await async_session.refresh(s)
    return settings


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "webhook: Webhook endpoint tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")
    config.addinivalue_line("markers", "slow: Slow tests")


@pytest.fixture(scope="function")
async def sample_agent(async_session) -> Agent:
    agent = Agent(
        token="emb_testtoken123",
        endpoint="https://talk-api.jeffmeridian.com",
        environment="local",
        js_source="https://talk.jeffmeridian.com/embed/dograh-widget.js",
        script="dograh-widget",
        category="test",
        language="en",
        name="test agent",
        finger_hole="assets/test.png",
        scrollable_agent_card="assets/test.png",
        info="A test agent for testing",
        is_active=True,
    )
    async_session.add(agent)
    await async_session.commit()
    await async_session.refresh(agent)
    return agent