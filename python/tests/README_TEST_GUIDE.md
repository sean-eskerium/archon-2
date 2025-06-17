# Archon Python Test Suite Guide

This guide explains how to run and use the Archon Python test suite.

## Quick Start

### Running All Tests
```bash
cd python
python tests/run_tests.py
```

### Running Specific Test Types
```bash
# Unit tests only
python tests/run_tests.py unit

# Integration tests only  
python tests/run_tests.py integration

# End-to-end tests only
python tests/run_tests.py e2e
```

### Running Without Coverage
```bash
python tests/run_tests.py --no-coverage
```

## Test Structure

```
tests/
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_services/       # Service layer tests
│   ├── test_modules/        # MCP module tests
│   └── test_utils/          # Utility tests
├── integration/             # Integration tests (with mocked external services)
│   ├── test_api/            # API endpoint tests
│   ├── test_mcp/            # MCP server tests
│   └── test_websockets/     # WebSocket tests
├── e2e/                     # End-to-end tests
│   └── test_workflows/      # Complete workflow tests
└── fixtures/                # Test data and helpers
```

## Running Individual Test Files

```bash
# Run a specific test file
python -m pytest tests/unit/test_services/test_projects/test_project_service.py

# Run with verbose output
python -m pytest -v tests/unit/test_services/test_projects/test_project_service.py

# Run a specific test function
python -m pytest tests/unit/test_services/test_projects/test_project_service.py::TestProjectService::test_project_service_creates_project_with_valid_data
```

## Test Markers

Tests are marked with categories for selective execution:

```bash
# Run only unit tests
python -m pytest -m unit

# Run only tests requiring database
python -m pytest -m requires_db

# Run tests excluding slow ones
python -m pytest -m "not slow"
```

## Coverage Reports

After running tests with coverage, view the HTML report:
```bash
# Open coverage report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Writing New Tests

### Unit Test Template
```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.your_service import YourService

class TestYourService:
    @pytest.fixture
    def mock_dependency(self):
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_dependency):
        return YourService(dependency=mock_dependency)
    
    @pytest.mark.unit
    def test_service_method(self, service, mock_dependency):
        # Arrange
        mock_dependency.some_method.return_value = "expected"
        
        # Act
        result = service.method_to_test()
        
        # Assert
        assert result == "expected"
        mock_dependency.some_method.assert_called_once()
```

### Using Test Fixtures

Common fixtures are available in `conftest.py`:
- `mock_supabase_client`: Mocked Supabase client
- `mock_credential_service`: Mocked credential service
- `sample_project`: Sample project data
- `sample_task`: Sample task data

### Using Mock Data Factory

```python
from tests.fixtures.mock_data import mock_factory

# Create single items
project = mock_factory.create_project(title="Custom Project")
task = mock_factory.create_task(status="doing")

# Create batches
projects = mock_factory.create_batch(mock_factory.create_project, count=5)
```

## Environment Variables

Tests run with `TESTING=true` environment variable set automatically.

Additional test environment variables can be set in `.env.test`:
```
SUPABASE_URL=http://test.supabase.co
SUPABASE_ANON_KEY=test-key
```

## Debugging Tests

### Run with debugger
```bash
# Using pytest's built-in debugger
python -m pytest --pdb tests/unit/test_services/test_projects/test_project_service.py

# Stop on first failure
python -m pytest -x tests/unit
```

### Show print statements
```bash
python -m pytest -s tests/unit
```

## CI/CD Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    cd python
    python tests/run_tests.py --no-coverage
```

## Best Practices

1. **Always mock external dependencies** - Database, APIs, file system
2. **Use descriptive test names** - `test_service_creates_item_with_valid_data`
3. **Follow AAA pattern** - Arrange, Act, Assert
4. **One assertion per test** - Keep tests focused
5. **Use fixtures** - Don't repeat setup code
6. **Mock at the boundary** - Mock external calls, not internal methods
7. **Test edge cases** - Empty data, None values, errors

## Troubleshooting

### Import Errors
- Ensure you're running from the `python` directory
- The test runner adds `src` to Python path automatically

### Database Connection Errors
- Tests should not connect to real database
- Check that mocks are properly configured

### Async Test Issues
- Use `@pytest.mark.asyncio` for async tests
- Use `AsyncMock` for async dependencies

## Coverage Goals

- Service Layer: 95%
- API Endpoints: 90%
- MCP Tools: 90%
- Utils: 95%
- Overall: 80%