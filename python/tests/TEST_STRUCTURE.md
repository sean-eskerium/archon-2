# Archon Python Test Structure - File Creation Guide

This document shows the exact directory structure and files to create for the test suite.

## Directory Structure to Create

```bash
# Create directories
mkdir -p tests/unit/test_services/test_projects
mkdir -p tests/unit/test_services/test_rag
mkdir -p tests/unit/test_modules
mkdir -p tests/unit/test_utils
mkdir -p tests/unit/test_models
mkdir -p tests/integration/test_api
mkdir -p tests/integration/test_mcp
mkdir -p tests/integration/test_websockets
mkdir -p tests/integration/test_database
mkdir -p tests/e2e/test_workflows
mkdir -p tests/e2e/test_mcp_tools
mkdir -p tests/performance
mkdir -p tests/fixtures
```

## Complete File List

### Configuration Files

```
tests/
├── __init__.py
├── conftest.py                                    # Global test configuration
├── pytest.ini                                     # Pytest settings
└── .coveragerc                                   # Coverage configuration
```

### Unit Tests - Service Layer (Priority: CRITICAL)

```
tests/unit/test_services/
├── __init__.py
├── test_credential_service.py                     # 6 tests
├── test_mcp_client_service.py                     # 8 tests
├── test_mcp_session_manager.py                    # 5 tests
├── test_prompt_service.py                         # 4 tests
├── test_projects/
│   ├── __init__.py
│   ├── test_project_service.py                   # 8 tests
│   ├── test_task_service.py                      # 10 tests
│   ├── test_document_service.py                  # 7 tests
│   └── test_versioning_service.py                # 7 tests
└── test_rag/
    ├── __init__.py
    ├── test_crawling_service.py                  # 8 tests
    ├── test_document_storage_service.py          # 8 tests
    ├── test_search_service.py                    # 8 tests
    └── test_source_management_service.py         # 6 tests
```

### Unit Tests - Modules (Priority: HIGH)

```
tests/unit/test_modules/
├── __init__.py
├── test_project_module.py                         # 4 tests
├── test_rag_module.py                            # 4 tests
└── test_models.py                                # 4 tests
```

### Unit Tests - Utils (Priority: HIGH)

```
tests/unit/test_utils/
├── __init__.py
├── test_utils.py                                 # 6 tests
├── test_config.py                                # 3 tests
└── test_logfire_config.py                        # 3 tests
```

### Unit Tests - Core Components (Priority: CRITICAL)

```
tests/unit/
├── test_mcp_server.py                            # 6 tests
└── test_main.py                                  # 5 tests
```

### Integration Tests - API (Priority: CRITICAL)

```
tests/integration/test_api/
├── __init__.py
├── test_agent_chat_api.py                        # 7 tests
├── test_knowledge_api.py                         # 9 tests
├── test_mcp_api.py                              # 6 tests
├── test_mcp_client_api.py                       # 5 tests
├── test_projects_api.py                         # 9 tests
├── test_settings_api.py                         # 6 tests
└── test_tests_api.py                            # 4 tests
```

### Integration Tests - MCP Server (Priority: HIGH)

```
tests/integration/test_mcp/
├── __init__.py
├── test_mcp_server_lifecycle.py                 # 6 tests
├── test_mcp_tool_execution.py                   # 8 tests
└── test_mcp_session_management.py               # 4 tests
```

### Integration Tests - WebSockets (Priority: MEDIUM)

```
tests/integration/test_websockets/
├── __init__.py
├── test_websocket_connections.py                # 5 tests
├── test_progress_streaming.py                   # 4 tests
└── test_chat_websockets.py                     # 4 tests
```

### Integration Tests - Database (Priority: HIGH)

```
tests/integration/test_database/
├── __init__.py
├── test_database_connections.py                 # 3 tests
├── test_migrations.py                           # 3 tests
└── test_transactions.py                        # 4 tests
```

### End-to-End Tests (Priority: MEDIUM)

```
tests/e2e/test_workflows/
├── __init__.py
├── test_knowledge_workflow.py                   # 3 tests
├── test_project_workflow.py                    # 3 tests
└── test_agent_workflow.py                      # 2 tests
```

```
tests/e2e/test_mcp_tools/
├── __init__.py
├── test_mcp_tool_chains.py                    # 3 tests
└── test_cross_module_tools.py                 # 2 tests
```

### Performance Tests (Priority: LOW)

```
tests/performance/
├── __init__.py
├── test_load_performance.py                    # 4 tests
└── test_search_performance.py                  # 3 tests
```

### Test Fixtures and Utilities

```
tests/fixtures/
├── __init__.py
├── mock_data.py                                # Test data factories
├── test_helpers.py                             # Helper functions
├── api_mocks.py                               # API response mocks
├── database_fixtures.py                       # Database test data
└── websocket_mocks.py                         # WebSocket mocks
```

## Test File Templates

### Unit Test Template

```python
# tests/unit/test_services/test_projects/test_project_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.projects.project_service import ProjectService

class TestProjectService:
    """Unit tests for ProjectService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database dependency."""
        return AsyncMock()
    
    @pytest.fixture
    def project_service(self, mock_db):
        """Create ProjectService instance with mocked dependencies."""
        return ProjectService(db=mock_db)
    
    async def test_project_service_creates_project_with_valid_data(self, project_service, mock_db):
        """Test creating a project with valid data returns expected result."""
        # Arrange
        # Act
        # Assert
        pass
```

### Integration Test Template

```python
# tests/integration/test_api/test_projects_api.py
import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
class TestProjectsAPI:
    """Integration tests for projects API endpoints."""
    
    async def test_create_project_endpoint_returns_201(self, async_client: AsyncClient):
        """Test POST /api/projects returns 201 Created."""
        # Arrange
        # Act
        # Assert
        pass
```

## Summary Statistics

- **Total Directories**: 18
- **Total Test Files**: 52
- **Total Test Cases**: 145
- **Critical Priority Tests**: 75 (52%)
- **High Priority Tests**: 45 (31%)
- **Medium Priority Tests**: 18 (12%)
- **Low Priority Tests**: 7 (5%)

## Implementation Order

1. **Day 1-2**: Create directory structure and base configuration
2. **Week 1**: Implement critical service layer tests (52 tests)
3. **Week 2**: Implement API integration tests (46 tests)
4. **Week 3**: Implement remaining tests (47 tests)

This structure provides complete test coverage for the Archon Python backend with clear priorities and implementation guidance.