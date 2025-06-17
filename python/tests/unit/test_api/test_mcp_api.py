"""Unit tests for MCP API endpoints."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import WebSocket
from fastapi.testclient import TestClient
import subprocess
import json
from collections import deque
from datetime import datetime
from src.api.mcp_api import (
    router, MCPServerManager, ServerConfig, ServerResponse, LogEntry
)


class TestMCPServerManager:
    """Unit tests for MCPServerManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create MCPServerManager instance."""
        return MCPServerManager()
    
    @pytest.fixture
    def mock_process(self):
        """Mock subprocess.Popen process."""
        process = MagicMock()
        process.poll.return_value = None  # Process running
        process.pid = 12345
        process.stdout = MagicMock()
        process.stderr = MagicMock()
        return process
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.Popen')
    @patch('src.api.mcp_api.credential_service')
    async def test_start_server_success(self, mock_cred_service, mock_popen, manager, mock_process):
        """Test successful MCP server start."""
        # Setup mocks
        mock_popen.return_value = mock_process
        mock_cred_service.load_all_credentials = AsyncMock()
        mock_cred_service.get_credential = AsyncMock(return_value='test-value')
        
        # Start server
        result = await manager.start_server()
        
        assert result['success'] is True
        assert result['status'] == 'running'
        assert result['pid'] == 12345
        assert manager.status == 'running'
        assert manager.process == mock_process
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_server_already_running(self, manager):
        """Test starting server when already running."""
        # Simulate running server
        manager.process = MagicMock()
        manager.process.poll.return_value = None
        manager.status = 'running'
        
        result = await manager.start_server()
        
        assert result['success'] is False
        assert 'already running' in result['message']
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stop_server_success(self, manager, mock_process):
        """Test successful MCP server stop."""
        # Setup running server
        manager.process = mock_process
        manager.status = 'running'
        
        # Create mock async task
        manager.log_reader_task = AsyncMock()
        
        result = await manager.stop_server()
        
        assert result['success'] is True
        assert result['status'] == 'stopped'
        assert manager.process is None
        mock_process.terminate.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stop_server_not_running(self, manager):
        """Test stopping server when not running."""
        manager.process = None
        manager.status = 'stopped'
        
        result = await manager.stop_server()
        
        assert result['success'] is False
        assert 'not running' in result['message']
    
    @pytest.mark.unit
    def test_get_status(self, manager, mock_process):
        """Test getting server status."""
        # Test with running process
        manager.process = mock_process
        manager.status = 'running'
        manager.start_time = 1000
        
        with patch('time.time', return_value=1100):
            status = manager.get_status()
        
        assert status['status'] == 'running'
        assert status['uptime'] == 100
        
        # Test with stopped process
        mock_process.poll.return_value = 0
        status = manager.get_status()
        
        assert status['status'] == 'stopped'
        assert manager.process is None
    
    @pytest.mark.unit
    def test_log_management(self, manager):
        """Test log adding and retrieval."""
        # Add logs
        manager._add_log('INFO', 'Test info message')
        manager._add_log('ERROR', 'Test error message')
        
        assert len(manager.logs) == 2
        
        # Get logs
        logs = manager.get_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]['level'] == 'ERROR'
        assert logs[0]['message'] == 'Test error message'
        
        # Clear logs
        manager.clear_logs()
        assert len(manager.logs) == 1  # Should have "Logs cleared" message
    
    @pytest.mark.unit
    def test_parse_log_line(self, manager):
        """Test log line parsing."""
        # Test various log formats
        level, msg = manager._parse_log_line('[INFO] Server started')
        assert level == 'INFO'
        assert msg == 'Server started'
        
        level, msg = manager._parse_log_line('ERROR: Connection failed')
        assert level == 'ERROR'
        assert msg == 'ERROR: Connection failed'
        
        level, msg = manager._parse_log_line('Normal log message')
        assert level == 'INFO'
        assert msg == 'Normal log message'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_management(self, manager):
        """Test WebSocket connection management."""
        # Mock WebSocket
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        
        # Add WebSocket
        await manager.add_websocket(ws)
        
        assert ws in manager.log_websockets
        ws.accept.assert_called_once()
        
        # Remove WebSocket
        manager.remove_websocket(ws)
        assert ws not in manager.log_websockets
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_broadcast_log(self, manager):
        """Test log broadcasting to WebSockets."""
        # Setup WebSockets
        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Disconnected"))
        
        manager.log_websockets = [ws1, ws2]
        
        # Broadcast log
        log_entry = {
            'timestamp': '2024-01-01T00:00:00Z',
            'level': 'INFO',
            'message': 'Test broadcast'
        }
        
        await manager._broadcast_log(log_entry)
        
        # Check ws1 received and ws2 was removed
        ws1.send_json.assert_called_once_with(log_entry)
        assert ws1 in manager.log_websockets
        assert ws2 not in manager.log_websockets


class TestMCPAPIEndpoints:
    """Unit tests for MCP API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_manager(self):
        """Mock MCP manager."""
        with patch('src.api.mcp_api.mcp_manager') as mock:
            yield mock
    
    @pytest.mark.unit
    def test_start_server_endpoint(self, test_client, mock_manager):
        """Test POST /mcp/start endpoint."""
        mock_manager.start_server = AsyncMock(return_value={
            'success': True,
            'status': 'running',
            'message': 'Server started',
            'pid': 12345
        })
        
        response = test_client.post("/api/mcp/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['status'] == 'running'
        assert data['pid'] == 12345
    
    @pytest.mark.unit
    def test_stop_server_endpoint(self, test_client, mock_manager):
        """Test POST /mcp/stop endpoint."""
        mock_manager.stop_server = AsyncMock(return_value={
            'success': True,
            'status': 'stopped',
            'message': 'Server stopped'
        })
        
        response = test_client.post("/api/mcp/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['status'] == 'stopped'
    
    @pytest.mark.unit
    def test_get_status_endpoint(self, test_client, mock_manager):
        """Test GET /mcp/status endpoint."""
        mock_manager.get_status.return_value = {
            'status': 'running',
            'uptime': 3600,
            'logs': ['[INFO] Server running']
        }
        
        response = test_client.get("/api/mcp/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'running'
        assert data['uptime'] == 3600
        assert len(data['logs']) == 1
    
    @pytest.mark.unit
    def test_get_logs_endpoint(self, test_client, mock_manager):
        """Test GET /mcp/logs endpoint."""
        mock_logs = [
            {'timestamp': '2024-01-01T00:00:00Z', 'level': 'INFO', 'message': 'Log 1'},
            {'timestamp': '2024-01-01T00:01:00Z', 'level': 'ERROR', 'message': 'Log 2'}
        ]
        mock_manager.get_logs.return_value = mock_logs
        
        response = test_client.get("/api/mcp/logs?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 2
        assert data['logs'][1]['level'] == 'ERROR'
    
    @pytest.mark.unit
    def test_clear_logs_endpoint(self, test_client, mock_manager):
        """Test DELETE /mcp/logs endpoint."""
        mock_manager.clear_logs.return_value = None
        
        response = test_client.delete("/api/mcp/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        mock_manager.clear_logs.assert_called_once()
    
    @pytest.mark.unit
    @patch('src.api.mcp_api.credential_service')
    def test_get_config_endpoint(self, mock_cred_service, test_client):
        """Test GET /mcp/config endpoint."""
        mock_cred_service.get_credential = AsyncMock(side_effect=[
            'gpt-4o-mini',  # model_choice
            'true',         # use_contextual_embeddings
            'false',        # use_hybrid_search
            'true'          # use_agentic_rag
        ])
        
        response = test_client.get("/api/mcp/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data['transport'] == 'sse'
        assert data['port'] == 8051
        assert data['model_choice'] == 'gpt-4o-mini'
        assert data['use_contextual_embeddings'] is True
    
    @pytest.mark.unit
    @patch('aiohttp.ClientSession')
    def test_get_tools_endpoint(self, mock_session_class, test_client):
        """Test GET /mcp/tools endpoint."""
        # Mock aiohttp session
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'tools': [
                {'name': 'tool1', 'description': 'Tool 1'},
                {'name': 'tool2', 'description': 'Tool 2'}
            ]
        })
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        response = test_client.get("/api/mcp/tools")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['tools']) == 2
        assert data['tools'][0]['name'] == 'tool1'
    
    @pytest.mark.unit
    def test_health_endpoint(self, test_client, mock_manager):
        """Test GET /mcp/health endpoint."""
        mock_manager.get_status.return_value = {'status': 'running'}
        
        response = test_client.get("/api/mcp/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['healthy'] is True
        assert data['mcp_status'] == 'running'
    
    @pytest.mark.unit
    def test_server_config_validation(self):
        """Test ServerConfig model validation."""
        # Test with defaults
        config = ServerConfig()
        assert config.transport == 'sse'
        assert config.host == 'localhost'
        assert config.port == 8051
        
        # Test with custom values
        config = ServerConfig(transport='stdio', host='0.0.0.0', port=8080)
        assert config.transport == 'stdio'
        assert config.host == '0.0.0.0'
        assert config.port == 8080
    
    @pytest.mark.unit
    def test_error_handling(self, test_client, mock_manager):
        """Test API error handling."""
        # Mock start_server to raise exception
        mock_manager.start_server = AsyncMock(side_effect=Exception("Test error"))
        
        response = test_client.post("/api/mcp/start")
        
        assert response.status_code == 500
        assert "Test error" in response.json()['detail']