"""Test helper utilities for the Archon test suite.

This module provides helper functions for common testing patterns including:
- Async test utilities
- Mock creation and configuration
- Performance measurement
- Data validation
- WebSocket/SSE testing
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, TypeVar, Union
from unittest.mock import AsyncMock, Mock, call

import pytest


T = TypeVar('T')


# =============================================================================
# Async Testing Utilities
# =============================================================================

async def async_timeout(coro, timeout: float = 1.0):
    """Run an async function with a timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        pytest.fail(f"Async operation timed out after {timeout}s")


async def async_retry(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 0.1,
    exceptions: tuple = (Exception,)
):
    """Retry an async function on failure."""
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
    
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("No exception captured but retry failed")


@asynccontextmanager
async def async_raises(exception_type: type, match: Optional[str] = None):
    """Async context manager for asserting exceptions."""
    with pytest.raises(exception_type, match=match) as exc_info:
        yield exc_info


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met"
):
    """Wait for a condition to become true."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return
        await asyncio.sleep(interval)
    
    pytest.fail(f"{message} after {timeout}s")


# =============================================================================
# Mock Creation Helpers
# =============================================================================

def create_async_mock(spec=None, **kwargs) -> AsyncMock:
    """Create an AsyncMock with common configurations."""
    mock = AsyncMock(spec=spec)
    
    # Set default return values
    for key, value in kwargs.items():
        setattr(mock, key, AsyncMock(return_value=value))
    
    return mock


def create_mock_response(
    status_code: int = 200,
    json_data: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    raise_for_status: bool = True
) -> Mock:
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=json_data or {})
    response.text = text or json.dumps(json_data or {})
    response.headers = headers or {"content-type": "application/json"}
    
    if raise_for_status and status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        response.raise_for_status = Mock()
    
    return response


def create_mock_websocket(
    messages: Optional[List[Dict[str, Any]]] = None,
    close_after: Optional[int] = None
) -> AsyncMock:
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.closed = False
    
    message_queue = messages or []
    message_index = 0
    
    async def receive_json():
        nonlocal message_index
        if close_after and message_index >= close_after:
            ws.closed = True
            raise ConnectionError("WebSocket closed")
        
        if message_index < len(message_queue):
            msg = message_queue[message_index]
            message_index += 1
            return msg
        
        # Wait indefinitely if no more messages
        await asyncio.sleep(3600)
    
    ws.receive_json = receive_json
    ws.send_json = AsyncMock()
    ws.close = AsyncMock(side_effect=lambda: setattr(ws, 'closed', True))
    
    return ws


def create_mock_sse_client(events: Optional[List[Dict[str, Any]]] = None) -> Mock:
    """Create a mock SSE client."""
    client = Mock()
    event_queue = events or []
    event_index = 0
    
    def iterate_events():
        nonlocal event_index
        while event_index < len(event_queue):
            event = event_queue[event_index]
            event_index += 1
            yield event
    
    client.events = Mock(return_value=iterate_events())
    client.close = Mock()
    
    return client


# =============================================================================
# Performance Measurement
# =============================================================================

@contextmanager
def measure_time(name: str = "Operation", threshold: Optional[float] = None):
    """Measure execution time of a code block."""
    start_time = time.perf_counter()
    
    yield
    
    duration = time.perf_counter() - start_time
    print(f"{name} took {duration:.3f}s")
    
    if threshold and duration > threshold:
        pytest.fail(f"{name} took {duration:.3f}s, exceeding threshold of {threshold}s")


@asynccontextmanager
async def async_measure_time(name: str = "Async Operation", threshold: Optional[float] = None):
    """Measure execution time of an async code block."""
    start_time = time.perf_counter()
    
    yield
    
    duration = time.perf_counter() - start_time
    print(f"{name} took {duration:.3f}s")
    
    if threshold and duration > threshold:
        pytest.fail(f"{name} took {duration:.3f}s, exceeding threshold of {threshold}s")


class PerformanceTracker:
    """Track performance metrics across multiple operations."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    @contextmanager
    def track(self, operation: str):
        """Track a single operation."""
        start_time = time.perf_counter()
        
        yield
        
        duration = time.perf_counter() - start_time
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return {"count": 0, "total": 0, "average": 0, "min": 0, "max": 0}
        
        times = self.metrics[operation]
        return {
            "count": len(times),
            "total": sum(times),
            "average": sum(times) / len(times),
            "min": min(times),
            "max": max(times)
        }
    
    def print_report(self):
        """Print a performance report."""
        print("\n=== Performance Report ===")
        for operation, times in self.metrics.items():
            stats = self.get_stats(operation)
            print(f"{operation}:")
            print(f"  Count: {stats['count']}")
            print(f"  Average: {stats['average']:.3f}s")
            print(f"  Min: {stats['min']:.3f}s")
            print(f"  Max: {stats['max']:.3f}s")


