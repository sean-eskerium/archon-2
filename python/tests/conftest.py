"""Root conftest.py - Shared fixtures and configuration for all tests."""

import asyncio
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import fixtures from fixtures package
from tests.fixtures.mock_data import *
from tests.fixtures.test_helpers import *

# Suppress warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


# =============================================================================
# Session-scoped fixtures (shared across all tests)
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app_config() -> Dict[str, Any]:
    """Session-wide application configuration."""
    return {
        "testing": True,
        "debug": False,
        "api_version": "v1",
        "max_retries": 3,
        "timeout": 30,
        "base_url": "http://localhost:8000",
    }


@pytest.fixture(scope="session")
def embedding_model() -> str:
    """Session-scoped embedding model name."""
    return "text-embedding-ada-002"


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Directory containing test data files."""
    return Path(__file__).parent / "test_data"


# =============================================================================
# Module-scoped fixtures (shared within a test module)
# =============================================================================

@pytest.fixture(scope="module")
def mock_openai_client() -> Mock:
    """Module-scoped mock OpenAI client."""
    client = Mock()
    client.embeddings = Mock()
    client.embeddings.create = Mock(return_value=Mock(
        data=[Mock(embedding=[0.1] * 1536)]
    ))
    return client


@pytest.fixture(scope="module")
def mock_supabase_client() -> Mock:
    """Module-scoped mock Supabase client."""
    client = Mock()
    
    # Mock table operations
    table_mock = Mock()
    table_mock.select = Mock(return_value=table_mock)
    table_mock.insert = Mock(return_value=table_mock)
    table_mock.update = Mock(return_value=table_mock)
    table_mock.delete = Mock(return_value=table_mock)
    table_mock.eq = Mock(return_value=table_mock)
    table_mock.execute = Mock(return_value=Mock(data=[]))
    
    client.table = Mock(return_value=table_mock)
    client.rpc = Mock()
    
    return client


# =============================================================================
# Function-scoped fixtures (default scope)
# =============================================================================

@pytest.fixture
def mock_config(app_config: Dict[str, Any]) -> Mock:
    """Mock configuration object."""
    config = Mock()
    for key, value in app_config.items():
        setattr(config, key.upper(), value)
    config.OPENAI_API_KEY = "test-key"
    config.SUPABASE_URL = "http://localhost:54321"
    config.SUPABASE_KEY = "test-key"
    return config


@pytest.fixture
def mock_request() -> Mock:
    """Mock FastAPI request object."""
    request = Mock()
    request.app = Mock()
    request.app.state = Mock()
    request.url = Mock(path="/api/v1/test")
    request.headers = {"Authorization": "Bearer test-token"}
    request.query_params = {}
    return request


# =============================================================================
# Autouse fixtures (automatically applied)
# =============================================================================

@pytest.fixture(autouse=True)
def prevent_network_calls(monkeypatch, request):
    """Prevent accidental network calls in unit tests."""
    # Skip for integration and e2e tests
    if "integration" in request.keywords or "e2e" in request.keywords:
        return
    
    def network_error(*args, **kwargs):
        raise RuntimeError(
            "Network call attempted in unit test! "
            "Use mocks or mark test with @pytest.mark.integration"
        )
    
    # Block common network libraries
    monkeypatch.setattr("requests.get", network_error)
    monkeypatch.setattr("requests.post", network_error)
    monkeypatch.setattr("requests.put", network_error)
    monkeypatch.setattr("requests.delete", network_error)
    monkeypatch.setattr("aiohttp.ClientSession", network_error)
    monkeypatch.setattr("httpx.AsyncClient", network_error)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Import here to avoid circular imports
    from src.services.prompt_service import PromptService
    
    # Reset PromptService singleton
    PromptService._instance = None
    
    yield
    
    # Cleanup after test
    PromptService._instance = None


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Ensure clean environment for each test."""
    # Set test environment
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TESTING", "true")
    
    # Clear any cached environment variables
    test_env_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "DATABASE_URL",
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            monkeypatch.delenv(var, raising=False)


# =============================================================================
# Performance and debugging fixtures
# =============================================================================

@pytest.fixture
def memory_tracker():
    """Track memory usage during test."""
    import tracemalloc
    import gc
    
    gc.collect()
    tracemalloc.start()
    
    yield
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Alert if > 100MB used
    if peak > 100 * 1024 * 1024:
        warnings.warn(
            f"High memory usage detected: {peak / 1024 / 1024:.1f}MB peak",
            ResourceWarning
        )


