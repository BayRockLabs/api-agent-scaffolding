"""
Global test fixtures and configuration.
Provides mocks and utilities for all tests.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, MagicMock
from httpx import AsyncClient
from io import BytesIO
import fakeredis

from app.main import app
from app.core.auth import UserContext


# ==================== User Context Fixtures ====================

@pytest.fixture
def mock_user_context() -> UserContext:
    """Standard user context"""
    return UserContext(
        user_id="test_user_123",
        email="test@example.com",
        role="analyst",
    )


@pytest.fixture
def mock_admin_context() -> UserContext:
    """Admin user context"""
    return UserContext(
        user_id="admin_456",
        email="admin@example.com",
        role="admin",
    )


@pytest.fixture
def mock_sales_context() -> UserContext:
    """Sales rep user context"""
    return UserContext(
        user_id="sales_789",
        email="sales@example.com",
        role="sales_rep",
    )


# ==================== API Client Fixtures ====================

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(
    async_client: AsyncClient,
    mock_user_context: UserContext,
) -> AsyncClient:
    """Authenticated async client with user headers"""
    async_client.headers.update(
        {
            "X-User-ID": mock_user_context.user_id,
            "X-User-Email": mock_user_context.email,
            "X-User-Role": mock_user_context.role or "",
        }
    )
    return async_client


# ==================== Database Mocks ====================

@pytest.fixture
def mock_snowflake_engine():
    """Mock Snowflake engine"""
    mock = MagicMock()
    mock.execute_query = AsyncMock(
        return_value=[
            {"id": 1, "name": "Test1", "value": 100},
            {"id": 2, "name": "Test2", "value": 200},
        ]
    )
    mock.execute_query_one = AsyncMock(
        return_value={"id": 1, "name": "Test1", "value": 100}
    )
    mock.test_connection = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_redis_client():
    """Mock Redis client using fakeredis"""
    return fakeredis.FakeRedis()


# ==================== S3 Mocks ====================

@pytest.fixture
def mock_s3_client():
    """Mock S3 client"""
    mock = MagicMock()
    mock.upload_file = AsyncMock(
        return_value={
            "object_key": "test_user_123/test_file.txt",
            "size": 1024,
            "etag": "abc123",
            "content_type": "text/plain",
            "url": "https://s3.test.com/bucket/test_user_123/test_file.txt",
        }
    )
    mock.download_file = AsyncMock(return_value=BytesIO(b"test data"))
    mock.list_files = AsyncMock(
        return_value=[
            {
                "key": "test_user_123/file1.txt",
                "size": 1024,
                "last_modified": "2024-01-01T00:00:00",
                "etag": "abc123",
            }
        ]
    )
    mock.delete_file = AsyncMock(return_value=True)
    mock.generate_presigned_url = AsyncMock(return_value="https://presigned.url")
    mock.file_exists = AsyncMock(return_value=True)
    return mock


# ==================== LLM Mocks ====================

@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM",
                }
            }
        ]
    }


# ==================== Agent Mocks ====================

@pytest.fixture
def mock_agent_graph():
    """Mock LangGraph agent"""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(
        return_value={
            "messages": [Mock(content="Agent response")],
            "current_step": "end",
            "widget_type": None,
            "widget_data": None,
        }
    )
    mock.astream = AsyncMock()
    return mock


# ==================== Test Data Fixtures ====================

@pytest.fixture
def sample_file_data() -> BytesIO:
    """Sample file content"""
    return BytesIO(b"Sample file content for testing")


@pytest.fixture
def sample_snowflake_data():
    """Sample Snowflake query results"""
    return [
        {
            "account_id": "ACC123",
            "account_name": "Acme Corp",
            "coverage_gap": 25.5,
            "sla_status": "warning",
        },
        {
            "account_id": "ACC456",
            "account_name": "TechCo",
            "coverage_gap": 10.2,
            "sla_status": "healthy",
        },
    ]


@pytest.fixture
def sample_widget_data():
    """Sample widget data"""
    return {
        "type": "table",
        "title": "Test Table",
        "columns": ["Col1", "Col2"],
        "rows": [["A", "B"], ["C", "D"]],
    }


# ==================== Cleanup ====================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    yield
    # Cleanup code if needed
