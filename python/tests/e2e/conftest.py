"""End-to-end test specific fixtures and configuration."""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import Dict, Any, List
from unittest.mock import Mock
import warnings
import time


# =============================================================================
# System setup fixtures
# =============================================================================

@pytest.fixture(scope="session")
async def e2e_system_setup():
    """Complete system setup for E2E tests."""
    setup_info = {
        "start_time": time.time(),
        "services_started": [],
        "cleanup_functions": []
    }
    
    # Start all required services
    # This would typically start:
    # - Database
    # - API server
    # - MCP servers
    # - Background workers
    
    yield setup_info
    
    # Cleanup all services
    for cleanup_func in setup_info["cleanup_functions"]:
        try:
            await cleanup_func()
        except Exception as e:
            warnings.warn(f"E2E cleanup failed: {e}")


@pytest.fixture(scope="module")
async def e2e_api_server(e2e_system_setup):
    """Start API server for E2E tests."""
    # In a real implementation, this would start the FastAPI server
    server_info = {
        "url": "http://localhost:8000",
        "health_endpoint": "/health",
        "started": True
    }
    
    # Wait for server to be ready
    await asyncio.sleep(1)
    
    yield server_info


@pytest.fixture(scope="module")
async def e2e_mcp_servers(e2e_system_setup):
    """Start MCP servers for E2E tests."""
    servers = {
        "project_manager": {
            "url": "http://localhost:9001",
            "transport": "sse"
        },
        "rag_server": {
            "url": "http://localhost:9002",
            "transport": "websocket"
        }
    }
    
    yield servers


# =============================================================================
# User and authentication fixtures
# =============================================================================

@pytest.fixture
async def e2e_test_user():
    """Create a test user for E2E tests."""
    user = {
        "id": "user_e2e_test",
        "email": "e2e@test.com",
        "name": "E2E Test User",
        "api_key": "e2e-test-api-key",
        "permissions": ["read", "write", "admin"]
    }
    
    yield user


@pytest.fixture
async def e2e_auth_headers(e2e_test_user):
    """Authentication headers for E2E tests."""
    return {
        "Authorization": f"Bearer {e2e_test_user['api_key']}",
        "X-User-ID": e2e_test_user["id"]
    }


# =============================================================================
# Complete workflow fixtures
# =============================================================================

@pytest.fixture
async def e2e_project_workflow():
    """Set up a complete project workflow for testing."""
    workflow = {
        "project": None,
        "tasks": [],
        "documents": [],
        "rag_sources": [],
        "chat_sessions": []
    }
    
    # This would be populated by the test
    yield workflow
    
    # Cleanup would happen here


@pytest.fixture
async def e2e_rag_workflow():
    """Set up a complete RAG workflow for testing."""
    workflow = {
        "sources": [],
        "crawl_jobs": [],
        "documents": [],
        "search_queries": [],
        "chat_sessions": []
    }
    
    yield workflow


# =============================================================================
# API client fixtures
# =============================================================================

@pytest.fixture
async def e2e_api_client(e2e_api_server, e2e_auth_headers):
    """Authenticated API client for E2E tests."""
    try:
        from httpx import AsyncClient
        
        async with AsyncClient(base_url=e2e_api_server["url"]) as client:
            client.headers.update(e2e_auth_headers)
            
            # Verify server is ready
            response = await client.get(e2e_api_server["health_endpoint"])
            if response.status_code != 200:
                pytest.fail("API server not healthy")
            
            yield client
    except ImportError:
        # Fallback to mock client
        client = Mock()
        client.get = Mock()
        client.post = Mock()
        client.put = Mock()
        client.delete = Mock()
        yield client


@pytest.fixture
async def e2e_websocket_client(e2e_api_server, e2e_auth_headers):
    """WebSocket client for E2E tests."""
    ws_url = e2e_api_server["url"].replace("http://", "ws://")
    
    # This would create a real WebSocket connection
    client = Mock()
    client.connect = Mock()
    client.send = Mock()
    client.receive = Mock()
    client.close = Mock()
    
    yield client


# =============================================================================
# Data generation fixtures
# =============================================================================

@pytest.fixture
def e2e_test_data_generator():
    """Generate test data for E2E scenarios."""
    
    class TestDataGenerator:
        def __init__(self):
            self.counter = 0
        
        def generate_project(self, **overrides) -> Dict[str, Any]:
            self.counter += 1
            project = {
                "name": f"E2E Project {self.counter}",
                "description": f"End-to-end test project {self.counter}",
                "status": "active",
                "metadata": {
                    "test_type": "e2e",
                    "test_id": f"e2e_proj_{self.counter}"
                }
            }
            project.update(overrides)
            return project
        
        def generate_task(self, project_id: str, **overrides) -> Dict[str, Any]:
            self.counter += 1
            task = {
                "project_id": project_id,
                "title": f"E2E Task {self.counter}",
                "description": f"End-to-end test task {self.counter}",
                "status": "todo",
                "priority": "medium",
                "metadata": {
                    "test_type": "e2e",
                    "test_id": f"e2e_task_{self.counter}"
                }
            }
            task.update(overrides)
            return task
        
        def generate_document(self, project_id: str, **overrides) -> Dict[str, Any]:
            self.counter += 1
            document = {
                "project_id": project_id,
                "title": f"E2E Document {self.counter}",
                "content": {
                    "text": f"This is test document {self.counter} for end-to-end testing.",
                    "sections": [
                        {"title": "Introduction", "content": "Test introduction"},
                        {"title": "Details", "content": "Test details"}
                    ]
                },
                "type": "markdown",
                "metadata": {
                    "test_type": "e2e",
                    "test_id": f"e2e_doc_{self.counter}"
                }
            }
            document.update(overrides)
            return document
        
        def generate_chat_message(self, role: str = "user", **overrides) -> Dict[str, Any]:
            self.counter += 1
            message = {
                "role": role,
                "content": f"Test message {self.counter} from {role}",
                "metadata": {
                    "test_type": "e2e",
                    "test_id": f"e2e_msg_{self.counter}"
                }
            }
            message.update(overrides)
            return message
    
    return TestDataGenerator()


