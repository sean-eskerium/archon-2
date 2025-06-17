"""Unit test specific fixtures and configuration."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, Optional


# =============================================================================
# Autouse fixtures for unit test isolation
# =============================================================================

@pytest.fixture(autouse=True)
def mock_database_isolation(monkeypatch):
    """Prevent any database access in unit tests."""
    def db_error(*args, **kwargs):
        raise RuntimeError(
            "Database access attempted in unit test! "
            "Unit tests should not access the database. "
            "Use mocks or mark test with @pytest.mark.integration"
        )
    
    # Block Supabase client creation
    monkeypatch.setattr("supabase.create_client", db_error)
    monkeypatch.setattr("supabase.Client", db_error)
    
    # Block direct database connections
    monkeypatch.setattr("asyncpg.connect", db_error)
    monkeypatch.setattr("psycopg2.connect", db_error)
    monkeypatch.setattr("sqlalchemy.create_engine", db_error)


@pytest.fixture(autouse=True)
def mock_external_apis(monkeypatch):
    """Mock all external API calls in unit tests."""
    # Mock OpenAI
    mock_openai = Mock()
    mock_openai.chat.completions.create = AsyncMock()
    mock_openai.embeddings.create = AsyncMock(
        return_value=Mock(data=[Mock(embedding=[0.1] * 1536)])
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: mock_openai)
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_openai)
    
    # Mock Anthropic
    mock_anthropic = Mock()
    mock_anthropic.messages.create = AsyncMock()
    monkeypatch.setattr("anthropic.Anthropic", lambda **kwargs: mock_anthropic)
    monkeypatch.setattr("anthropic.AsyncAnthropic", lambda **kwargs: mock_anthropic)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Make sleep instant in unit tests."""
    monkeypatch.setattr("time.sleep", lambda x: None)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())


# =============================================================================
# Mock service fixtures
# =============================================================================

@pytest.fixture
def mock_project_service():
    """Mock project service for unit tests."""
    service = Mock()
    service.create_project = AsyncMock(return_value={"id": "proj_123"})
    service.get_project = AsyncMock(return_value={"id": "proj_123"})
    service.update_project = AsyncMock(return_value={"id": "proj_123"})
    service.delete_project = AsyncMock()
    service.list_projects = AsyncMock(return_value=[])
    service.search_projects = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_task_service():
    """Mock task service for unit tests."""
    service = Mock()
    service.create_task = AsyncMock(return_value={"id": "task_123"})
    service.get_task = AsyncMock(return_value={"id": "task_123"})
    service.update_task = AsyncMock(return_value={"id": "task_123"})
    service.delete_task = AsyncMock()
    service.list_tasks = AsyncMock(return_value=[])
    service.update_task_status = AsyncMock()
    service.get_subtasks = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_document_service():
    """Mock document service for unit tests."""
    service = Mock()
    service.create_document = AsyncMock(return_value={"id": "doc_123"})
    service.get_document = AsyncMock(return_value={"id": "doc_123"})
    service.update_document = AsyncMock(return_value={"id": "doc_123"})
    service.delete_document = AsyncMock()
    service.list_documents = AsyncMock(return_value=[])
    service.get_document_content = AsyncMock(return_value={})
    service.update_document_content = AsyncMock()
    return service


@pytest.fixture
def mock_credential_service():
    """Mock credential service for unit tests."""
    service = Mock()
    service.get_credential = AsyncMock(return_value="test-value")
    service.set_credential = AsyncMock()
    service.delete_credential = AsyncMock()
    service.list_credentials = AsyncMock(return_value=[])
    service.encrypt_value = Mock(return_value="encrypted")
    service.decrypt_value = Mock(return_value="decrypted")
    return service


@pytest.fixture
def mock_mcp_client_service():
    """Mock MCP client service for unit tests."""
    service = Mock()
    service.connect = AsyncMock()
    service.disconnect = AsyncMock()
    service.execute_tool = AsyncMock(return_value={})
    service.list_tools = AsyncMock(return_value=[])
    service.get_tool_schema = AsyncMock(return_value={})
    return service


@pytest.fixture
def mock_search_service():
    """Mock search service for unit tests."""
    service = Mock()
    service.search = AsyncMock(return_value=[])
    service.hybrid_search = AsyncMock(return_value=[])
    service.rerank_results = AsyncMock(return_value=[])
    service.get_similar_documents = AsyncMock(return_value=[])
    return service


# =============================================================================
# Mock agent fixtures
# =============================================================================

@pytest.fixture
def mock_base_agent():
    """Mock base agent for unit tests."""
    agent = Mock()
    agent.process = AsyncMock(return_value="response")
    agent.stream = AsyncMock()
    agent.reset = Mock()
    return agent


@pytest.fixture
def mock_rag_agent():
    """Mock RAG agent for unit tests."""
    agent = Mock()
    agent.query = AsyncMock(return_value={"answer": "test", "sources": []})
    agent.search_and_answer = AsyncMock(return_value={"answer": "test", "sources": []})
    agent.reset_context = Mock()
    return agent


# =============================================================================
# WebSocket and SSE mocks
# =============================================================================

@pytest.fixture
def mock_websocket():
    """Mock WebSocket for unit tests."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "test"}')
    ws.receive_json = AsyncMock(return_value={"type": "test"})
    ws.close = AsyncMock()
    ws.client_state = Mock()
    return ws


@pytest.fixture
def mock_sse_response():
    """Mock SSE response for unit tests."""
    class MockSSE:
        def __init__(self):
            self.events = []
        
        async def send(self, data: str, event: Optional[str] = None):
            self.events.append({"data": data, "event": event})
        
        def get_events(self):
            return self.events
    
    return MockSSE()


# =============================================================================
# Test data isolation
# =============================================================================

@pytest.fixture
def isolated_test_data(tmp_path):
    """Provide isolated test data directory."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    
    # Create some test files
    (test_dir / "test.txt").write_text("test content")
    (test_dir / "test.json").write_text('{"test": true}')
    
    return test_dir


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for unit tests."""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "SUPABASE_URL": "http://test.supabase.co",
        "SUPABASE_KEY": "test-key",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


# =============================================================================
# Performance helpers for unit tests
# =============================================================================

@pytest.fixture
def assert_fast():
    """Helper to assert that code executes quickly in unit tests."""
    import time
    
    class FastAssertion:
        def __init__(self, max_seconds: float = 0.1):
            self.max_seconds = max_seconds
            self.start_time: Optional[float] = None
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.start_time is not None:
                duration = time.perf_counter() - self.start_time
                if duration > self.max_seconds:
                    pytest.fail(
                        f"Unit test took too long: {duration:.3f}s "
                        f"(max allowed: {self.max_seconds}s)"
                    )
    
    return FastAssertion


# =============================================================================
# Mock factory fixtures
# =============================================================================

@pytest.fixture
def make_mock_response():
    """Factory for creating mock HTTP responses."""
    def _make_response(
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        response = Mock()
        response.status_code = status_code
        response.json = Mock(return_value=json_data or {})
        response.text = text or ""
        response.headers = headers or {}
        response.raise_for_status = Mock()
        
        if status_code >= 400:
            response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        
        return response
    
    return _make_response


@pytest.fixture
def make_mock_event():
    """Factory for creating mock events."""
    def _make_event(
        event_type: str = "test",
        data: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None
    ):
        return {
            "type": event_type,
            "data": data or {},
            "id": id or f"evt_{event_type}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    return _make_event