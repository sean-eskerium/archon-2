"""Test helper functions and utilities."""
import asyncio
from typing import Dict, Any, Optional, List, Callable
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime


class TestHelpers:
    """Collection of test helper utilities."""
    
    @staticmethod
    def mock_supabase_response(data: Any = None, error: Any = None):
        """Create a mock Supabase response."""
        response = MagicMock()
        response.data = data
        response.error = error
        response.count = len(data) if isinstance(data, list) else 1
        return response
    
    @staticmethod
    def mock_async_response(data: Any = None, error: Any = None):
        """Create a mock async response."""
        async def _response():
            return data if error is None else error
        return _response()
    
    @staticmethod
    @asynccontextmanager
    async def mock_websocket_connection():
        """Mock WebSocket connection context manager."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.close = AsyncMock()
        
        yield ws
        
        # Cleanup
        await ws.close()
    
    @staticmethod
    @contextmanager
    def mock_environment_variables(env_vars: Dict[str, str]):
        """Temporarily set environment variables."""
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            yield
        finally:
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    @staticmethod
    def create_mock_file_upload(
        filename: str = "test.txt",
        content: bytes = b"test content",
        content_type: str = "text/plain"
    ):
        """Create a mock file upload object."""
        from io import BytesIO
        
        file = MagicMock()
        file.filename = filename
        file.content_type = content_type
        file.file = BytesIO(content)
        file.read = AsyncMock(return_value=content)
        
        return file
    
    @staticmethod
    async def mock_stream_response(messages: List[str], delay: float = 0.1):
        """Mock a streaming response."""
        for message in messages:
            yield message
            await asyncio.sleep(delay)
    
    @staticmethod
    def assert_database_called_with(mock_db, table: str, method: str, **kwargs):
        """Assert database was called with specific parameters."""
        mock_db.table.assert_called_with(table)
        getattr(mock_db.table.return_value, method).assert_called()
        
        if kwargs:
            for key, value in kwargs.items():
                method_mock = getattr(mock_db.table.return_value, key)
                method_mock.assert_called_with(value)
    
    @staticmethod
    def create_mock_mcp_tool_response(
        tool_name: str,
        result: Any = None,
        error: Optional[str] = None
    ):
        """Create a mock MCP tool response."""
        if error:
            return {
                "error": {
                    "code": -32603,
                    "message": error
                }
            }
        
        return {
            "result": result or {"success": True},
            "tool": tool_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def create_mock_llm_response(
        content: str = "Test response",
        model: str = "gpt-4",
        usage: Optional[Dict[str, int]] = None
    ):
        """Create a mock LLM response."""
        return MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content=content),
                    finish_reason="stop"
                )
            ],
            model=model,
            usage=usage or {"prompt_tokens": 10, "completion_tokens": 20}
        )
    
    @staticmethod
    def assert_websocket_sent_json(mock_ws, expected_data: Dict[str, Any]):
        """Assert WebSocket sent specific JSON data."""
        calls = mock_ws.send_json.call_args_list
        for call in calls:
            if call[0][0] == expected_data:
                return True
        
        raise AssertionError(
            f"WebSocket did not send expected data: {expected_data}\n"
            f"Actual calls: {[call[0][0] for call in calls]}"
        )
    
    @staticmethod
    @contextmanager
    def capture_logs(logger_name: str = ""):
        """Capture log messages for testing."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        try:
            yield log_capture
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
    
    @staticmethod
    def mock_datetime_now(target_datetime: datetime):
        """Mock datetime.now() to return a specific time."""
        return patch('datetime.datetime') \
            .start() \
            .now \
            .return_value \
            .__eq__(target_datetime)
    
    @staticmethod
    async def wait_for_condition(
        condition_func: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False


# Convenience instance
test_helpers = TestHelpers()