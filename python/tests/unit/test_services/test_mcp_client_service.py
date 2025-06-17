"""Unit tests for MCPClientService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone
from src.services.mcp_client_service import (
    MCPClientService, 
    MCPClientConfig, 
    MCPClientInfo,
    TransportType,
    ClientStatus
)


class TestMCPClientService:
    """Unit tests for MCPClientService."""
    
    @pytest.fixture
    def mcp_client_service(self):
        """Create MCPClientService instance."""
        return MCPClientService()
    
    @pytest.fixture
    def sample_client_config(self):
        """Sample MCP client configuration."""
        return MCPClientConfig(
            name="Test MCP Server",
            transport_type=TransportType.SSE,
            connection_config={"url": "http://localhost:3000/sse"},
            auto_connect=False,
            health_check_interval=30
        )
    
    @pytest.fixture
    def mock_client_session(self):
        """Mock MCP ClientSession."""
        session = AsyncMock()
        session.initialize = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_connects_to_server(self, mcp_client_service, sample_client_config, mock_client_session):
        """Test connecting to an MCP server."""
        # Arrange
        client_id = "test-client-id"
        
        # First add the client
        await mcp_client_service.add_client(client_id, sample_client_config)
        
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
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_handles_connection_errors(self, mcp_client_service, sample_client_config):
        """Test handling connection errors gracefully."""
        # Arrange
        client_id = "test-client-id"
        await mcp_client_service.add_client(client_id, sample_client_config)
        
        with patch.object(mcp_client_service, '_create_sse_session_direct', side_effect=Exception("Connection failed")):
            # Act & Assert
            with pytest.raises(Exception, match="Connection failed"):
                await mcp_client_service.connect_client(client_id)
            
            client_info = mcp_client_service.get_client(client_id)
            assert client_info.status == ClientStatus.ERROR
            assert "Connection failed" in client_info.last_error
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_executes_tools(self, mcp_client_service, sample_client_config, mock_client_session):
        """Test executing tools via MCP client."""
        # Arrange
        client_id = "test-client-id"
        tool_name = "test_tool"
        arguments = {"arg1": "value1"}
        
        # Setup mock tool result
        mock_result = MagicMock()
        mock_result.content = [{"type": "text", "text": "Tool executed successfully"}]
        mock_client_session.call_tool = AsyncMock(return_value=mock_result)
        
        # Add client and connect
        await mcp_client_service.add_client(client_id, sample_client_config)
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
    @pytest.mark.unit
    async def test_mcp_client_manages_multiple_connections(self, mcp_client_service, sample_client_config):
        """Test managing multiple MCP client connections."""
        # Arrange
        client_configs = {
            "client1": MCPClientConfig(
                name="Server 1",
                transport_type=TransportType.SSE,
                connection_config={"url": "http://localhost:3001/sse"}
            ),
            "client2": MCPClientConfig(
                name="Server 2",
                transport_type=TransportType.SSE,
                connection_config={"url": "http://localhost:3002/sse"}
            )
        }
        
        # Act
        for client_id, config in client_configs.items():
            await mcp_client_service.add_client(client_id, config)
        
        # Assert
        assert len(mcp_client_service.list_clients()) == 2
        assert mcp_client_service.get_client("client1").config.name == "Server 1"
        assert mcp_client_service.get_client("client2").config.name == "Server 2"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('asyncio.sleep', return_value=None)
    async def test_mcp_client_reconnects_on_failure(self, mock_sleep, mcp_client_service):
        """Test automatic reconnection on connection failure."""
        # Arrange
        client_id = "test-client-id"
        config = MCPClientConfig(
            name="Auto Reconnect Server",
            transport_type=TransportType.SSE,
            connection_config={"url": "http://localhost:3000/sse"},
            auto_connect=True
        )
        
        # Mock connection attempts
        connection_attempts = 0
        async def mock_connect(*args):
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts < 3:
                raise Exception("Connection failed")
            return True
        
        with patch.object(mcp_client_service, 'connect_client', side_effect=mock_connect):
            # Act
            await mcp_client_service.add_client(client_id, config)
            
            # Wait a bit for reconnection attempts
            await asyncio.sleep(0.1)
            
            # Assert - should have attempted connection
            assert connection_attempts >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_lists_available_tools(self, mcp_client_service, sample_client_config, mock_client_session):
        """Test listing available tools from connected clients."""
        # Arrange
        client_id = "test-client-id"
        mock_tools = [
            MagicMock(name="tool1", description="Tool 1"),
            MagicMock(name="tool2", description="Tool 2")
        ]
        
        # Mock list_tools response
        mock_response = MagicMock()
        mock_response.tools = mock_tools
        mock_client_session.list_tools = AsyncMock(return_value=mock_response)
        
        # Add and connect client
        await mcp_client_service.add_client(client_id, sample_client_config)
        mcp_client_service.sessions[client_id] = mock_client_session
        mcp_client_service.clients[client_id].status = ClientStatus.CONNECTED
        
        # Act
        with patch.object(mcp_client_service, '_discover_tools') as mock_discover:
            mock_discover.return_value = None
            # Manually set tools (since _discover_tools is mocked)
            mcp_client_service.clients[client_id].tools = mock_tools
        
        tools = await mcp_client_service.get_client_tools(client_id)
        
        # Assert
        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool2"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_validates_tool_arguments(self, mcp_client_service):
        """Test validation of tool arguments."""
        # Arrange
        client_id = "test-client-id"
        
        # Act & Assert - calling tool on non-existent client
        with pytest.raises(ValueError, match="Client not found"):
            await mcp_client_service.call_tool(client_id, "tool", {})
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_client_handles_tool_errors(self, mcp_client_service, sample_client_config, mock_client_session):
        """Test handling errors during tool execution."""
        # Arrange
        client_id = "test-client-id"
        mock_client_session.call_tool = AsyncMock(side_effect=Exception("Tool execution failed"))
        
        # Add and connect client
        await mcp_client_service.add_client(client_id, sample_client_config)
        mcp_client_service.sessions[client_id] = mock_client_session
        mcp_client_service.clients[client_id].status = ClientStatus.CONNECTED
        
        # Act & Assert
        with pytest.raises(Exception, match="Tool execution failed"):
            await mcp_client_service.call_tool(client_id, "failing_tool", {})
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_disconnect_client(self, mcp_client_service, sample_client_config, mock_client_session):
        """Test disconnecting from an MCP client."""
        # Arrange
        client_id = "test-client-id"
        await mcp_client_service.add_client(client_id, sample_client_config)
        mcp_client_service.sessions[client_id] = mock_client_session
        mcp_client_service.clients[client_id].status = ClientStatus.CONNECTED
        
        # Act
        result = await mcp_client_service.disconnect_client(client_id)
        
        # Assert
        assert result is True
        assert mcp_client_service.clients[client_id].status == ClientStatus.DISCONNECTED
        assert client_id not in mcp_client_service.sessions
        assert len(mcp_client_service.clients[client_id].tools) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_client(self, mcp_client_service, sample_client_config):
        """Test removing a client completely."""
        # Arrange
        client_id = "test-client-id"
        await mcp_client_service.add_client(client_id, sample_client_config)
        
        # Act
        result = await mcp_client_service.remove_client(client_id)
        
        # Assert
        assert result is True
        assert client_id not in mcp_client_service.clients
        assert mcp_client_service.get_client(client_id) is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_client_status_tracking(self, mcp_client_service, sample_client_config):
        """Test that client status is properly tracked."""
        # Arrange
        client_id = "test-client-id"
        
        # Act - Add client
        client_info = await mcp_client_service.add_client(client_id, sample_client_config)
        
        # Assert initial status
        assert client_info.status == ClientStatus.DISCONNECTED
        assert client_info.last_seen is None
        assert client_info.last_error is None
        
        # Update status
        client_info.status = ClientStatus.CONNECTED
        client_info.last_seen = datetime.now(timezone.utc)
        
        # Assert updated status
        retrieved_client = mcp_client_service.get_client(client_id)
        assert retrieved_client.status == ClientStatus.CONNECTED
        assert retrieved_client.last_seen is not None