# =============================================================================
# Scenario fixtures
# =============================================================================

@pytest.fixture
async def e2e_populated_project(e2e_api_client, e2e_test_data_generator):
    """Create a populated project for E2E testing."""
    generator = e2e_test_data_generator
    
    # Create project
    project_data = generator.generate_project()
    project_response = await e2e_api_client.post("/api/v1/projects", json=project_data)
    project = project_response.json()
    
    # Create tasks
    tasks = []
    for i in range(5):
        task_data = generator.generate_task(project["id"], status=["todo", "in_progress", "done"][i % 3])
        task_response = await e2e_api_client.post("/api/v1/tasks", json=task_data)
        tasks.append(task_response.json())
    
    # Create documents
    documents = []
    for i in range(3):
        doc_data = generator.generate_document(project["id"])
        doc_response = await e2e_api_client.post("/api/v1/documents", json=doc_data)
        documents.append(doc_response.json())
    
    result = {
        "project": project,
        "tasks": tasks,
        "documents": documents
    }
    
    yield result
    
    # Cleanup
    try:
        await e2e_api_client.delete(f"/api/v1/projects/{project['id']}")
    except Exception:
        pass


# =============================================================================
# Performance and monitoring
# =============================================================================

@pytest.fixture
def e2e_performance_tracker():
    """Track performance metrics for E2E tests."""
    
    class PerformanceTracker:
        def __init__(self):
            self.metrics = []
            self.thresholds = {
                "api_response_time": 1.0,  # seconds
                "workflow_completion": 30.0,  # seconds
                "memory_usage": 500,  # MB
            }
        
        def track_api_call(self, endpoint: str, duration: float):
            self.metrics.append({
                "type": "api_call",
                "endpoint": endpoint,
                "duration": duration,
                "timestamp": time.time()
            })
            
            if duration > self.thresholds["api_response_time"]:
                warnings.warn(f"Slow API call to {endpoint}: {duration:.2f}s")
        
        def track_workflow(self, workflow_name: str, duration: float):
            self.metrics.append({
                "type": "workflow",
                "name": workflow_name,
                "duration": duration,
                "timestamp": time.time()
            })
            
            if duration > self.thresholds["workflow_completion"]:
                warnings.warn(f"Slow workflow {workflow_name}: {duration:.2f}s")
        
        def get_summary(self) -> Dict[str, Any]:
            if not self.metrics:
                return {}
            
            api_calls = [m for m in self.metrics if m["type"] == "api_call"]
            workflows = [m for m in self.metrics if m["type"] == "workflow"]
            
            return {
                "total_api_calls": len(api_calls),
                "avg_api_response_time": sum(m["duration"] for m in api_calls) / len(api_calls) if api_calls else 0,
                "total_workflows": len(workflows),
                "avg_workflow_time": sum(m["duration"] for m in workflows) / len(workflows) if workflows else 0,
                "slow_operations": len([m for m in self.metrics if m["duration"] > 1.0])
            }
    
    tracker = PerformanceTracker()
    yield tracker
    
    # Print summary
    summary = tracker.get_summary()
    if summary:
        print("\n=== E2E Performance Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")


# =============================================================================
# Validation helpers
# =============================================================================

@pytest.fixture
def e2e_validators():
    """Validation helpers for E2E tests."""
    
    class Validators:
        @staticmethod
        def validate_project(project: Dict[str, Any]) -> bool:
            required_fields = ["id", "name", "description", "status", "created_at", "updated_at"]
            return all(field in project for field in required_fields)
        
        @staticmethod
        def validate_task(task: Dict[str, Any]) -> bool:
            required_fields = ["id", "project_id", "title", "status", "created_at", "updated_at"]
            valid_statuses = ["todo", "in_progress", "done", "archived"]
            return (
                all(field in task for field in required_fields) and
                task.get("status") in valid_statuses
            )
        
        @staticmethod
        def validate_workflow_complete(workflow: Dict[str, Any]) -> bool:
            return (
                workflow.get("project") is not None and
                len(workflow.get("tasks", [])) > 0 and
                len(workflow.get("documents", [])) > 0
            )
    
    return Validators()


# =============================================================================
# Cleanup and teardown
# =============================================================================

@pytest.fixture(autouse=True)
async def e2e_test_isolation():
    """Ensure E2E tests are properly isolated."""
    # Setup
    start_time = time.time()
    
    yield
    
    # Teardown
    duration = time.time() - start_time
    if duration > 60:  # 1 minute
        warnings.warn(f"E2E test took too long: {duration:.1f}s")


@pytest.fixture
async def e2e_cleanup_registry():
    """Registry for cleanup operations."""
    cleanup_operations = []
    
    def register_cleanup(operation):
        cleanup_operations.append(operation)
    
    yield register_cleanup
    
    # Execute all cleanup operations
    for operation in reversed(cleanup_operations):
        try:
            if asyncio.iscoroutinefunction(operation):
                await operation()
            else:
                operation()
        except Exception as e:
            warnings.warn(f"Cleanup operation failed: {e}")