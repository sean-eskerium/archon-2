"""Unit tests for MCP API endpoints with enhanced patterns."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException, WebSocket
from fastapi.testclient import TestClient
from typing import List, Dict, Any, Optional
import asyncio
import uuid
from datetime import datetime

from src.api.mcp_api import router
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import assert_fields_equal, measure_time


@pytest.mark.unit
@pytest.mark.standard
class TestMCPAPI:
    """Unit tests for MCP API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Mock MCP server instance."""
        server = MagicMock()
        server.is_running = False
        server.start = AsyncMock()
        server.stop = AsyncMock()
        server.restart = AsyncMock()
        server.get_status = MagicMock(return_value={"status": "stopped"})
        server.get_logs = MagicMock(return_value=[])
        return server
    
    @pytest.fixture
    def mock_mcp_client_service(self):
        """Mock MCP client service."""
        service = MagicMock()
        service.list_clients = AsyncMock(return_value=[])
        service.get_client = AsyncMock(return_value=None)
        service.create_client = AsyncMock()
        service.update_client = AsyncMock()
        service.delete_client = AsyncMock()
        service.test_connection = AsyncMock()
        return service
    
    @pytest.fixture
    def make_mcp_server_config(self):
        """Factory for creating MCP server configurations."""
        def _make_config(
            name: str = "test-server",
            port: int = 3000,
            transport: str = "stdio",
            command: Optional[str] = None,
            args: Optional[List[str]] = None
        ) -> Dict:
            return {
                "name": name,
                "port": port,
                "transport": transport,
                "command": command or "node",
                "args": args or ["server.js"],
                "env": {"NODE_ENV": "production"},
                "auto_restart": True
            }
        return _make_config
    
    @pytest.fixture
    def make_mcp_client_config(self):
        """Factory for creating MCP client configurations."""
        def _make_config(
            client_id: Optional[str] = None,
            name: str = "test-client",
            transport: str = "sse",
            endpoint: str = "http://localhost:3000",
            enabled: bool = True
        ) -> Dict:
            return {
                "id": client_id or f"client-{uuid.uuid4().hex[:8]}",
                "name": name,
                "transport": transport,
                "endpoint": endpoint,
                "enabled": enabled,
                "metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_connected": None
                }
            }
        return _make_config
    
    # =============================================================================
    # Server Lifecycle Tests
    # =============================================================================
    
    @pytest.mark.parametrize("initial_state,action,expected_status", [
        pytest.param(False, "start", "running", id="start-stopped-server"),
        pytest.param(True, "stop", "stopped", id="stop-running-server"),
        pytest.param(True, "restart", "running", id="restart-running-server"),
        pytest.param(False, "stop", "stopped", id="stop-already-stopped"),
    ])
    @patch('src.api.mcp_api.mcp_server')
    async def test_server_lifecycle_operations(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        initial_state,
        action,
        expected_status
    ):
        """Test server start, stop, and restart operations."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        mock_mcp_server.is_running = initial_state
        
        # Update status after action
        async def update_status():
            if action == "start":
                mock_mcp_server.is_running = True
                mock_mcp_server.get_status.return_value = {"status": "running"}
            elif action == "stop":
                mock_mcp_server.is_running = False
                mock_mcp_server.get_status.return_value = {"status": "stopped"}
            elif action == "restart":
                mock_mcp_server.is_running = True
                mock_mcp_server.get_status.return_value = {"status": "running"}
        
        mock_mcp_server.start.side_effect = lambda: update_status()
        mock_mcp_server.stop.side_effect = lambda: update_status()
        mock_mcp_server.restart.side_effect = lambda: update_status()
        
        # Act
        response = test_client.post(f"/api/mcp/server/{action}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["status"] == expected_status
        
        # Verify correct method was called
        if action == "start" and not initial_state:
            mock_mcp_server.start.assert_called_once()
        elif action == "stop" and initial_state:
            mock_mcp_server.stop.assert_called_once()
        elif action == "restart":
            mock_mcp_server.restart.assert_called_once()
    
    @patch('src.api.mcp_api.mcp_server')
    def test_get_server_status(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server
    ):
        """Test getting server status."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        mock_mcp_server.get_status.return_value = {
            "status": "running",
            "uptime": 3600,
            "memory_usage": "128MB",
            "connected_clients": 5,
            "last_error": None
        }
        
        # Act
        response = test_client.get("/api/mcp/server/status")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "running"
        assert result["uptime"] == 3600
        assert result["connected_clients"] == 5
    
    # =============================================================================
    # Server Configuration Tests
    # =============================================================================
    
    @pytest.mark.parametrize("config_update", [
        pytest.param({"port": 3001}, id="update-port"),
        pytest.param({"auto_restart": False}, id="disable-auto-restart"),
        pytest.param({"env": {"NODE_ENV": "development"}}, id="update-env"),
        pytest.param(
            {"port": 3002, "command": "deno", "args": ["run", "server.ts"]},
            id="multiple-updates"
        ),
    ])
    @patch('src.api.mcp_api.mcp_server')
    def test_update_server_configuration(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        make_mcp_server_config,
        config_update
    ):
        """Test updating server configuration."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        current_config = make_mcp_server_config()
        updated_config = {**current_config, **config_update}
        
        mock_mcp_server.get_config = MagicMock(return_value=current_config)
        mock_mcp_server.update_config = AsyncMock(return_value=updated_config)
        
        # Act
        response = test_client.put("/api/mcp/server/config", json=config_update)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        # Verify updated fields
        for key, value in config_update.items():
            assert result["config"][key] == value
    
    # =============================================================================
    # Log Streaming Tests
    # =============================================================================
    
    @pytest.mark.parametrize("log_params", [
        pytest.param({}, id="default-logs"),
        pytest.param({"level": "error"}, id="error-logs-only"),
        pytest.param({"limit": 50}, id="limited-logs"),
        pytest.param({"since": "2024-01-01T00:00:00Z"}, id="logs-since-date"),
        pytest.param({"level": "info", "limit": 100}, id="filtered-and-limited"),
    ])
    @patch('src.api.mcp_api.mcp_server')
    def test_get_server_logs(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        log_params
    ):
        """Test retrieving server logs with various filters."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        
        # Generate mock logs
        all_logs = []
        for i in range(200):
            level = ["info", "warning", "error"][i % 3]
            all_logs.append({
                "timestamp": f"2024-01-01T{i//60:02d}:{i%60:02d}:00Z",
                "level": level,
                "message": f"Log message {i}",
                "source": "mcp-server"
            })
        
        # Filter logs based on params
        filtered_logs = all_logs
        if "level" in log_params:
            filtered_logs = [log for log in filtered_logs if log["level"] == log_params["level"]]
        if "since" in log_params:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= log_params["since"]]
        if "limit" in log_params:
            filtered_logs = filtered_logs[-log_params["limit"]:]
        else:
            filtered_logs = filtered_logs[-100:]  # Default limit
        
        mock_mcp_server.get_logs = MagicMock(return_value=filtered_logs)
        
        # Act
        query_string = "&".join(f"{k}={v}" for k, v in log_params.items())
        response = test_client.get(f"/api/mcp/server/logs?{query_string}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "logs" in result
        assert len(result["logs"]) <= log_params.get("limit", 100)
        
        if "level" in log_params:
            assert all(log["level"] == log_params["level"] for log in result["logs"])
    
    # =============================================================================
    # WebSocket Log Streaming Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    @patch('src.api.mcp_api.mcp_server')
    async def test_websocket_log_streaming(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server
    ):
        """Test real-time log streaming via WebSocket."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        
        # Mock log generator
        async def generate_logs():
            for i in range(5):
                yield {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": f"Real-time log {i}",
                    "source": "mcp-server"
                }
                await asyncio.sleep(0.1)
        
        mock_mcp_server.stream_logs = generate_logs
        
        # Act & Assert
        with test_client.websocket_connect("/api/mcp/server/logs/stream") as websocket:
            # Receive initial connection message
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert data["status"] == "connected"
            
            # Receive log messages
            log_count = 0
            for _ in range(3):  # Get first 3 logs
                data = websocket.receive_json()
                assert data["type"] == "log"
                assert "timestamp" in data["data"]
                assert "level" in data["data"]
                assert "message" in data["data"]
                log_count += 1
            
            assert log_count == 3
    
    # =============================================================================
    # Client Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_clients", [0, 1, 5, 10])
    @patch('src.api.mcp_api.mcp_client_service')
    async def test_list_mcp_clients(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client_config,
        num_clients
    ):
        """Test listing MCP clients."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        clients = [
            make_mcp_client_config(name=f"Client {i+1}")
            for i in range(num_clients)
        ]
        mock_mcp_client_service.list_clients.return_value = clients
        
        # Act
        response = test_client.get("/api/mcp/clients")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["clients"]) == num_clients
        assert result["total"] == num_clients
    
    @pytest.mark.parametrize("client_data,expected_status", [
        pytest.param(
            {"name": "New Client", "transport": "sse", "endpoint": "http://localhost:3000"},
            201,
            id="valid-client"
        ),
        pytest.param(
            {"name": "WebSocket Client", "transport": "websocket", "endpoint": "ws://localhost:3001"},
            201,
            id="websocket-client"
        ),
        pytest.param(
            {"name": "Client", "transport": "invalid", "endpoint": "http://localhost:3000"},
            422,
            id="invalid-transport"
        ),
        pytest.param(
            {"name": "", "transport": "sse", "endpoint": "http://localhost:3000"},
            422,
            id="empty-name"
        ),
    ])
    @patch('src.api.mcp_api.mcp_client_service')
    async def test_create_mcp_client(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client_config,
        client_data,
        expected_status
    ):
        """Test creating MCP clients."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        if expected_status == 201:
            created_client = make_mcp_client_config(**client_data)
            mock_mcp_client_service.create_client.return_value = created_client
        
        # Act
        response = test_client.post("/api/mcp/clients", json=client_data)
        
        # Assert
        assert response.status_code == expected_status
        
        if expected_status == 201:
            result = response.json()
            assert result["name"] == client_data["name"]
            assert result["transport"] == client_data["transport"]
            assert result["endpoint"] == client_data["endpoint"]
    
    # =============================================================================
    # Connection Testing Tests
    # =============================================================================
    
    @pytest.mark.parametrize("test_result", [
        pytest.param(
            {"success": True, "latency": 50, "message": "Connection successful"},
            id="successful-connection"
        ),
        pytest.param(
            {"success": False, "error": "Connection refused", "latency": None},
            id="connection-refused"
        ),
        pytest.param(
            {"success": False, "error": "Timeout", "latency": 5000},
            id="connection-timeout"
        ),
    ])
    @patch('src.api.mcp_api.mcp_client_service')
    async def test_test_client_connection(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        test_result
    ):
        """Test testing client connections."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        mock_mcp_client_service.test_connection.return_value = test_result
        
        # Act
        response = test_client.post(f"/api/mcp/clients/{client_id}/test")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == test_result["success"]
        
        if test_result["success"]:
            assert "latency" in result
            assert result["latency"] == test_result["latency"]
        else:
            assert "error" in result
    
    # =============================================================================
    # Tool Discovery Tests
    # =============================================================================
    
    @pytest.mark.parametrize("available_tools", [
        pytest.param([], id="no-tools"),
        pytest.param([
            {"name": "search", "description": "Search the web"},
            {"name": "calculate", "description": "Perform calculations"}
        ], id="basic-tools"),
        pytest.param([
            {
                "name": "complex_tool",
                "description": "Complex tool with parameters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10}
                    }
                }
            }
        ], id="tool-with-schema"),
    ])
    @patch('src.api.mcp_api.mcp_server')
    def test_discover_available_tools(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        available_tools
    ):
        """Test discovering available MCP tools."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        mock_mcp_server.get_available_tools = AsyncMock(return_value=available_tools)
        
        # Act
        response = test_client.get("/api/mcp/tools")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["tools"]) == len(available_tools)
        
        for i, tool in enumerate(result["tools"]):
            assert tool["name"] == available_tools[i]["name"]
            assert tool["description"] == available_tools[i]["description"]
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario", [
        pytest.param("server_start_failed", id="start-failure"),
        pytest.param("client_not_found", id="client-404"),
        pytest.param("server_crash", id="server-crash"),
        pytest.param("invalid_config", id="config-error"),
    ])
    @patch('src.api.mcp_api.mcp_server')
    @patch('src.api.mcp_api.mcp_client_service')
    async def test_error_handling(
        self,
        mock_client_service,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        mock_mcp_client_service,
        error_scenario
    ):
        """Test error handling for various scenarios."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        mock_client_service.return_value = mock_mcp_client_service
        
        if error_scenario == "server_start_failed":
            mock_mcp_server.start.side_effect = Exception("Port already in use")
            response = test_client.post("/api/mcp/server/start")
            expected_status = 500
            
        elif error_scenario == "client_not_found":
            mock_mcp_client_service.get_client.return_value = None
            response = test_client.get("/api/mcp/clients/nonexistent")
            expected_status = 404
            
        elif error_scenario == "server_crash":
            mock_mcp_server.get_status.side_effect = Exception("Server process crashed")
            response = test_client.get("/api/mcp/server/status")
            expected_status = 500
            
        elif error_scenario == "invalid_config":
            mock_mcp_server.update_config.side_effect = ValueError("Invalid port number")
            response = test_client.put("/api/mcp/server/config", json={"port": -1})
            expected_status = 400
        
        # Assert
        assert response.status_code == expected_status
        assert "error" in response.json() or "detail" in response.json()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_logs", [1000, 5000, 10000])
    @patch('src.api.mcp_api.mcp_server')
    def test_log_retrieval_performance(
        self,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        num_logs
    ):
        """Test performance of retrieving large numbers of logs."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        
        # Generate mock logs
        logs = [{
            "timestamp": f"2024-01-01T{i//3600:02d}:{(i//60)%60:02d}:{i%60:02d}Z",
            "level": "info",
            "message": f"Log message {i}",
            "source": "mcp-server"
        } for i in range(num_logs)]
        
        # Return only last 1000 (pagination)
        mock_mcp_server.get_logs = MagicMock(return_value=logs[-1000:])
        
        # Act & Assert
        with measure_time(f"retrieve_{num_logs}_logs", threshold=0.5):
            response = test_client.get("/api/mcp/server/logs?limit=1000")
        
        assert response.status_code == 200
        assert len(response.json()["logs"]) == min(num_logs, 1000)
    
    # =============================================================================
    # Health Monitoring Tests
    # =============================================================================
    
    @pytest.mark.parametrize("health_status", [
        pytest.param(
            {"healthy": True, "checks": {"server": "ok", "clients": "ok"}},
            id="all-healthy"
        ),
        pytest.param(
            {"healthy": False, "checks": {"server": "ok", "clients": "degraded"}},
            id="clients-degraded"
        ),
        pytest.param(
            {"healthy": False, "checks": {"server": "down", "clients": "unknown"}},
            id="server-down"
        ),
    ])
    @patch('src.api.mcp_api.mcp_server')
    @patch('src.api.mcp_api.mcp_client_service')
    def test_health_check(
        self,
        mock_client_service,
        mock_server_instance,
        test_client,
        mock_mcp_server,
        mock_mcp_client_service,
        health_status
    ):
        """Test MCP system health check."""
        # Arrange
        mock_server_instance.return_value = mock_mcp_server
        mock_client_service.return_value = mock_mcp_client_service
        
        # Setup health checks
        if health_status["checks"]["server"] == "ok":
            mock_mcp_server.is_running = True
            mock_mcp_server.get_status.return_value = {"status": "running"}
        else:
            mock_mcp_server.is_running = False
            mock_mcp_server.get_status.side_effect = Exception("Server not responding")
        
        if health_status["checks"]["clients"] == "ok":
            mock_mcp_client_service.get_health_status = AsyncMock(
                return_value={"connected": 5, "total": 5}
            )
        elif health_status["checks"]["clients"] == "degraded":
            mock_mcp_client_service.get_health_status = AsyncMock(
                return_value={"connected": 3, "total": 5}
            )
        else:
            mock_mcp_client_service.get_health_status = AsyncMock(
                side_effect=Exception("Client service unavailable")
            )
        
        # Act
        response = test_client.get("/api/mcp/health")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["healthy"] == health_status["healthy"]
        assert "checks" in result
        assert "timestamp" in result