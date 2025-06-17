"""Unit tests for MCPClientService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from src.services.mcp_client_service import (
    MCPClientService, 
    MCPClientConfig, 
    MCPClientInfo,
    TransportType,
    ClientStatus
)
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_called_with_subset,
    async_timeout,
    measure_time,
    wait_for_condition
)


@pytest.mark.unit
@pytest.mark.critical
class TestMCPClientService:
    """Unit tests for MCPClientService with enhanced patterns."""
    
    @pytest.fixture
    def mcp_client_service(self):
        """Create MCPClientService instance with clean state."""
        return MCPClientService()
    
    @pytest.fixture
    def make_client_config(self):
        """Factory for creating MCP client configurations."""
        def _make_config(
            name: Optional[str] = None,
            transport_type: TransportType = TransportType.SSE,
            url: Optional[str] = None,
            auto_connect: bool = False,
            health_check_interval: int = 30,
            **kwargs
        ) -> MCPClientConfig:
            name = name or f"Test MCP Server {IDGenerator.generate('srv')}"
            url = url or f"http://localhost:{3000 + hash(name) % 1000}/sse"
            
            config = MCPClientConfig(
                name=name,
                transport_type=transport_type,
                connection_config={"url": url, **kwargs},
                auto_connect=auto_connect,
                health_check_interval=health_check_interval
            )
            return config
        return _make_config
    
    @pytest.fixture
    def mock_client_session(self):
        """Mock MCP ClientSession with common operations."""
        session = AsyncMock()
        session.initialize = AsyncMock()
        session.close = AsyncMock()
        session.call_tool = AsyncMock()
        session.list_tools = AsyncMock()
        return session
    
    # =============================================================================
    # Connection Management Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("transport_type,connection_config,should_succeed", [
        pytest.param(
            TransportType.SSE, 
            {"url": "http://localhost:3000/sse"},
            True,
            id="sse-valid-url"
        ),
        pytest.param(
            TransportType.SSE,
            {"url": ""},
            False,
            id="sse-empty-url"
        ),
        pytest.param(
            TransportType.SSE,
            {},
            False,
            id="sse-missing-url"
        ),
    ])
    async def test_connect_client_with_various_transports(
        self,
        mcp_client_service,
        make_client_config,
        mock_client_session,
        transport_type,
        connection_config,
        should_succeed
    ):
        """Test connecting to MCP servers with different transport configurations."""
        # Arrange
        client_id = f"client_{IDGenerator.generate('id')}"
        config = MCPClientConfig(
            name="Test Server",
            transport_type=transport_type,
            connection_config=connection_config,
            auto_connect=False
        )
        
        await mcp_client_service.add_client(client_id, config)
        
        if should_succeed:
            with patch.object(mcp_client_service, '_create_sse_session_direct', return_value=mock_client_session):
                with patch.object(mcp_client_service, '_discover_tools', return_value=None):
                    # Act
                    result = await mcp_client_service.connect_client(client_id)
                    
                    # Assert
                    assert result is True
                    client_info = mcp_client_service.get_client(client_id)
                    assert client_info.status == ClientStatus.CONNECTED
                    assert client_id in mcp_client_service.sessions
                    mock_client_session.initialize.assert_called_once()
        else:
            # Act & Assert
            with pytest.raises(Exception):
                await mcp_client_service.connect_client(client_id)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,expected_status", [
        pytest.param(
            ConnectionRefusedError("Connection refused"),
            ClientStatus.ERROR,
            id="connection-refused"
        ),
        pytest.param(
            TimeoutError("Connection timeout"),
            ClientStatus.ERROR,
            id="timeout-error"
        ),
        pytest.param(
            Exception("Unknown error"),
            ClientStatus.ERROR,
            id="generic-error"
        ),
    ])
    async def test_connection_error_handling(
        self,
        mcp_client_service,
        make_client_config,
        error_type,
        expected_status
    ):
        """Test handling various connection errors."""
        # Arrange
        client_id = "error-client"
        config = make_client_config()
        await mcp_client_service.add_client(client_id, config)
        
        with patch.object(mcp_client_service, '_create_sse_session_direct', side_effect=error_type):
            # Act & Assert
            with pytest.raises(type(error_type)):
                await mcp_client_service.connect_client(client_id)
            
            # Verify client status
            client_info = mcp_client_service.get_client(client_id)
            assert client_info.status == expected_status
            assert str(error_type) in client_info.last_error
    
    # =============================================================================
    # Tool Execution Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name,arguments,expected_result", [
        pytest.param(
            "simple_tool",
            {"arg1": "value1"},
            {"type": "text", "text": "Success"},
            id="simple-tool"
        ),
        pytest.param(
            "complex_tool",
            {"nested": {"key": "value"}, "list": [1, 2, 3]},
            {"type": "text", "text": "Complex result"},
            id="complex-arguments"
        ),
        pytest.param(
            "no_args_tool",
            {},
            {"type": "text", "text": "No args needed"},
            id="no-arguments"
        ),
    ])
    async def test_execute_tools_with_various_arguments(
        self,
        mcp_client_service,
        make_client_config,
        mock_client_session,
        tool_name,
        arguments,
        expected_result
    ):
        """Test executing tools with different argument patterns."""
        # Arrange
        client_id = "tool-client"
        config = make_client_config()
        
        # Setup mock response
        mock_result = MagicMock()
        mock_result.content = [expected_result]
        mock_client_session.call_tool = AsyncMock(return_value=mock_result)
        
        # Connect client
        await mcp_client_service.add_client(client_id, config)
        mcp_client_service.sessions[client_id] = mock_client_session
        mcp_client_service.clients[client_id].status = ClientStatus.CONNECTED
        
        # Act
        result = await mcp_client_service.call_tool(client_id, tool_name, arguments)
        
        # Assert
        assert result == mock_result
        mock_client_session.call_tool.assert_called_once()
        
        call_args = mock_client_session.call_tool.call_args[0][0]
        assert call_args.name == tool_name
        assert call_args.arguments == arguments
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_disconnected_client(
        self,
        mcp_client_service,
        make_client_config
    ):
        """Test tool execution fails gracefully when client is disconnected."""
        # Arrange
        client_id = "disconnected-client"
        config = make_client_config()
        await mcp_client_service.add_client(client_id, config)
        
        # Act & Assert
        with pytest.raises(ValueError, match="not connected"):
            await mcp_client_service.call_tool(client_id, "any_tool", {})
    
    # =============================================================================
    # Multi-Client Management Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("client_count", [1, 3, 5, 10])
    async def test_manage_multiple_clients(
        self,
        mcp_client_service,
        make_client_config,
        client_count
    ):
        """Test managing multiple MCP client connections."""
        # Arrange
        client_configs = {}
        for i in range(client_count):
            client_id = f"client_{i}"
            config = make_client_config(
                name=f"Server {i}",
                url=f"http://localhost:{3000 + i}/sse"
            )
            client_configs[client_id] = config
        
        # Act
        for client_id, config in client_configs.items():
            await mcp_client_service.add_client(client_id, config)
        
        # Assert
        assert len(mcp_client_service.list_clients()) == client_count
        
        for client_id, config in client_configs.items():
            client_info = mcp_client_service.get_client(client_id)
            assert client_info is not None
            assert client_info.config.name == config.name
    
    # =============================================================================
    # Auto-Reconnection Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    @pytest.mark.parametrize("failure_count,should_succeed", [
        pytest.param(0, True, id="immediate-success"),
        pytest.param(2, True, id="success-after-retries"),
        pytest.param(5, False, id="too-many-failures"),
    ])
    async def test_auto_reconnection_behavior(
        self,
        mcp_client_service,
        make_client_config,
        failure_count,
        should_succeed
    ):
        """Test automatic reconnection with various failure scenarios."""
        # Arrange
        client_id = "auto-reconnect-client"
        config = make_client_config(auto_connect=True)
        
        connection_attempts = 0
        async def mock_connect(*args):
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts <= failure_count:
                raise ConnectionError("Simulated failure")
            return True
        
        with patch.object(mcp_client_service, 'connect_client', side_effect=mock_connect):
            with patch('asyncio.sleep', return_value=None):  # Speed up test
                # Act
                await mcp_client_service.add_client(client_id, config)
                
                # Wait for reconnection attempts
                await asyncio.sleep(0.1)
                
                # Assert
                if should_succeed and failure_count < 5:
                    assert connection_attempts >= failure_count + 1
                else:
                    assert connection_attempts >= 1
    
    # =============================================================================
    # Tool Discovery Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_count", [0, 1, 5, 20])
    async def test_discover_tools_from_clients(
        self,
        mcp_client_service,
        make_client_config,
        mock_client_session,
        tool_count
    ):
        """Test discovering various numbers of tools from connected clients."""
        # Arrange
        client_id = "tool-discovery-client"
        config = make_client_config()
        
        # Create mock tools
        mock_tools = []
        for i in range(tool_count):
            tool = MagicMock()
            tool.name = f"tool_{i}"
            tool.description = f"Tool {i} description"
            tool.inputSchema = {"type": "object", "properties": {}}
            mock_tools.append(tool)
        
        # Mock list_tools response
        mock_response = MagicMock()
        mock_response.tools = mock_tools
        mock_client_session.list_tools = AsyncMock(return_value=mock_response)
        
        # Setup client
        await mcp_client_service.add_client(client_id, config)
        mcp_client_service.sessions[client_id] = mock_client_session
        mcp_client_service.clients[client_id].status = ClientStatus.CONNECTED
        
        # Act
        await mcp_client_service._discover_tools(client_id)
        
        # Assert
        client_info = mcp_client_service.get_client(client_id)
        assert len(client_info.tools) == tool_count
        
        if tool_count > 0:
            tools = await mcp_client_service.get_client_tools(client_id)
            assert len(tools) == tool_count
            for i, tool in enumerate(tools):
                assert tool.name == f"tool_{i}"
    
    # =============================================================================
    # Client Lifecycle Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_client_lifecycle_complete(
        self,
        mcp_client_service,
        make_client_config,
        mock_client_session
    ):
        """Test complete client lifecycle: add -> connect -> use -> disconnect -> remove."""
        client_id = "lifecycle-client"
        config = make_client_config()
        
        # 1. Add client
        client_info = await mcp_client_service.add_client(client_id, config)
        assert client_info.status == ClientStatus.DISCONNECTED
        
        # 2. Connect client
        with patch.object(mcp_client_service, '_create_sse_session_direct', return_value=mock_client_session):
            with patch.object(mcp_client_service, '_discover_tools', return_value=None):
                connected = await mcp_client_service.connect_client(client_id)
                assert connected is True
                assert mcp_client_service.get_client(client_id).status == ClientStatus.CONNECTED
        
        # 3. Use client (call tool)
        mock_result = MagicMock()
        mock_result.content = [{"type": "text", "text": "Result"}]
        mock_client_session.call_tool = AsyncMock(return_value=mock_result)
        
        result = await mcp_client_service.call_tool(client_id, "test_tool", {})
        assert result == mock_result
        
        # 4. Disconnect client
        disconnected = await mcp_client_service.disconnect_client(client_id)
        assert disconnected is True
        assert mcp_client_service.get_client(client_id).status == ClientStatus.DISCONNECTED
        assert client_id not in mcp_client_service.sessions
        
        # 5. Remove client
        removed = await mcp_client_service.remove_client(client_id)
        assert removed is True
        assert mcp_client_service.get_client(client_id) is None
    
    # =============================================================================
    # Status Tracking Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_sequence", [
        pytest.param(
            [ClientStatus.DISCONNECTED, ClientStatus.CONNECTING, ClientStatus.CONNECTED],
            id="normal-connection"
        ),
        pytest.param(
            [ClientStatus.DISCONNECTED, ClientStatus.CONNECTING, ClientStatus.ERROR],
            id="connection-error"
        ),
        pytest.param(
            [ClientStatus.CONNECTED, ClientStatus.DISCONNECTED],
            id="disconnection"
        ),
    ])
    async def test_client_status_transitions(
        self,
        mcp_client_service,
        make_client_config,
        status_sequence
    ):
        """Test various client status transitions."""
        # Arrange
        client_id = "status-client"
        config = make_client_config()
        await mcp_client_service.add_client(client_id, config)
        
        # Act & Assert
        for status in status_sequence:
            client_info = mcp_client_service.get_client(client_id)
            client_info.status = status
            
            if status == ClientStatus.CONNECTED:
                client_info.last_seen = datetime.now(timezone.utc)
            elif status == ClientStatus.ERROR:
                client_info.last_error = "Test error"
            
            # Verify status is persisted
            retrieved = mcp_client_service.get_client(client_id)
            assert retrieved.status == status
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("client_count", [10, 50, 100])
    async def test_multiple_client_performance(
        self,
        mcp_client_service,
        make_client_config,
        client_count
    ):
        """Test performance with large numbers of clients."""
        # Arrange & Act
        with measure_time(f"add_{client_count}_clients", threshold=1.0):
            for i in range(client_count):
                client_id = f"perf_client_{i}"
                config = make_client_config(name=f"Perf Server {i}")
                await mcp_client_service.add_client(client_id, config)
        
        # Assert
        assert len(mcp_client_service.list_clients()) == client_count
        
        # Test listing performance
        with measure_time(f"list_{client_count}_clients", threshold=0.1):
            clients = mcp_client_service.list_clients()
            assert len(clients) == client_count
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("operation,error_condition", [
        pytest.param("connect_missing", "Client not found", id="connect-missing-client"),
        pytest.param("call_tool_missing", "Client not found", id="tool-missing-client"),
        pytest.param("disconnect_missing", "Client not found", id="disconnect-missing-client"),
    ])
    async def test_operations_on_missing_client(
        self,
        mcp_client_service,
        operation,
        error_condition
    ):
        """Test operations on non-existent clients fail gracefully."""
        # Arrange
        missing_id = "non-existent-client"
        
        # Act & Assert
        if operation == "connect_missing":
            with pytest.raises(ValueError, match=error_condition):
                await mcp_client_service.connect_client(missing_id)
        elif operation == "call_tool_missing":
            with pytest.raises(ValueError, match=error_condition):
                await mcp_client_service.call_tool(missing_id, "tool", {})
        elif operation == "disconnect_missing":
            # Disconnect returns False for missing clients
            result = await mcp_client_service.disconnect_client(missing_id)
            assert result is False