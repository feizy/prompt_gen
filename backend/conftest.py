"""
Pytest configuration and fixtures
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from httpx import AsyncClient

from src.main import app
from src.database.connection import Base, get_db_session
from src.core.config import get_settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = MagicMock()
    settings.DATABASE_URL = TEST_DATABASE_URL
    GLM_API_KEY = "test_api_key"
    settings.SECRET_KEY = "test_secret_key"
    settings.DEBUG = True
    settings.LOG_LEVEL = "info"
    settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
    return settings

@pytest_asyncio.fixture
async def test_client(test_db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database dependency override"""
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_glm_api():
    """Mock GLM API for testing"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = {
        "choices": [{
            "message": {
                "content": "Test response from GLM API"
            }
        }]
    }
    return mock_client

@pytest.fixture
def sample_user_input():
    """Sample user input for testing"""
    return "I want to create a chatbot for customer service"

@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "user_input": "I want to create a chatbot for customer service",
        "status": "active",
        "final_prompt": None,
        "created_at": "2025-11-03T10:00:00Z",
        "updated_at": "2025-11-03T10:00:00Z",
        "iteration_count": 0,
        "user_intervention_count": 0,
        "max_interventions": 3,
        "waiting_for_user_since": None,
        "current_question_id": None,
        "metadata": {}
    }

@pytest.fixture
def sample_agent_message():
    """Sample agent message for testing"""
    return {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "session_id": "123e4567-e89b-12d3-a456-426614174000",
        "agent_type": "product_manager",
        "message_content": "I'll analyze your requirement and create a detailed product specification.",
        "message_type": "requirement",
        "sequence_number": 1,
        "parent_message_id": None,
        "created_at": "2025-11-03T10:01:00Z",
        "processing_time_ms": 1500,
        "metadata": {}
    }

# Test markers
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "contract: mark test as a contract test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "tdd: mark test as test-driven development test"
    )

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables"""
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("GLM_API_KEY", "test_api_key")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "info")