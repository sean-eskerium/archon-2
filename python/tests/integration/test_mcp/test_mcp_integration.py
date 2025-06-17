"""Integration tests for MCP functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import json
from datetime import datetime

from src.services.mcp_client_service import MCPClientService
from src.services.mcp_session_manager import SimplifiedSessionManager
from src.mcp_server import MCPServerManager
from src.models.mcp_models import TransportType, SSEConfig, WebSocketConfig


class TestMCPServerClientIntegration:
    """Test MCP server and client integration."""
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    @patch('aiohttp.ClientSession')
    async def test_server_client_lifecycle(self, mock_session, mock_subprocess):
        """Test complete server-client lifecycle."""
        # Mock subprocess for server
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process
        
        # Mock HTTP client for MCP
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        # Initialize services
        server_manager = MCPServerManager()
        client_service = MCPClientService()
        
        # 1. Register and start server
        server_id = await server_manager.register_server(
            name="test_mcp_server",
            command="python",
            args=["-m", "test_server"],
            env={"API_KEY": "test"}
        )
        
        server = server_manager.servers[server_id]
        await server.start()
        
        assert server.status == "running"
        
        # 2. Create client and connect
        client_config = {
            "server_id": server_id,
            "transport_type": TransportType.SSE,
            "sse_config": SSEConfig(url="http://localhost:8080/sse")
        }
        
        client = await client_service.create_client(client_config)
        
        # Mock SSE connection
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_client.get.return_value.__aenter__.return_value = mock_response
        
        await client.connect()
        
        assert client.is_connected
        
        # 3. Clean shutdown
        await client.disconnect()
        await server.stop()
        
        assert not client.is_connected
        assert server.status == "stopped"
    
    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_communication(self, mock_ws_connect):
        """Test WebSocket communication between client and server."""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws
        
        client_service = MCPClientService()
        
        # Create WebSocket client
        client_config = {
            "server_id": "test_server",
            "transport_type": TransportType.WEBSOCKET,
            "websocket_config": WebSocketConfig(url="ws://localhost:8080/ws")
        }
        
        client = await client_service.create_client(client_config)
        await client.connect()
        
        # Test tool discovery
        mock_ws.recv.return_value = json.dumps({
            "id": "1",
            "result": {
                "tools": [
                    {
                        "name": "calculate",
                        "description": "Perform calculations",
                        "inputSchema": {"type": "object"}
                    }
                ]
            }
        })
        
        tools = await client.list_tools()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "calculate"
        
        # Verify request was sent
        mock_ws.send.assert_called()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["method"] == "tools/list"


class TestMCPToolExecution:
    """Test MCP tool execution integration."""
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_tool_execution_flow(self, mock_session):
        """Test complete tool execution flow."""
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        # Mock SSE responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_client.post.return_value.__aenter__.return_value = mock_response
        
        client_service = MCPClientService()
        session_manager = SimplifiedSessionManager()
        
        # Create session
        session_id = await session_manager.create_session("user_123", "client_123")
        
        # Execute tool
        tool_request = {
            "tool": "search",
            "arguments": {"query": "test query", "limit": 10}
        }
        
        # Mock tool response
        mock_response.json.return_value = {
            "id": "exec_123",
            "result": {
                "content": [
                    {"type": "text", "text": "Search results..."}
                ]
            }
        }
        
        result = await client_service.execute_tool(
            session_id,
            tool_request["tool"],
            tool_request["arguments"]
        )
        
        assert result["content"][0]["text"] == "Search results..."
        
        # Verify session was updated
        session = await session_manager.get_session(session_id)
        assert len(session.tool_calls) == 1
        assert session.tool_calls[0]["tool"] == "search"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool execution error handling."""
        client_service = MCPClientService()
        
        with patch.object(client_service, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock error response
            mock_client.execute_tool.side_effect = Exception("Tool execution failed")
            
            with pytest.raises(Exception) as exc_info:
                await client_service.execute_tool(
                    "session_123",
                    "failing_tool",
                    {"param": "value"}
                )
            
            assert "Tool execution failed" in str(exc_info.value)


class TestMCPSessionManagement:
    """Test MCP session management integration."""
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling multiple concurrent sessions."""
        session_manager = SimplifiedSessionManager()
        
        # Create multiple sessions concurrently
        session_tasks = []
        for i in range(10):
            task = session_manager.create_session(f"user_{i}", f"client_{i}")
            session_tasks.append(task)
        
        session_ids = await asyncio.gather(*session_tasks)
        
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # All unique
        
        # Verify all sessions exist
        for session_id in session_ids:
            session = await session_manager.get_session(session_id)
            assert session is not None
    
    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_session_expiration(self, mock_sleep):
        """Test session expiration and cleanup."""
        session_manager = SimplifiedSessionManager()
        session_manager.session_timeout = 1  # 1 second timeout
        
        # Create session
        session_id = await session_manager.create_session("user_123", "client_123")
        
        # Session should exist initially
        session = await session_manager.get_session(session_id)
        assert session is not None
        
        # Simulate time passing
        session.last_activity = datetime.now().timestamp() - 2
        
        # Run cleanup
        await session_manager.cleanup_expired_sessions()
        
        # Session should be expired
        session = await session_manager.get_session(session_id)
        assert session is None


class TestMCPResourceHandling:
    """Test MCP resource handling integration."""
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_resource_discovery(self, mock_session):
        """Test resource discovery and access."""
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        client_service = MCPClientService()
        
        # Mock resource list response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "res_list",
            "result": {
                "resources": [
                    {
                        "uri": "file:///config/app.json",
                        "name": "App Config",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": "db://users/schema",
                        "name": "User Schema",
                        "mimeType": "application/sql"
                    }
                ]
            }
        }
        
        mock_client.post.return_value.__aenter__.return_value = mock_response
        
        resources = await client_service.list_resources("client_123")
        
        assert len(resources) == 2
        assert resources[0]["name"] == "App Config"
        assert resources[1]["uri"] == "db://users/schema"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_resource_content_retrieval(self, mock_session):
        """Test retrieving resource content."""
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        client_service = MCPClientService()
        
        # Mock resource content response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "res_read",
            "result": {
                "contents": [
                    {
                        "uri": "file:///config/app.json",
                        "mimeType": "application/json",
                        "text": '{"version": "1.0.0", "debug": true}'
                    }
                ]
            }
        }
        
        mock_client.post.return_value.__aenter__.return_value = mock_response
        
        content = await client_service.read_resource(
            "client_123",
            "file:///config/app.json"
        )
        
        assert content["mimeType"] == "application/json"
        config = json.loads(content["text"])
        assert config["version"] == "1.0.0"
        assert config["debug"] is True


class TestMCPReconnection:
    """Test MCP reconnection and recovery."""
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_auto_reconnection(self, mock_session):
        """Test automatic reconnection on connection loss."""
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        client_service = MCPClientService()
        
        # Create client
        client_config = {
            "server_id": "test_server",
            "transport_type": TransportType.SSE,
            "sse_config": SSEConfig(
                url="http://localhost:8080/sse",
                reconnect_attempts=3,
                reconnect_delay=0.1
            )
        }
        
        client = await client_service.create_client(client_config)
        
        # First connection succeeds
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_client.get.return_value.__aenter__.return_value = mock_response
        
        await client.connect()
        assert client.is_connected
        
        # Simulate connection loss
        mock_client.get.side_effect = [
            Exception("Connection lost"),
            Exception("Still failing"),
            mock_client.get.return_value  # Third attempt succeeds
        ]
        
        # Trigger reconnection
        with patch('asyncio.sleep'):  # Skip delays
            await client.ensure_connected()
        
        # Should reconnect after retries
        assert client.is_connected
        assert mock_client.get.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_session_recovery(self):
        """Test session recovery after server restart."""
        session_manager = SimplifiedSessionManager()
        
        # Create session with state
        session_id = await session_manager.create_session("user_123", "client_123")
        
        # Add some tool calls
        await session_manager.add_tool_call(
            session_id,
            {
                "tool": "search",
                "arguments": {"query": "test"},
                "result": {"content": "results"}
            }
        )
        
        # Simulate server restart - serialize session
        session_data = await session_manager.export_session(session_id)
        
        # Clear sessions (simulating restart)
        session_manager.sessions.clear()
        
        # Restore session
        restored_id = await session_manager.import_session(session_data)
        
        # Verify session restored
        session = await session_manager.get_session(restored_id)
        assert session is not None
        assert len(session.tool_calls) == 1
        assert session.tool_calls[0]["tool"] == "search"