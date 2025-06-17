"""Tests for MCP server module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import json
from datetime import datetime

from src.mcp_server import (
    MCPServer,
    MCPServerManager,
    MCPTransport,
    SSETransport,
    WebSocketTransport,
    MCPMessage,
    MCPError,
    ToolDefinition,
    ResourceDefinition
)


class TestMCPServer:
    """Test cases for MCPServer class."""
    
    def test_mcp_server_initialization(self):
        """Test MCP server initialization."""
        server = MCPServer(
            name="test_server",
            command="python",
            args=["-m", "test_module"],
            env={"API_KEY": "test_key"}
        )
        
        assert server.name == "test_server"
        assert server.command == "python"
        assert server.args == ["-m", "test_module"]
        assert server.env["API_KEY"] == "test_key"
        assert server.status == "stopped"
        assert server.process is None
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_start_server(self, mock_subprocess):
        """Test starting MCP server."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process
        
        server = MCPServer("test", "python", ["-m", "test"])
        await server.start()
        
        assert server.status == "running"
        assert server.process == mock_process
        mock_subprocess.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_server(self):
        """Test stopping MCP server."""
        server = MCPServer("test", "python", [])
        server.process = AsyncMock()
        server.status = "running"
        
        await server.stop()
        
        assert server.status == "stopped"
        server.process.terminate.assert_called_once()
        server.process.wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restart_server(self):
        """Test restarting MCP server."""
        server = MCPServer("test", "python", [])
        server.start = AsyncMock()
        server.stop = AsyncMock()
        server.status = "running"
        
        await server.restart()
        
        server.stop.assert_called_once()
        server.start.assert_called_once()
    
    def test_server_health_check(self):
        """Test server health check."""
        server = MCPServer("test", "python", [])
        
        # Stopped server is not healthy
        assert server.is_healthy() is False
        
        # Running server with process is healthy
        server.status = "running"
        server.process = Mock()
        server.process.returncode = None
        assert server.is_healthy() is True
        
        # Running server with terminated process is not healthy
        server.process.returncode = 1
        assert server.is_healthy() is False


class TestMCPServerManager:
    """Test cases for MCPServerManager class."""
    
    def test_manager_initialization(self):
        """Test server manager initialization."""
        manager = MCPServerManager()
        
        assert manager.servers == {}
        assert manager.transports == {}
        assert isinstance(manager.lock, asyncio.Lock)
    
    @pytest.mark.asyncio
    async def test_register_server(self):
        """Test registering a server."""
        manager = MCPServerManager()
        
        server_id = await manager.register_server(
            name="test_server",
            command="python",
            args=["-m", "test"],
            env={"KEY": "value"}
        )
        
        assert server_id in manager.servers
        server = manager.servers[server_id]
        assert server.name == "test_server"
        assert server.command == "python"
    
    @pytest.mark.asyncio
    async def test_unregister_server(self):
        """Test unregistering a server."""
        manager = MCPServerManager()
        server_id = await manager.register_server("test", "python", [])
        
        # Start the server
        manager.servers[server_id].stop = AsyncMock()
        
        await manager.unregister_server(server_id)
        
        assert server_id not in manager.servers
        manager.servers[server_id].stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_server_status(self):
        """Test getting server status."""
        manager = MCPServerManager()
        server_id = await manager.register_server("test", "python", [])
        
        status = manager.get_server_status(server_id)
        
        assert status["name"] == "test"
        assert status["status"] == "stopped"
        assert status["healthy"] is False
        
        # Test non-existent server
        assert manager.get_server_status("invalid_id") is None
    
    @pytest.mark.asyncio
    async def test_list_servers(self):
        """Test listing all servers."""
        manager = MCPServerManager()
        
        # Register multiple servers
        id1 = await manager.register_server("server1", "python", [])
        id2 = await manager.register_server("server2", "node", [])
        
        servers = manager.list_servers()
        
        assert len(servers) == 2
        assert any(s["id"] == id1 for s in servers)
        assert any(s["id"] == id2 for s in servers)


class TestMCPTransport:
    """Test cases for MCP transport implementations."""
    
    def test_base_transport_interface(self):
        """Test base transport interface."""
        transport = MCPTransport()
        
        with pytest.raises(NotImplementedError):
            asyncio.run(transport.connect())
        
        with pytest.raises(NotImplementedError):
            asyncio.run(transport.disconnect())
        
        with pytest.raises(NotImplementedError):
            asyncio.run(transport.send({}))
        
        with pytest.raises(NotImplementedError):
            asyncio.run(transport.receive())
    
    @pytest.mark.asyncio
    async def test_sse_transport(self):
        """Test SSE transport implementation."""
        transport = SSETransport("http://localhost:8080/sse")
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.iter_any = AsyncMock()
            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response
            
            await transport.connect()
            
            assert transport.connected is True
            mock_session.return_value.get.assert_called_with("http://localhost:8080/sse")
    
    @pytest.mark.asyncio
    async def test_websocket_transport(self):
        """Test WebSocket transport implementation."""
        transport = WebSocketTransport("ws://localhost:8080/ws")
        
        # Mock websocket connection
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            await transport.connect()
            
            assert transport.connected is True
            assert transport.websocket == mock_ws
            mock_connect.assert_called_with("ws://localhost:8080/ws")
    
    @pytest.mark.asyncio
    async def test_transport_reconnection(self):
        """Test transport automatic reconnection."""
        transport = SSETransport("http://localhost:8080/sse")
        transport.max_retries = 3
        transport.retry_delay = 0.1
        
        # Mock failed connections
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.get.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                await transport.connect()
            
            # Verify retry attempts
            assert mock_session.return_value.get.call_count >= transport.max_retries


