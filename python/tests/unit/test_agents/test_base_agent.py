"""Unit tests for BaseAgent with enhanced patterns and parametrization."""

import pytest
from typing import Optional, List, Dict, Any
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from dataclasses import dataclass
from pydantic import BaseModel

from src.agents.base_agent import BaseAgent, ArchonDependencies, RateLimitHandler, BaseAgentOutput
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time,
    async_timeout
)


# Test implementations of BaseAgent
@dataclass
class TestDependencies(ArchonDependencies):
    """Test dependencies."""
    test_value: str = "test"
    progress_callback: Optional[Any] = None


class TestOutput(BaseModel):
    """Test output model."""
    result: str
    count: int


class TestAgent(BaseAgent[TestDependencies, TestOutput]):
    """Test implementation of BaseAgent."""
    
    def _create_agent(self, **kwargs):
        """Create mock agent."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock()
        mock_agent.run_stream = AsyncMock()
        mock_agent.tool = MagicMock(return_value=lambda func: func)
        mock_agent.system_prompt = MagicMock(return_value=lambda func: func)
        return mock_agent
    
    def get_system_prompt(self) -> str:
        """Return test system prompt."""
        return "Test system prompt"


@pytest.mark.unit
@pytest.mark.standard
class TestBaseAgent:
    """Unit tests for BaseAgent with enhanced patterns."""
    
    @pytest.fixture
    def make_test_agent(self):
        """Factory for creating test agents with custom configs."""
        def _make_agent(
            name: str = "TestAgent",
            model: str = "openai:gpt-4o",
            enable_rate_limiting: bool = True,
            retries: int = 3,
            temperature: float = 0.7
        ) -> TestAgent:
            return TestAgent(
                name=name,
                model=model,
                enable_rate_limiting=enable_rate_limiting,
                retries=retries,
                temperature=temperature
            )
        return _make_agent
    
    @pytest.fixture
    def test_agent(self, make_test_agent):
        """Create default test agent instance."""
        return make_test_agent()
    
    @pytest.fixture
    def make_test_deps(self):
        """Factory for creating test dependencies."""
        def _make_deps(
            request_id: Optional[str] = None,
            user_id: Optional[str] = None,
            test_value: str = "test-data",
            progress_callback: Optional[Any] = None
        ) -> TestDependencies:
            return TestDependencies(
                request_id=request_id or f"test-request-{IDGenerator('REQ').generate()}",
                user_id=user_id or f"test-user-{IDGenerator('USR').generate()}",
                test_value=test_value,
                progress_callback=progress_callback
            )
        return _make_deps
    
    @pytest.fixture
    def test_deps(self, make_test_deps):
        """Create default test dependencies."""
        return make_test_deps()
    
    @pytest.fixture
    def make_mock_result(self):
        """Factory for creating mock results."""
        def _make_result(result: str = "success", count: int = 42) -> MagicMock:
            mock = MagicMock()
            mock.data = TestOutput(result=result, count=count)
            return mock
        return _make_result
    
    # =============================================================================
    # Initialization and Configuration Tests
    # =============================================================================
    
    @pytest.mark.parametrize("config", [
        pytest.param(
            {"name": "Agent1", "model": "openai:gpt-4o", "enable_rate_limiting": True},
            id="standard-config"
        ),
        pytest.param(
            {"name": "Agent2", "model": "anthropic:claude-3", "enable_rate_limiting": False},
            id="no-rate-limiting"
        ),
        pytest.param(
            {"name": "Agent3", "model": "openai:gpt-3.5-turbo", "retries": 5, "temperature": 0.2},
            id="custom-retries-temp"
        ),
    ])
    def test_agent_initialization_with_configs(self, make_test_agent, config):
        """Test agent initialization with various configurations."""
        # Act
        agent = make_test_agent(**config)
        
        # Assert
        assert_fields_equal(agent, config)
        
        if config.get("enable_rate_limiting", True):
            assert agent.rate_limiter is not None
        else:
            assert agent.rate_limiter is None
    
    # =============================================================================
    # Rate Limiting Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    @pytest.mark.parametrize("error_sequence,expected_calls", [
        pytest.param(
            [Exception("Rate limit exceeded"), "success"],
            2,
            id="single-retry"
        ),
        pytest.param(
            [Exception("429 Too Many Requests"), Exception("rate limit"), "success"],
            3,
            id="double-retry"
        ),
        pytest.param(
            [Exception("503 Service Unavailable"), "success"],
            1,  # Non-rate-limit error, no retry
            id="non-rate-limit-error"
        ),
    ])
    async def test_rate_limiting_retry_behavior(
        self,
        test_agent,
        test_deps,
        make_mock_result,
        error_sequence,
        expected_calls
    ):
        """Test rate limiting retry behavior with various error sequences."""
        # Arrange
        side_effects = []
        for item in error_sequence:
            if isinstance(item, str):
                side_effects.append(make_mock_result(result=item))
            else:
                side_effects.append(item)
        
        test_agent._agent.run.side_effect = side_effects
        
        with patch('asyncio.sleep', return_value=None):
            # Act
            if expected_calls == 1 and isinstance(error_sequence[0], Exception) and "503" in str(error_sequence[0]):
                # Non-rate-limit error should be raised
                with pytest.raises(Exception, match="503"):
                    await test_agent.run("test prompt", test_deps)
            else:
                result = await test_agent.run("test prompt", test_deps)
                
                # Assert
                assert result.result == "success"
                assert test_agent._agent.run.call_count == expected_calls
    
    @pytest.mark.parametrize("error_message,expected_wait_time", [
        pytest.param("Please try again in 1.5s", 1.5, id="decimal-seconds"),
        pytest.param("try again in 2.0s after", 2.0, id="embedded-time"),
        pytest.param("retry after 60s", 60.0, id="whole-seconds"),
        pytest.param("No wait time here", None, id="no-time-found"),
        pytest.param("wait 0.5s then retry", 0.5, id="fractional-second"),
    ])
    def test_rate_limit_handler_time_extraction(self, error_message, expected_wait_time):
        """Test RateLimitHandler extracts wait time from various error formats."""
        # Arrange
        handler = RateLimitHandler()
        
        # Act
        wait_time = handler._extract_wait_time(error_message)
        
        # Assert
        assert wait_time == expected_wait_time
    
    @pytest.mark.asyncio
    @pytest.mark.flaky(reruns=3)  # Network-like behavior can be flaky
    async def test_exponential_backoff_timing(self, test_agent, test_deps, make_mock_result):
        """Test exponential backoff timing for rate limit retries."""
        # Arrange
        test_agent._agent.run.side_effect = [
            Exception("rate limit"),
            Exception("rate limit"),
            make_mock_result()
        ]
        
        sleep_calls = []
        async def mock_sleep(duration):
            sleep_calls.append(duration)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            # Act
            await test_agent.run("test", test_deps)
            
            # Assert - Verify exponential backoff
            assert len(sleep_calls) == 2
            assert sleep_calls[1] > sleep_calls[0]  # Backoff increases
    
    # =============================================================================
    # Streaming Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_streaming_functionality(self, test_agent, test_deps):
        """Test streaming functionality with proper async iteration."""
        # Arrange
        async def mock_stream():
            for i in range(3):
                yield f"chunk_{i}"
        
        test_agent._agent.run_stream.return_value = mock_stream()
        
        # Act
        stream = await test_agent.run_stream("test prompt", test_deps)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        
        # Assert
        assert chunks == ["chunk_0", "chunk_1", "chunk_2"]
        test_agent._agent.run_stream.assert_called_once_with("test prompt", deps=test_deps)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("stream_error_at", [0, 2, 5])
    async def test_streaming_error_handling(self, test_agent, test_deps, stream_error_at):
        """Test error handling during streaming at various points."""
        # Arrange
        async def mock_stream_with_error():
            for i in range(10):
                if i == stream_error_at:
                    raise ValueError(f"Stream error at chunk {i}")
                yield f"chunk_{i}"
        
        test_agent._agent.run_stream.return_value = mock_stream_with_error()
        
        # Act & Assert
        stream = await test_agent.run_stream("test", test_deps)
        chunks = []
        
        with pytest.raises(ValueError, match=f"Stream error at chunk {stream_error_at}"):
            async for chunk in stream:
                chunks.append(chunk)
        
        assert len(chunks) == stream_error_at
    
    # =============================================================================
    # Timeout Protection Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(2)  # Test timeout shorter than agent timeout
    @pytest.mark.parametrize("hang_duration,should_timeout", [
        pytest.param(0.1, False, id="quick-response"),
        pytest.param(5.0, True, id="slow-response"),
    ])
    async def test_timeout_protection(
        self,
        test_agent,
        test_deps,
        make_mock_result,
        hang_duration,
        should_timeout
    ):
        """Test agent timeout protection with various response times."""
        # Arrange
        async def mock_slow_response(*args, **kwargs):
            await asyncio.sleep(hang_duration)
            return make_mock_result()
        
        test_agent._agent.run.side_effect = mock_slow_response
        
        # Override default timeout for testing
        original_timeout = getattr(test_agent, 'timeout', None)
        test_agent.timeout = 1.0  # 1 second timeout
        
        try:
            # Act & Assert
            if should_timeout:
                with pytest.raises(Exception, match="timed out|timeout"):
                    await test_agent.run("test", test_deps)
            else:
                result = await test_agent.run("test", test_deps)
                assert result.result == "success"
        finally:
            if original_timeout:
                test_agent.timeout = original_timeout
    
    # =============================================================================
    # Tool and System Prompt Tests
    # =============================================================================
    
    @pytest.mark.parametrize("tool_count", [0, 1, 5, 10])
    def test_add_multiple_tools(self, test_agent, tool_count):
        """Test adding multiple tools to the agent."""
        # Arrange
        tools = []
        for i in range(tool_count):
            def tool(x: int, tool_id: int = i) -> int:
                return x * tool_id
            tools.append(tool)
        
        # Act
        for tool in tools:
            test_agent.add_tool(tool)
        
        # Assert
        assert test_agent._agent.tool.call_count == tool_count
    
    @pytest.mark.parametrize("prompt_type,expected_prompt", [
        pytest.param("static", "Static system prompt", id="static-prompt"),
        pytest.param("dynamic", "Dynamic prompt for context", id="dynamic-prompt"),
        pytest.param("empty", "", id="empty-prompt"),
    ])
    def test_system_prompt_variations(self, make_test_agent, prompt_type, expected_prompt):
        """Test various system prompt configurations."""
        # Arrange
        class CustomAgent(TestAgent):
            def get_system_prompt(self) -> str:
                if prompt_type == "dynamic":
                    return f"Dynamic prompt for {self.name}"
                elif prompt_type == "empty":
                    return ""
                else:
                    return expected_prompt
        
        # Act
        agent = CustomAgent(name="context")
        prompt = agent.get_system_prompt()
        
        # Assert
        if prompt_type == "dynamic":
            assert prompt == "Dynamic prompt for context"
        else:
            assert prompt == expected_prompt
    
    # =============================================================================
    # Progress Callback Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_progress_callback_during_operations(
        self,
        test_agent,
        make_test_deps,
        make_mock_result
    ):
        """Test progress callbacks are invoked during various operations."""
        # Arrange
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        deps = make_test_deps(progress_callback=progress_callback)
        
        # Mock rate limit then success
        test_agent._agent.run.side_effect = [
            Exception("rate limit exceeded"),
            make_mock_result()
        ]
        
        with patch('asyncio.sleep', return_value=None):
            # Act
            await test_agent.run("test", deps)
            
            # Assert
            assert len(progress_updates) > 0
            
            # Check for rate limit notification
            rate_limit_updates = [u for u in progress_updates if "rate limit" in str(u.get('log', '')).lower()]
            assert len(rate_limit_updates) > 0
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_requests", [10, 50, 100])
    async def test_concurrent_request_handling(
        self,
        make_test_agent,
        make_test_deps,
        make_mock_result,
        num_requests
    ):
        """Test handling multiple concurrent requests."""
        # Arrange
        agent = make_test_agent(enable_rate_limiting=False)  # Disable for performance test
        agent._agent.run.return_value = make_mock_result()
        
        # Act
        tasks = []
        for i in range(num_requests):
            deps = make_test_deps(request_id=f"req-{i}")
            tasks.append(agent.run(f"prompt-{i}", deps))
        
        with measure_time(f"concurrent_{num_requests}_requests", threshold=2.0):
            results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == num_requests
        assert all(r.result == "success" for r in results)
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,error_message", [
        pytest.param(ValueError, "Invalid input format", id="value-error"),
        pytest.param(TypeError, "Type mismatch", id="type-error"),
        pytest.param(RuntimeError, "Runtime failure", id="runtime-error"),
        pytest.param(Exception, "Generic error", id="generic-error"),
    ])
    async def test_error_propagation(
        self,
        test_agent,
        test_deps,
        error_type,
        error_message
    ):
        """Test that non-rate-limit errors are properly propagated."""
        # Arrange
        test_agent._agent.run.side_effect = error_type(error_message)
        
        # Act & Assert
        with pytest.raises(error_type, match=error_message):
            await test_agent.run("test", test_deps)