"""Integration test specific fixtures and configuration."""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import Mock
import warnings

# Import real services for integration testing
try:
    from src.services.projects.project_service import ProjectService
    from src.services.projects.task_service import TaskService
    from src.services.projects.document_service import DocumentService
    from src.services.credential_service import CredentialService
    from src.services.mcp_client_service import MCPClientService
    from src.services.mcp_session_manager import MCPSessionManager
    from src.utils import get_supabase_client
except ImportError as e:
    warnings.warn(f"Could not import services for integration tests: {e}")


# =============================================================================
# Database fixtures (module-scoped for efficiency)
# =============================================================================

@pytest.fixture(scope="module")
def test_database_url():
    """Get test database URL from environment."""
    url = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
    if not url:
        pytest.skip("No test database URL available")
    return url


@pytest.fixture(scope="module")
def test_supabase_client():
    """Real Supabase client for integration tests."""
    url = os.getenv("TEST_SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = os.getenv("TEST_SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    
    if not url or not key:
        pytest.skip("Supabase credentials not available for integration tests")
    
    try:
        client = get_supabase_client()
        return client
    except Exception as e:
        pytest.skip(f"Could not create Supabase client: {e}")


@pytest.fixture(scope="function")
async def db_transaction(test_supabase_client):
    """Provide database transaction that rolls back after test."""
    # Note: Supabase doesn't support transactions in the same way
    # We'll use a different approach - track created records and clean them up
    created_records = {
        "projects": [],
        "tasks": [],
        "documents": [],
        "knowledge_sources": [],
    }
    
    original_insert = test_supabase_client.table
    
    def tracking_table(table_name: str):
        table = original_insert(table_name)
        original_insert_method = table.insert
        
        def tracking_insert(data):
            result = original_insert_method(data)
            if table_name in created_records:
                created_records[table_name].append(data)
            return result
        
        table.insert = tracking_insert
        return table
    
    test_supabase_client.table = tracking_table
    
    yield test_supabase_client
    
    # Cleanup created records
    for table_name, records in created_records.items():
        if records:
            ids = [r.get("id") for r in records if r.get("id")]
            if ids:
                try:
                    test_supabase_client.table(table_name).delete().in_("id", ids).execute()
                except Exception as e:
                    warnings.warn(f"Failed to cleanup {table_name}: {e}")


# =============================================================================
# Service fixtures (using real services with test database)
# =============================================================================

@pytest.fixture
async def integration_project_service(test_supabase_client):
    """Real project service for integration tests."""
    service = ProjectService(test_supabase_client)
    return service


@pytest.fixture
async def integration_task_service(test_supabase_client):
    """Real task service for integration tests."""
    service = TaskService(test_supabase_client)
    return service


@pytest.fixture
async def integration_document_service(test_supabase_client):
    """Real document service for integration tests."""
    service = DocumentService(test_supabase_client)
    return service


@pytest.fixture
async def integration_credential_service():
    """Real credential service for integration tests."""
    # Use test-specific encryption key
    test_key = os.getenv("TEST_ENCRYPTION_KEY", "test-key-for-integration-tests")
    os.environ["CREDENTIAL_ENCRYPTION_KEY"] = test_key
    
    service = CredentialService()
    yield service
    
    # Cleanup
    if "CREDENTIAL_ENCRYPTION_KEY" in os.environ:
        del os.environ["CREDENTIAL_ENCRYPTION_KEY"]


# =============================================================================
# MCP fixtures for integration testing
# =============================================================================

@pytest.fixture
async def test_mcp_server():
    """Start a test MCP server for integration tests."""
    # This would start an actual test MCP server
    # For now, we'll use a mock that behaves like a real server
    server = Mock()
    server.start = Mock()
    server.stop = Mock()
    server.url = "http://localhost:8999"
    
    yield server
    
    # Cleanup
    server.stop()


@pytest.fixture
async def integration_mcp_client(test_mcp_server):
    """Real MCP client connected to test server."""
    client = MCPClientService(
        name="test-client",
        server_params={
            "url": test_mcp_server.url,
            "transport": "sse"
        }
    )
    
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def integration_mcp_session_manager():
    """Real MCP session manager for integration tests."""
    manager = MCPSessionManager()
    yield manager
    
    # Cleanup all sessions
    await manager.cleanup_expired_sessions()


# =============================================================================
# Test data fixtures
# =============================================================================

@pytest.fixture
async def test_project(integration_project_service):
    """Create a real test project."""
    project_data = {
        "name": "Integration Test Project",
        "description": "Project for integration testing",
        "metadata": {"test": True}
    }
    
    project = await integration_project_service.create_project(project_data)
    yield project
    
    # Cleanup
    try:
        await integration_project_service.delete_project(project["id"])
    except Exception:
        pass


@pytest.fixture
async def test_task(integration_task_service, test_project):
    """Create a real test task."""
    task_data = {
        "project_id": test_project["id"],
        "title": "Integration Test Task",
        "description": "Task for integration testing",
        "status": "todo",
        "metadata": {"test": True}
    }
    
    task = await integration_task_service.create_task(task_data)
    yield task
    
    # Cleanup
    try:
        await integration_task_service.delete_task(task["id"])
    except Exception:
        pass


@pytest.fixture
async def test_document(integration_document_service, test_project):
    """Create a real test document."""
    doc_data = {
        "project_id": test_project["id"],
        "title": "Integration Test Document",
        "content": {"text": "Test content for integration testing"},
        "type": "markdown",
        "metadata": {"test": True}
    }
    
    document = await integration_document_service.create_document(doc_data)
    yield document
    
    # Cleanup
    try:
        await integration_document_service.delete_document(document["id"])
    except Exception:
        pass


# =============================================================================
# API client fixtures
# =============================================================================

@pytest.fixture
async def test_api_client():
    """HTTP client for testing API endpoints."""
    from httpx import AsyncClient
    from src.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Set test headers
        client.headers.update({
            "X-Test-Mode": "true",
            "Authorization": "Bearer test-token"
        })
        yield client


# =============================================================================
# WebSocket fixtures
# =============================================================================

@pytest.fixture
async def test_websocket_client():
    """WebSocket client for testing WebSocket endpoints."""
    from fastapi.testclient import TestClient
    from src.main import app
    
    client = TestClient(app)
    return client


# =============================================================================
# Performance monitoring
# =============================================================================

@pytest.fixture
def integration_performance_monitor():
    """Monitor performance metrics during integration tests."""
    import time
    import psutil
    import gc
    
    process = psutil.Process()
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.metrics = {}
        
        def start(self):
            gc.collect()
            self.start_time = time.perf_counter()
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def stop(self, test_name: str):
            duration = time.perf_counter() - self.start_time
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = end_memory - self.start_memory
            
            self.metrics[test_name] = {
                "duration": duration,
                "memory_delta": memory_delta,
                "end_memory": end_memory
            }
            
            # Warn if test is slow or uses too much memory
            if duration > 5.0:
                warnings.warn(f"{test_name} took {duration:.2f}s (>5s)")
            if memory_delta > 50:
                warnings.warn(f"{test_name} used {memory_delta:.1f}MB memory")
        
        def get_report(self):
            return self.metrics
    
    monitor = PerformanceMonitor()
    yield monitor
    
    # Print performance report
    if monitor.metrics:
        print("\n=== Integration Test Performance Report ===")
        for test, metrics in monitor.metrics.items():
            print(f"{test}: {metrics['duration']:.2f}s, {metrics['memory_delta']:.1f}MB")


# =============================================================================
# Cleanup fixtures
# =============================================================================

@pytest.fixture(autouse=True)
async def cleanup_test_data(request):
    """Ensure test data is cleaned up after each test."""
    yield
    
    # Additional cleanup if needed
    if hasattr(request, "test_cleanup_funcs"):
        for func in request.test_cleanup_funcs:
            try:
                await func()
            except Exception as e:
                warnings.warn(f"Cleanup failed: {e}")


@pytest.fixture
def register_cleanup(request):
    """Register cleanup functions to run after test."""
    if not hasattr(request, "test_cleanup_funcs"):
        request.test_cleanup_funcs = []
    
    def add_cleanup(func):
        request.test_cleanup_funcs.append(func)
    
    return add_cleanup