import sys, os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime
import asyncio
from typing import Dict, Any, AsyncGenerator

# Add src folder to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Import the FastAPI application from the current codebase
# Use the package path so relative imports inside the module work
from src.main import app

# Set test environment
os.environ["TESTING"] = "true"
os.environ["SUPABASE_URL"] = "http://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"

@pytest_asyncio.fixture
async def async_client():
    """Async client for testing FastAPI endpoints"""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

@pytest.fixture 
def sync_client():
    """Sync client for testing non-async endpoints"""
    from fastapi.testclient import TestClient
    with TestClient(app) as tc:
        yield tc

# Database Fixtures
@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for database operations"""
    mock = MagicMock()
    
    # Mock table methods
    mock.table = MagicMock(return_value=mock)
    mock.select = MagicMock(return_value=mock)
    mock.insert = MagicMock(return_value=mock)
    mock.update = MagicMock(return_value=mock)
    mock.delete = MagicMock(return_value=mock)
    mock.eq = MagicMock(return_value=mock)
    mock.neq = MagicMock(return_value=mock)
    mock.order = MagicMock(return_value=mock)
    mock.limit = MagicMock(return_value=mock)
    mock.single = MagicMock(return_value=mock)
    
    # Default execute response
    mock.execute = MagicMock(return_value=MagicMock(data=[], count=0))
    
    return mock

@pytest.fixture
def mock_db_session():
    """Mock database session for async operations"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

# Service Fixtures
@pytest.fixture
def mock_credential_service():
    """Mock credential service"""
    service = AsyncMock()
    service.load_credentials = AsyncMock()
    service.get_credential = AsyncMock(return_value="test-value")
    service.set_credential = AsyncMock()
    service.is_initialized = True
    return service

@pytest.fixture
def mock_project_service():
    """Mock project service"""
    service = AsyncMock()
    service.create_project = AsyncMock()
    service.get_project = AsyncMock()
    service.update_project = AsyncMock()
    service.delete_project = AsyncMock()
    service.list_projects = AsyncMock(return_value=[])
    return service

@pytest.fixture
def mock_task_service():
    """Mock task service"""
    service = AsyncMock()
    service.create_task = AsyncMock()
    service.get_task = AsyncMock()
    service.update_task = AsyncMock()
    service.delete_task = AsyncMock()
    service.list_tasks = AsyncMock(return_value=[])
    return service

@pytest.fixture
def mock_mcp_session_manager():
    """Mock MCP session manager"""
    manager = AsyncMock()
    manager.create_session = AsyncMock(return_value="test-session-id")
    manager.get_session = AsyncMock()
    manager.execute_tool = AsyncMock()
    manager.close_session = AsyncMock()
    return manager

# WebSocket Fixtures
@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing WebSocket endpoints"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "test"}')
    ws.receive_json = AsyncMock(return_value={"type": "test"})
    ws.close = AsyncMock()
    return ws

# Sample Data Fixtures
@pytest.fixture
def sample_project():
    """Sample project data for testing"""
    return {
        "id": "test-project-id",
        "title": "Test Project",
        "description": "Test project description",
        "status": "active",
        "pinned": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {"test": True}
    }

@pytest.fixture
def sample_task():
    """Sample task data for testing"""
    return {
        "id": "test-task-id",
        "project_id": "test-project-id",
        "title": "Test Task",
        "description": "Test task description",
        "status": "todo",
        "priority": 1,
        "assignee": "Archon",
        "parent_id": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {"test": True}
    }

@pytest.fixture
def sample_document():
    """Sample document data for testing"""
    return {
        "id": "test-doc-id",
        "project_id": "test-project-id",
        "title": "Test Document",
        "content": "Test document content",
        "type": "markdown",
        "metadata": {"test": True},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

# Environment Fixtures
@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables for each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def test_env_vars():
    """Set up test environment variables"""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "SUPABASE_URL": "http://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key"
    }
    for key, value in env_vars.items():
        os.environ[key] = value
    return env_vars

# Async Utilities
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock External Services
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = Mock()
    client.chat.completions.create = AsyncMock()
    client.embeddings.create = AsyncMock()
    return client

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    client = Mock()
    client.messages.create = AsyncMock()
    return client

# Cleanup Fixtures
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Add any cleanup logic here
    pass
