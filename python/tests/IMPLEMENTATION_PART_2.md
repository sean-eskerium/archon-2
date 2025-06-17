# Test Suite Implementation Part 2: Refactoring Plan

## Lessons Learned from Pytest Documentation

After reviewing extensive pytest documentation examples, I've identified several patterns and best practices that can significantly improve our test suite. This document outlines a comprehensive refactoring plan based on these insights.

## Key Patterns Identified

### 1. Fixture Organization and Scoping
- **Current**: Most fixtures are function-scoped by default
- **Best Practice**: Use appropriate scopes (`session`, `module`, `class`, `function`) to optimize resource usage
- **Example**: Database connections should be session-scoped, not recreated for each test

### 2. Parametrization Improvements
- **Current**: Limited use of parametrization
- **Best Practice**: Use `@pytest.mark.parametrize` with custom IDs for better test reporting
- **Example**: Use `ids` parameter or `pytest.param` for meaningful test names

### 3. Marker Usage
- **Current**: Basic markers (critical, integration, etc.)
- **Best Practice**: Create domain-specific markers with metadata
- **Example**: `@pytest.mark.timeout(10, method="thread")` for performance tests

### 4. Exception Testing
- **Current**: Basic `pytest.raises` usage
- **Best Practice**: Use context managers with regex matching and exception inspection
- **Example**: Access `excinfo` for detailed assertions

### 5. Fixture Factories
- **Current**: Static fixtures returning fixed data
- **Best Practice**: Factory fixtures that can generate customized test data
- **Example**: `make_customer_record` pattern for flexible data generation

## Refactoring Checklist

### Phase 1: Infrastructure Improvements

#### 1.1 Enhanced pytest.ini Configuration
```ini
# Current
[pytest]
markers = 
    critical: Critical priority tests
    slow: Slow running tests

# Improved
[pytest]
minversion = 8.0
addopts = 
    -ra
    --strict-markers
    --import-mode=importlib
    --tb=short
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    critical: Critical priority tests that must pass
    slow: Tests that take > 1s to run (deselect with '-m "not slow"')
    integration: Integration tests requiring external resources
    unit: Fast, isolated unit tests
    e2e: End-to-end workflow tests
    performance: Performance benchmark tests
    asyncio: Asynchronous test (auto-applied)
    timeout(seconds): Test timeout duration
    flaky(reruns, delay): Retry flaky tests
required_plugins = 
    pytest-asyncio>=0.21.0
    pytest-timeout>=2.1.0
    pytest-mock>=3.10.0
```

#### 1.2 Improved conftest.py Structure
```python
# Current approach - everything in one file
# Improved approach - hierarchical conftest files

# tests/conftest.py - Root level fixtures
@pytest.fixture(scope="session")
def app_config():
    """Session-wide app configuration."""
    return {...}

# tests/unit/conftest.py - Unit test fixtures
@pytest.fixture
def mock_supabase(monkeypatch):
    """Auto-use fixture to prevent database calls."""
    ...

# tests/integration/conftest.py - Integration fixtures
@pytest.fixture(scope="module")
def test_database():
    """Test database connection."""
    ...
```

### Phase 2: Fixture Refactoring

#### 2.1 Scope Optimization
```python
# Before
@pytest.fixture
def embedding_model():
    return "text-embedding-ada-002"

# After
@pytest.fixture(scope="session")
def embedding_model():
    """Session-scoped since model doesn't change."""
    return "text-embedding-ada-002"

@pytest.fixture(scope="module")
def mock_openai_client():
    """Module-scoped for API client mocks."""
    return Mock()
```

#### 2.2 Factory Fixtures
```python
# Before
@pytest.fixture
def project_data():
    return {"name": "Test Project", "description": "Test"}

# After
@pytest.fixture
def make_project():
    """Factory fixture for creating custom projects."""
    created_projects = []
    
    def _make_project(name=None, **kwargs):
        project = {
            "id": f"proj_{len(created_projects)}",
            "name": name or f"Project {len(created_projects)}",
            "description": kwargs.get("description", "Test project"),
            "metadata": kwargs.get("metadata", {}),
            "created_at": datetime.now().isoformat()
        }
        created_projects.append(project)
        return project
    
    yield _make_project
    
    # Cleanup
    for project in created_projects:
        print(f"Cleanup project: {project['id']}")
```

#### 2.3 Parametrized Fixtures
```python
# Before
@pytest.fixture
def transport_config():
    return {"type": "SSE", "url": "http://localhost:8080"}

# After
@pytest.fixture(params=[
    pytest.param({"type": "SSE", "url": "http://localhost:8080"}, id="sse"),
    pytest.param({"type": "WebSocket", "url": "ws://localhost:8080"}, id="websocket"),
])
def transport_config(request):
    """Parametrized transport configurations."""
    return request.param
```

### Phase 3: Test Improvements

#### 3.1 Enhanced Parametrization
```python
# Before
@pytest.mark.parametrize("status", ["todo", "in_progress", "done"])
def test_task_status(status):
    ...

# After
@pytest.mark.parametrize(
    "status,expected_complete",
    [
        pytest.param("todo", False, id="todo-incomplete"),
        pytest.param("in_progress", False, id="progress-incomplete"),
        pytest.param("done", True, id="done-complete"),
        pytest.param("invalid", None, marks=pytest.mark.xfail(reason="Invalid status")),
    ]
)
def test_task_status(status, expected_complete):
    ...
```