# =============================================================================
# Data Validation Helpers
# =============================================================================

def assert_valid_uuid(value: str, field_name: str = "id"):
    """Assert that a value is a valid UUID-like string."""
    import re
    uuid_pattern = r'^[a-zA-Z0-9_-]+$'
    assert re.match(uuid_pattern, value), f"{field_name} is not a valid ID: {value}"


def assert_valid_iso_datetime(value: str, field_name: str = "timestamp"):
    """Assert that a value is a valid ISO datetime string."""
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        pytest.fail(f"{field_name} is not a valid ISO datetime: {value} - {e}")


def assert_valid_json(value: Union[str, dict], field_name: str = "data"):
    """Assert that a value is valid JSON."""
    if isinstance(value, str):
        try:
            json.loads(value)
        except json.JSONDecodeError as e:
            pytest.fail(f"{field_name} is not valid JSON: {e}")
    elif not isinstance(value, dict):
        pytest.fail(f"{field_name} must be a JSON string or dict")


def assert_fields_equal(obj1: dict, obj2: dict, fields: List[str], obj_names: tuple = ("actual", "expected")):
    """Assert that specific fields are equal between two objects."""
    for field in fields:
        actual = obj1.get(field)
        expected = obj2.get(field)
        assert actual == expected, (
            f"{field} mismatch:\n"
            f"  {obj_names[0]}: {actual}\n"
            f"  {obj_names[1]}: {expected}"
        )


def assert_subset(subset: dict, superset: dict, path: str = ""):
    """Assert that subset is contained in superset (deep comparison)."""
    for key, expected_value in subset.items():
        current_path = f"{path}.{key}" if path else key
        
        assert key in superset, f"Key '{current_path}' not found in superset"
        
        actual_value = superset[key]
        
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            assert_subset(expected_value, actual_value, current_path)
        else:
            assert actual_value == expected_value, (
                f"Value mismatch at '{current_path}':\n"
                f"  expected: {expected_value}\n"
                f"  actual: {actual_value}"
            )


# =============================================================================
# WebSocket Testing Helpers
# =============================================================================

class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.receive_queue: asyncio.Queue = asyncio.Queue()
        self.closed = False
    
    async def send_json(self, data: Dict[str, Any]):
        """Send a JSON message."""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        self.sent_messages.append(data)
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive a JSON message."""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        
        # Wait for a message with timeout
        try:
            return await asyncio.wait_for(self.receive_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            raise ConnectionError("No message received")
    
    async def close(self):
        """Close the connection."""
        self.closed = True
    
    async def inject_message(self, data: Dict[str, Any]):
        """Inject a message into the receive queue (for testing)."""
        await self.receive_queue.put(data)


# =============================================================================
# SSE Testing Helpers
# =============================================================================

class MockSSEClient:
    """Mock SSE client for testing."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.closed = False
    
    def send_event(self, event: str, data: Any, id: Optional[str] = None):
        """Send an SSE event."""
        if self.closed:
            raise ConnectionError("SSE connection is closed")
        
        self.events.append({
            "event": event,
            "data": json.dumps(data) if not isinstance(data, str) else data,
            "id": id
        })
    
    def close(self):
        """Close the SSE connection."""
        self.closed = True
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all sent events."""
        return self.events.copy()


# =============================================================================
# Test Data Builders
# =============================================================================

class TestDataBuilder:
    """Builder pattern for creating test data."""
    
    def __init__(self, base_data: Optional[Dict[str, Any]] = None):
        self.data = base_data or {}
    
    def set(self, key: str, value: Any) -> 'TestDataBuilder':
        """Set a field value."""
        self.data[key] = value
        return self
    
    def update(self, **kwargs) -> 'TestDataBuilder':
        """Update multiple fields."""
        self.data.update(kwargs)
        return self
    
    def remove(self, key: str) -> 'TestDataBuilder':
        """Remove a field."""
        self.data.pop(key, None)
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the final data object."""
        return self.data.copy()


