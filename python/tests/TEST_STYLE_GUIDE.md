# Archon Test Style Guide

This guide defines the testing standards and patterns for the Archon project. All tests should follow these conventions to maintain consistency and quality.

## Table of Contents
1. [General Principles](#general-principles)
2. [Test Organization](#test-organization)
3. [Naming Conventions](#naming-conventions)
4. [Test Structure](#test-structure)
5. [Fixtures and Mocking](#fixtures-and-mocking)
6. [Assertions](#assertions)
7. [Async Testing](#async-testing)
8. [Performance Testing](#performance-testing)
9. [Test Data](#test-data)
10. [Common Patterns](#common-patterns)

## General Principles

### 1. Single Responsibility
- Each test should verify ONE specific behavior
- If a test name contains "and", consider splitting it

### 2. Independence
- Tests must not depend on execution order
- Each test must set up its complete state
- Use fixtures for shared setup, not shared state

### 3. Clarity Over Cleverness
- Explicit is better than implicit
- Duplicate code in tests is often better than complex abstractions
- Test code should be obvious to understand

### 4. Fast and Reliable
- Unit tests should complete in milliseconds
- Mock all external dependencies
- Use `@pytest.mark.slow` for tests > 1 second

## Test Organization

### Directory Structure
```
tests/
├── unit/                  # Fast, isolated tests
│   ├── test_services/    # Service layer tests
│   ├── test_api/        # API endpoint tests
│   └── test_models/     # Model tests
├── integration/          # Tests with real dependencies
├── e2e/                 # End-to-end workflow tests
├── performance/         # Performance benchmarks
└── fixtures/           # Shared test utilities
    ├── mock_data.py   # Test data factories
    └── test_helpers.py # Assertion helpers
```

### Test Classes
Group related tests in classes:
```python
@pytest.mark.unit
@pytest.mark.critical
class TestProjectService:
    """Tests for ProjectService."""
    # All project service tests here
```

## Naming Conventions

### Test Functions
```python
# Pattern: test_<method>_<scenario>_<expected_result>

def test_create_project_with_valid_data_returns_success():
    """Test creating a project with valid data returns success."""

def test_create_project_with_empty_title_returns_error():
    """Test creating a project with empty title returns error."""

def test_update_task_status_from_todo_to_doing_succeeds():
    """Test updating task status from todo to doing succeeds."""
```

### Fixtures
```python
# Use descriptive names that indicate what they provide
@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chained method support."""

@pytest.fixture
def make_project_data():
    """Factory fixture for creating project test data."""
```

## Test Structure

### AAA Pattern (Arrange, Act, Assert)
```python
def test_example():
    # Arrange - Set up test data and mocks
    project_data = ProjectFactory.create(title="Test Project")
    mock_client.execute.return_value = MagicMock(data=[project_data])
    
    # Act - Execute the code under test
    success, result = service.create_project(title="Test Project")
    
    # Assert - Verify the results
    assert success is True
    assert result["project"]["title"] == "Test Project"
    assert_called_with_subset(mock_client.insert, title="Test Project")
```

### Docstrings
Add docstrings for complex test scenarios:
```python
def test_complex_workflow():
    """Test complete project lifecycle.
    
    This test verifies:
    1. Project creation with initial tasks
    2. Task status transitions
    3. Project archival cascades to tasks
    4. Proper WebSocket notifications at each step
    """
```

## Fixtures and Mocking

### Fixture Scopes
```python
@pytest.fixture(scope="session")  # Expensive setup, shared across all tests
def database_connection():
    """Session-scoped database connection."""

@pytest.fixture(scope="class")     # Shared within test class
def api_client():
    """Class-scoped API client."""

@pytest.fixture                    # Default: function scope
def mock_service():
    """Function-scoped mock service."""
```

### Mock Best Practices
```python
# Always use autospec=True for type safety
mock_service = Mock(spec=ServiceClass, autospec=True)

# Use AsyncMock for async methods
mock_async_method = AsyncMock(return_value=expected_result)

# Mock at the usage point, not definition
@patch('src.services.project_service.external_api_call')
def test_something(mock_api):
    pass
```

## Assertions

### Specific Error Messages
```python
# Bad
assert "error" in result

# Good
assert result["error"] == "Project title is required and cannot be empty"
```

### Custom Assertions
Use domain-specific assertion helpers:
```python
# Use these helpers from test_helpers.py
assert_valid_project_state(project)
assert_task_hierarchy_valid(tasks)
assert_api_response_valid(response, success=True)
assert_websocket_message_valid(message, expected_type="task_updated")
```

### Multiple Assertions
Group related assertions with comments:
```python
# Verify response structure
assert success is True
assert "project" in result

# Verify project data
project = result["project"]
assert_valid_uuid(project["id"])
assert project["title"] == expected_title
assert project["status"] == "active"

# Verify side effects
assert mock_websocket.broadcast.called_once()
```

## Async Testing

### Standard Pattern
```python
@pytest.mark.asyncio
@pytest.mark.timeout(5)  # Always set explicit timeouts
async def test_async_operation():
    # Arrange
    async with create_test_context() as context:
        mock_service = AsyncMock(return_value=expected_result)
        
        # Act
        result = await async_operation(context)
        
        # Assert
        assert result.success is True
        await assert_async_timeout(
            mock_service.assert_called_once(),
            timeout=1.0
        )
```

### WebSocket Testing
```python
@pytest.mark.websocket
async def test_websocket_notifications():
    async with websocket_connect("/ws") as ws:
        # Trigger action
        await service.create_task(...)
        
        # Assert message received
        message = await assert_websocket_receives(
            ws, 
            expected_type="task_created",
            timeout=2.0
        )
        assert message["task_id"] == expected_id
```

## Performance Testing

### Basic Performance Test
```python
@pytest.mark.slow
@pytest.mark.performance
def test_list_performance():
    # Arrange
    projects = [ProjectFactory.create() for _ in range(1000)]
    
    # Act & Assert
    with PerformanceTimer("list_projects", threshold=0.2):
        result = service.list_projects()
    
    assert len(result["projects"]) == 1000
```

### Parametrized Performance Tests
```python
@pytest.mark.parametrize("record_count", [100, 500, 1000, 5000])
def test_scaling_performance(record_count):
    # Test with different data sizes
    baseline_time = 0.0001 * record_count  # Linear scaling expected
    
    with PerformanceTimer(f"{record_count} records", threshold=baseline_time * 1.5):
        process_records(record_count)
```

## Test Data

### Using Factories
```python
# Simple factory usage
project = ProjectFactory.create(title="Custom Title")

# Builder pattern for complex scenarios
test_data = (ProjectBuilder()
    .with_title("Complex Project")
    .with_tasks(count=10)
    .with_task_hierarchy(depth=3, width=3)
    .with_documents(count=5)
    .build())
```

### Parametrized Test Data
```python
@pytest.mark.parametrize("title,status,expected", [
    pytest.param("Valid", "active", True, id="valid-active"),
    pytest.param("", "active", False, id="empty-title"),
    pytest.param("Valid", "invalid", False, id="invalid-status"),
])
def test_validation(title, status, expected):
    result = validate_project(title=title, status=status)
    assert result.is_valid == expected
```

## Common Patterns

### Testing Error Cases
```python
@pytest.mark.parametrize("exception,expected_error", [
    pytest.param(
        ConnectionError("Network error"),
        "Failed to connect to service",
        id="connection-error"
    ),
    pytest.param(
        ValueError("Invalid input"),
        "Invalid input provided",
        id="validation-error"
    ),
])
def test_error_handling(mock_service, exception, expected_error):
    mock_service.side_effect = exception
    
    success, result = service.operation()
    
    assert success is False
    assert expected_error in result["error"]
```

### Testing State Transitions
```python
@pytest.mark.parametrize("from_status,to_status,allowed", [
    ("todo", "doing", True),
    ("doing", "review", True),
    ("done", "todo", True),  # Can restart
    ("todo", "invalid", False),
])
def test_status_transitions(from_status, to_status, allowed):
    task = TaskFactory.create(status=from_status)
    
    result = service.update_status(task["id"], to_status)
    
    assert result.success == allowed
    if allowed:
        assert result.task["status"] == to_status
```

### Testing with Time
```python
def test_time_based_logic(freezer):
    # Freeze time for consistent testing
    freezer.move_to("2024-01-01")
    
    task = service.create_task(due_in_days=7)
    assert task["due_date"] == "2024-01-08"
    
    # Move time forward
    freezer.move_to("2024-01-05")
    assert service.is_overdue(task) is False
    
    freezer.move_to("2024-01-09")
    assert service.is_overdue(task) is True
```

## Markers

Always use appropriate markers:
```python
@pytest.mark.unit          # Fast, isolated unit test
@pytest.mark.integration   # Requires external resources
@pytest.mark.e2e          # End-to-end workflow
@pytest.mark.critical     # Must pass for deployment
@pytest.mark.slow         # Takes > 1 second
@pytest.mark.flaky        # Known intermittent failures
@pytest.mark.requires_openai  # Needs OpenAI API
```

## Code Review Checklist

When reviewing test code, ensure:
- [ ] Test has single, clear purpose
- [ ] Test name describes scenario and expected outcome
- [ ] Uses AAA pattern (Arrange, Act, Assert)
- [ ] Appropriate fixtures vs inline setup
- [ ] Proper parametrization for similar tests
- [ ] Async tests have explicit timeouts
- [ ] Mocks use autospec=True
- [ ] Specific error message assertions
- [ ] No hardcoded values (use fixtures)
- [ ] Appropriate test markers applied
- [ ] Performance tests have reasonable thresholds

## Examples

### Complete Unit Test Example
```python
@pytest.mark.unit
@pytest.mark.critical
class TestProjectService:
    """Unit tests for ProjectService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client with chained method support."""
        mock = MagicMock()
        # Setup chainable methods
        for method in ["table", "select", "insert", "eq", "execute"]:
            setattr(mock, method, MagicMock(return_value=mock))
        return mock
    
    @pytest.fixture
    def project_service(self, mock_supabase_client):
        """Create ProjectService instance with mocked dependencies."""
        return ProjectService(supabase_client=mock_supabase_client)
    
    @pytest.mark.parametrize("title,expected_success", [
        pytest.param("Valid Project", True, id="valid-title"),
        pytest.param("", False, id="empty-title"),
        pytest.param(None, False, id="none-title"),
    ])
    def test_create_project_validation(
        self, 
        project_service, 
        mock_supabase_client,
        title,
        expected_success
    ):
        """Test project creation with various title inputs."""
        # Arrange
        if expected_success:
            mock_project = ProjectFactory.create(title=title)
            mock_supabase_client.execute.return_value = MagicMock(
                data=[mock_project]
            )
        
        # Act
        success, result = project_service.create_project(title=title)
        
        # Assert
        assert success == expected_success
        
        if expected_success:
            assert_valid_project_state(result["project"])
            assert result["project"]["title"] == title
        else:
            assert_api_response_valid(result, success=False)
            assert "title is required" in result["error"]
```

This style guide is a living document. Update it as new patterns emerge or better practices are discovered.