#### 3.2 Better Exception Testing
```python
# Before
with pytest.raises(ValueError):
    service.create_project({})

# After
with pytest.raises(ValueError, match=r"name.*required") as excinfo:
    service.create_project({})

assert "Project name is required" in str(excinfo.value)
assert excinfo.type is ValueError
```

#### 3.3 Fixture Request Context
```python
# New pattern for dynamic fixture behavior
@pytest.fixture
def api_client(request):
    """API client with request context."""
    # Access test metadata
    markers = request.node.iter_markers()
    timeout = next((m.args[0] for m in markers if m.name == "timeout"), 30)
    
    # Access module/class attributes
    base_url = getattr(request.module, "API_BASE_URL", "http://localhost:8000")
    
    return APIClient(base_url=base_url, timeout=timeout)
```

### Phase 4: Advanced Patterns

#### 4.1 Indirect Parametrization
```python
# For expensive setup in fixtures
@pytest.fixture
def initialized_service(request):
    """Service initialized with different configs."""
    config = request.param
    service = ProjectService(**config)
    service.initialize()
    yield service
    service.cleanup()

@pytest.mark.parametrize(
    "initialized_service",
    [
        {"cache_enabled": True},
        {"cache_enabled": False},
    ],
    indirect=True
)
def test_service_behavior(initialized_service):
    ...
```

#### 4.2 Autouse Fixtures for Safety
```python
@pytest.fixture(autouse=True)
def prevent_network_calls(monkeypatch):
    """Prevent accidental network calls in unit tests."""
    def error(*args, **kwargs):
        raise RuntimeError("Network call attempted in unit test!")
    
    monkeypatch.setattr("requests.get", error)
    monkeypatch.setattr("aiohttp.ClientSession", error)
```

#### 4.3 Temporary Directory Fixtures
```python
# Before - manual temp file handling
def test_file_processing():
    with tempfile.TemporaryDirectory() as tmpdir:
        ...

# After - using pytest fixtures
def test_file_processing(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert test_file.read_text() == "content"
```

### Phase 5: Logging and Debugging

#### 5.1 Enhanced Logging Tests
```python
def test_service_logging(caplog):
    """Test logging with specific level filtering."""
    with caplog.at_level(logging.WARNING, logger="archon.services"):
        service.risky_operation()
    
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "risky" in warnings[0].message
```

#### 5.2 Output Capture
```python
def test_cli_output(capsys):
    """Test CLI output capture."""
    cli.run_command(["--help"])
    captured = capsys.readouterr()
    
    assert "Usage:" in captured.out
    assert captured.err == ""
```

### Phase 6: Performance Testing

#### 6.1 Duration Tracking
```python
@pytest.mark.timeout(5)  # Fail if takes > 5 seconds
def test_search_performance(benchmark):
    """Benchmark search performance."""
    result = benchmark(search_service.search, "query", limit=100)
    assert len(result) <= 100
```

#### 6.2 Memory Testing
```python
@pytest.fixture
def memory_tracker():
    """Track memory usage during test."""
    import tracemalloc
    tracemalloc.start()
    
    yield
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Alert if > 100MB used
    if peak > 100 * 1024 * 1024:
        pytest.fail(f"Peak memory usage too high: {peak / 1024 / 1024:.1f}MB")
```

### Phase 7: CI/CD Optimizations

#### 7.1 Marker-based Test Selection
```bash
# Run only critical tests in PR checks
pytest -m "critical and not slow"

# Run full suite nightly
pytest

# Run integration tests with retries
pytest -m integration --reruns 3 --reruns-delay 2
```

#### 7.2 Parallel Execution
```ini
# pytest.ini
[pytest]
addopts = -n auto  # Use pytest-xdist for parallel execution
```

### Phase 8: Documentation and Reporting

#### 8.1 Docstring Standards
```python
def test_project_creation():
    """Test project creation with valid data.
    
    Given: Valid project data with name and description
    When: create_project is called
    Then: Project is created with generated ID and timestamps
    
    Regression test for: ARCH-123
    """
```

#### 8.2 Custom Markers with Metadata
```python
@pytest.mark.issue("ARCH-456")
@pytest.mark.requirement("Projects must have unique names")
def test_duplicate_project_names():
    """Ensure duplicate project names are rejected."""
```

## Implementation Priority

1. **Immediate (Week 1)**
   - Update pytest.ini with strict configuration
   - Implement hierarchical conftest structure
   - Add autouse safety fixtures

2. **Short-term (Week 2-3)**
   - Refactor fixtures with proper scoping
   - Implement factory fixtures
   - Enhance parametrization with IDs

3. **Medium-term (Week 4-6)**
   - Add performance benchmarks
   - Implement indirect parametrization
   - Enhance exception testing

4. **Long-term (Month 2+)**
   - Complete marker system
   - Add memory tracking
   - Implement parallel execution

## Metrics for Success

- **Performance**: 50% reduction in test suite execution time
- **Clarity**: All tests have meaningful IDs in reports
- **Safety**: Zero accidental network calls or database writes
- **Maintainability**: Fixture reuse increased by 40%
- **Coverage**: Maintained at 95%+ with better edge cases

## Migration Strategy

1. Create new fixture structure alongside existing
2. Gradually migrate tests to use new fixtures
3. Update CI/CD to use new markers
4. Deprecate old patterns
5. Document new patterns in contributor guide

This refactoring will result in a more maintainable, efficient, and professional test suite that follows pytest best practices and provides better debugging capabilities.