class TestMCPMessage:
    """Test cases for MCP message handling."""
    
    def test_message_creation(self):
        """Test creating MCP messages."""
        msg = MCPMessage(
            id="msg_123",
            method="tools/list",
            params={},
            jsonrpc="2.0"
        )
        
        assert msg.id == "msg_123"
        assert msg.method == "tools/list"
        assert msg.params == {}
        assert msg.jsonrpc == "2.0"
    
    def test_message_serialization(self):
        """Test message serialization."""
        msg = MCPMessage(
            id="msg_123",
            method="tools/execute",
            params={"tool": "test_tool", "args": {"input": "test"}}
        )
        
        serialized = msg.to_json()
        assert isinstance(serialized, str)
        
        data = json.loads(serialized)
        assert data["id"] == "msg_123"
        assert data["method"] == "tools/execute"
        assert data["params"]["tool"] == "test_tool"
    
    def test_message_deserialization(self):
        """Test message deserialization."""
        json_str = '{"id": "msg_456", "method": "resources/list", "params": {}, "jsonrpc": "2.0"}'
        
        msg = MCPMessage.from_json(json_str)
        
        assert msg.id == "msg_456"
        assert msg.method == "resources/list"
        assert msg.params == {}
    
    def test_error_message(self):
        """Test error message creation."""
        error = MCPError(
            code=-32600,
            message="Invalid Request",
            data={"details": "Missing required field"}
        )
        
        msg = MCPMessage.error_response("msg_123", error)
        
        assert msg.id == "msg_123"
        assert msg.error == error
        assert msg.result is None


class TestToolAndResourceDefinitions:
    """Test cases for tool and resource definitions."""
    
    def test_tool_definition(self):
        """Test tool definition creation."""
        tool = ToolDefinition(
            name="calculate",
            description="Perform calculations",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        )
        
        assert tool.name == "calculate"
        assert tool.description == "Perform calculations"
        assert tool.input_schema["properties"]["expression"]["type"] == "string"
    
    def test_resource_definition(self):
        """Test resource definition creation."""
        resource = ResourceDefinition(
            uri="file:///path/to/resource",
            name="Config File",
            description="Application configuration",
            mime_type="application/json"
        )
        
        assert resource.uri == "file:///path/to/resource"
        assert resource.name == "Config File"
        assert resource.mime_type == "application/json"
    
    def test_tool_validation(self):
        """Test tool input validation."""
        tool = ToolDefinition(
            name="test_tool",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "required_field": {"type": "string"}
                },
                "required": ["required_field"]
            }
        )
        
        # Valid input
        assert tool.validate_input({"required_field": "value"}) is True
        
        # Invalid input (missing required field)
        assert tool.validate_input({}) is False
        
        # Invalid input (wrong type)
        assert tool.validate_input({"required_field": 123}) is False


class TestMCPServerIntegration:
    """Integration tests for MCP server functionality."""
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self):
        """Test complete server lifecycle."""
        manager = MCPServerManager()
        
        # Register server
        server_id = await manager.register_server(
            name="lifecycle_test",
            command="echo",
            args=["test"]
        )
        
        # Mock subprocess for start
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.pid = 99999
            mock_subprocess.return_value = mock_process
            
            # Start server
            server = manager.servers[server_id]
            await server.start()
            
            assert server.status == "running"
            
            # Stop server
            await server.stop()
            
            assert server.status == "stopped"
            
            # Unregister
            await manager.unregister_server(server_id)
            
            assert server_id not in manager.servers
    
    @pytest.mark.asyncio
    async def test_transport_message_flow(self):
        """Test message flow through transport."""
        transport = WebSocketTransport("ws://test")
        
        # Mock websocket
        mock_ws = AsyncMock()
        transport.websocket = mock_ws
        transport.connected = True
        
        # Send message
        msg = MCPMessage(id="test_123", method="ping", params={})
        await transport.send(msg.to_dict())
        
        mock_ws.send.assert_called_once()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["id"] == "test_123"
        assert sent_data["method"] == "ping"
        
        # Receive message
        mock_ws.recv.return_value = '{"id": "test_123", "result": "pong"}'
        
        received = await transport.receive()
        assert received["id"] == "test_123"
        assert received["result"] == "pong"