# =============================================================================
# Mock Call Assertions
# =============================================================================

def assert_called_with_subset(mock: Mock, **expected_kwargs):
    """Assert that a mock was called with arguments containing the expected subset."""
    assert mock.called, "Mock was not called"
    
    actual_kwargs = mock.call_args.kwargs
    for key, expected_value in expected_kwargs.items():
        assert key in actual_kwargs, f"Expected key '{key}' not found in call arguments"
        actual_value = actual_kwargs[key]
        
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            assert_subset(expected_value, actual_value, key)
        else:
            assert actual_value == expected_value, (
                f"Argument '{key}' mismatch:\n"
                f"  expected: {expected_value}\n"
                f"  actual: {actual_value}"
            )


def assert_not_called_with(mock: Mock, **kwargs):
    """Assert that a mock was not called with specific arguments."""
    for call_args in mock.call_args_list:
        if all(call_args.kwargs.get(k) == v for k, v in kwargs.items()):
            pytest.fail(f"Mock was called with forbidden arguments: {kwargs}")


def get_call_by_args(mock: Mock, **kwargs) -> Optional[call]:
    """Get a specific call by matching arguments."""
    for mock_call in mock.call_args_list:
        if all(mock_call.kwargs.get(k) == v for k, v in kwargs.items()):
            return mock_call
    return None


# =============================================================================
# Environment Helpers
# =============================================================================

@contextmanager
def temporary_env(**env_vars):
    """Temporarily set environment variables."""
    import os
    
    old_environ = os.environ.copy()
    os.environ.update({k: str(v) for k, v in env_vars.items()})
    
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


# =============================================================================
# Async Generator Helpers
# =============================================================================

async def async_list(async_gen: AsyncIterator[T]) -> List[T]:
    """Convert an async generator to a list."""
    return [item async for item in async_gen]


async def async_take(async_gen: AsyncIterator[T], n: int) -> List[T]:
    """Take first n items from an async generator."""
    items = []
    async for item in async_gen:
        items.append(item)
        if len(items) >= n:
            break
    return items


# =============================================================================
# Database Testing Helpers
# =============================================================================

class DatabaseTestHelper:
    """Helper for database-related tests."""
    
    @staticmethod
    def create_mock_query_result(data: List[Dict[str, Any]], count: Optional[int] = None) -> Mock:
        """Create a mock database query result."""
        result = Mock()
        result.data = data
        result.count = count if count is not None else len(data)
        return result
    
    @staticmethod
    def create_mock_transaction() -> Mock:
        """Create a mock database transaction."""
        transaction = Mock()
        transaction.__enter__ = Mock(return_value=transaction)
        transaction.__exit__ = Mock(return_value=None)
        transaction.commit = AsyncMock()
        transaction.rollback = AsyncMock()
        return transaction


# =============================================================================
# Error Testing Helpers
# =============================================================================

def assert_error_response(response: dict, expected_status: int, expected_message: Optional[str] = None):
    """Assert that a response is an error with expected properties."""
    assert "error" in response, "Response does not contain 'error' field"
    assert response.get("status") == expected_status, f"Expected status {expected_status}, got {response.get('status')}"
    
    if expected_message:
        actual_message = response.get("error", {}).get("message", "")
        assert expected_message in actual_message, (
            f"Expected message to contain '{expected_message}', "
            f"got '{actual_message}'"
        )


# =============================================================================
# Fixture Request Helpers
# =============================================================================

def parametrize_fixture(
    request: Any,  # Using Any to avoid pytest import issues
    param_name: str,
    default: Any = None
) -> Any:
    """Get a parametrized value from the fixture request."""
    if hasattr(request, "param") and isinstance(request.param, dict):
        return request.param.get(param_name, default)
    return default