@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer for performance tests."""
    import time
    
    times = []
    
    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        
        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.duration = self.end - self.start
            times.append(self.duration)
    
    yield Timer
    
    if times:
        avg_time = sum(times) / len(times)
        if avg_time > 1.0:  # Alert if average > 1 second
            warnings.warn(
                f"Slow test detected: {avg_time:.2f}s average",
                UserWarning
            )


# =============================================================================
# Factory fixtures
# =============================================================================

@pytest.fixture
def make_project():
    """Factory fixture for creating project data."""
    created_projects = []
    
    def _make_project(name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        project_id = f"proj_{len(created_projects)}"
        project = {
            "id": project_id,
            "name": name or f"Project {len(created_projects)}",
            "description": kwargs.get("description", "Test project"),
            "metadata": kwargs.get("metadata", {}),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        project.update(kwargs)
        created_projects.append(project)
        return project
    
    yield _make_project
    
    # Cleanup tracking
    if created_projects:
        print(f"Created {len(created_projects)} test projects")


@pytest.fixture
def make_task():
    """Factory fixture for creating task data."""
    created_tasks = []
    
    def _make_task(title: Optional[str] = None, project_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        task_id = f"task_{len(created_tasks)}"
        task = {
            "id": task_id,
            "project_id": project_id or "proj_default",
            "title": title or f"Task {len(created_tasks)}",
            "description": kwargs.get("description", ""),
            "status": kwargs.get("status", "todo"),
            "priority": kwargs.get("priority", "medium"),
            "assignee": kwargs.get("assignee"),
            "due_date": kwargs.get("due_date"),
            "labels": kwargs.get("labels", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        task.update(kwargs)
        created_tasks.append(task)
        return task
    
    yield _make_task
    
    # Cleanup tracking
    if created_tasks:
        print(f"Created {len(created_tasks)} test tasks")


@pytest.fixture
def make_document():
    """Factory fixture for creating document data."""
    created_documents = []
    
    def _make_document(content: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        doc_id = f"doc_{len(created_documents)}"
        document = {
            "id": doc_id,
            "content": content or f"Document content {len(created_documents)}",
            "metadata": kwargs.get("metadata", {}),
            "embeddings": kwargs.get("embeddings"),
            "chunk_index": kwargs.get("chunk_index", 0),
            "created_at": datetime.now().isoformat(),
        }
        document.update(kwargs)
        created_documents.append(document)
        return document
    
    yield _make_document
    
    # Cleanup tracking
    if created_documents:
        print(f"Created {len(created_documents)} test documents")


# =============================================================================
# Async fixtures
# =============================================================================

@pytest_asyncio.fixture
async def async_mock_client() -> AsyncMock:
    """Async mock client for testing."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send = AsyncMock()
    client.receive = AsyncMock(return_value={"type": "test", "data": {}})
    return client


# =============================================================================
# Transport fixtures (parametrized)
# =============================================================================

@pytest.fixture(params=[
    pytest.param({"type": "SSE", "url": "http://localhost:8080/sse"}, id="sse"),
    pytest.param({"type": "WebSocket", "url": "ws://localhost:8080/ws"}, id="websocket"),
])
def transport_config(request) -> Dict[str, str]:
    """Parametrized transport configurations."""
    return request.param


# =============================================================================
# Test data fixtures
# =============================================================================

@pytest.fixture
def sample_messages() -> List[Dict[str, Any]]:
    """Sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you?"},
        {"role": "user", "content": "Tell me about RAG"},
    ]


@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Sample search results for testing."""
    return [
        {
            "content": "RAG combines retrieval and generation",
            "metadata": {"source": "doc1.pdf", "page": 1},
            "score": 0.95,
        },
        {
            "content": "Retrieval Augmented Generation improves accuracy",
            "metadata": {"source": "doc2.pdf", "page": 5},
            "score": 0.87,
        },
    ]


# =============================================================================
# Marker-specific fixtures
# =============================================================================

@pytest.fixture
def requires_openai(monkeypatch):
    """Fixture for tests requiring OpenAI API."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not available")
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))


@pytest.fixture
def requires_supabase(monkeypatch):
    """Fixture for tests requiring Supabase."""
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        pytest.skip("Supabase credentials not available")
    monkeypatch.setenv("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    monkeypatch.setenv("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
