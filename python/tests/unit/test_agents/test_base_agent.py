"""Unit tests for BaseAgent."""
import pytest
from typing import Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from dataclasses import dataclass
from pydantic import BaseModel
from src.agents.base_agent import BaseAgent, ArchonDependencies, RateLimitHandler, BaseAgentOutput


# Test implementations of BaseAgent
@dataclass
class TestDependencies(ArchonDependencies):
    """Test dependencies."""
    test_value: str = "test"
    progress_callback: Optional[callable] = None


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


class TestBaseAgent:
    """Unit tests for BaseAgent."""
    
    @pytest.fixture
    def test_agent(self):
        """Create test agent instance."""
        return TestAgent(name="TestAgent", enable_rate_limiting=True)
    
    @pytest.fixture
    def test_deps(self):
        """Create test dependencies."""
        return TestDependencies(
            request_id="test-request-123",
            user_id="test-user",
            test_value="test-data"
        )
    
    @pytest.fixture
    def mock_run_result(self):
        """Mock run result."""
        result = MagicMock()
        result.data = TestOutput(result="success", count=42)
        return result
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_base_agent_provides_common_functionality(self, test_agent):
        """Test that base agent provides common functionality."""
        # Verify agent initialization
        assert test_agent.name == "TestAgent"
        assert test_agent.model == "openai:gpt-4o"
        assert test_agent.retries == 3
        assert test_agent.enable_rate_limiting is True
        assert test_agent.rate_limiter is not None
        
        # Verify abstract methods are implemented
        assert test_agent.get_system_prompt() == "Test system prompt"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_base_agent_handles_rate_limiting(self, test_agent, test_deps):
        """Test rate limiting functionality."""
        # Mock the internal agent to raise rate limit error first, then succeed
        test_agent._agent.run.side_effect = [
            Exception("Rate limit exceeded"),
            MagicMock(data=TestOutput(result="success", count=1))
        ]
        
        with patch('asyncio.sleep', return_value=None):  # Speed up test
            # Act
            result = await test_agent.run("test prompt", test_deps)
            
            # Assert
            assert result.result == "success"
            assert test_agent._agent.run.call_count == 2  # First failed, second succeeded
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_base_agent_supports_streaming(self, test_agent, test_deps):
        """Test streaming functionality."""
        # Mock streaming response
        mock_stream = AsyncMock()
        test_agent._agent.run_stream.return_value = mock_stream
        
        # Act
        result = await test_agent.run_stream("test prompt", test_deps)
        
        # Assert
        assert result == mock_stream
        test_agent._agent.run_stream.assert_called_once_with("test prompt", deps=test_deps)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_base_agent_handles_errors_gracefully(self, test_agent, test_deps):
        """Test error handling."""
        # Mock agent to raise non-rate-limit error
        test_agent._agent.run.side_effect = ValueError("Invalid input")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid input"):
            await test_agent.run("test prompt", test_deps)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_base_agent_implements_retry_logic(self, test_agent, test_deps):
        """Test retry logic with exponential backoff."""
        # Mock agent to fail multiple times with rate limit
        test_agent._agent.run.side_effect = [
            Exception("429 Too Many Requests"),
            Exception("Rate limit exceeded"),
            MagicMock(data=TestOutput(result="finally", count=3))
        ]
        
        with patch('asyncio.sleep', return_value=None) as mock_sleep:
            # Act
            result = await test_agent.run("test prompt", test_deps)
            
            # Assert
            assert result.result == "finally"
            assert test_agent._agent.run.call_count == 3
            # Verify exponential backoff was used
            assert mock_sleep.call_count == 2  # Two retries
    
    @pytest.mark.unit
    def test_rate_limit_handler_extracts_wait_time(self):
        """Test RateLimitHandler extracts wait time from error messages."""
        handler = RateLimitHandler()
        
        # Test various error message formats
        assert handler._extract_wait_time("Please try again in 1.5s") == 1.5
        assert handler._extract_wait_time("try again in 2.0s after") == 2.0
        assert handler._extract_wait_time("No wait time here") is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_agent_timeout_protection(self, test_agent, test_deps):
        """Test agent has timeout protection."""
        # Mock agent to hang indefinitely
        async def hang_forever(*args, **kwargs):
            await asyncio.sleep(300)  # 5 minutes
        
        test_agent._agent.run.side_effect = hang_forever
        
        # Act & Assert
        with pytest.raises(Exception, match="timed out"):
            await test_agent.run("test prompt", test_deps)
    
    @pytest.mark.unit
    def test_add_tool_functionality(self, test_agent):
        """Test adding tools to the agent."""
        # Define a test tool
        def test_tool(x: int) -> int:
            return x * 2
        
        # Act
        test_agent.add_tool(test_tool)
        
        # Assert
        test_agent._agent.tool.assert_called_once()
    
    @pytest.mark.unit
    def test_add_system_prompt_function(self, test_agent):
        """Test adding dynamic system prompt."""
        # Define a test system prompt function
        def dynamic_prompt(context):
            return f"Dynamic prompt for {context}"
        
        # Act
        test_agent.add_system_prompt_function(dynamic_prompt)
        
        # Assert
        test_agent._agent.system_prompt.assert_called_once_with(dynamic_prompt)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_progress_callback_integration(self, test_agent):
        """Test progress callback is used during rate limiting."""
        # Create deps with progress callback
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        deps = TestDependencies(progress_callback=progress_callback)
        
        # Mock rate limit error then success
        test_agent._agent.run.side_effect = [
            Exception("rate limit exceeded"),
            MagicMock(data=TestOutput(result="done", count=1))
        ]
        
        with patch('asyncio.sleep', return_value=None):
            # Act
            await test_agent.run("test", deps)
            
            # Assert - Should have progress update about rate limit
            assert len(progress_updates) > 0
            assert any("Rate limit" in str(u.get('log', '')) for u in progress_updates)