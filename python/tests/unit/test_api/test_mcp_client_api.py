"""Unit tests for MCP Client API endpoints with enhanced patterns."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

from src.api.mcp_client_api import router
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import assert_fields_equal, measure_time


@pytest.mark.unit
@pytest.mark.standard
class TestMCPClientAPI:
    """Unit tests for MCP Client API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_mcp_client_service(self):
        """Mock MCP client service."""
        service = MagicMock()
        service.list_clients = AsyncMock(return_value=[])
        service.get_client = AsyncMock(return_value=None)
        service.create_client = AsyncMock()
        service.update_client = AsyncMock()
        service.delete_client = AsyncMock()
        service.connect_client = AsyncMock()
        service.disconnect_client = AsyncMock()
        service.execute_tool = AsyncMock()
        service.get_available_tools = AsyncMock(return_value=[])
        service.test_connection = AsyncMock()
        service.get_client_logs = AsyncMock(return_value=[])
        return service
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        client = MagicMock()
        client.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return client
    
    @pytest.fixture
    def make_mcp_client(self):
        """Factory for creating MCP client data."""
        def _make_client(
            client_id: Optional[str] = None,
            name: str = "Test Client",
            transport: str = "sse",
            endpoint: str = "http://localhost:3000",
            enabled: bool = True,
            connected: bool = False,
            metadata: Optional[Dict] = None
        ) -> Dict:
            return {
                "id": client_id or f"client-{uuid.uuid4().hex[:8]}",
                "name": name,
                "transport": transport,
                "endpoint": endpoint,
                "enabled": enabled,
                "connected": connected,
                "metadata": metadata or {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_connected": None,
                    "version": "1.0.0"
                },
                "config": {
                    "timeout": 30,
                    "retry_attempts": 3,
                    "auto_reconnect": True
                }
            }
        return _make_client
    
    @pytest.fixture
    def make_mcp_tool(self):
        """Factory for creating MCP tool data."""
        def _make_tool(
            name: str = "test_tool",
            description: str = "Test tool description",
            parameters: Optional[Dict] = None,
            client_id: Optional[str] = None
        ) -> Dict:
            return {
                "name": name,
                "description": description,
                "parameters": parameters or {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input parameter"}
                    },
                    "required": ["input"]
                },
                "client_id": client_id,
                "category": "utility"
            }
        return _make_tool
    
    # =============================================================================
    # Client CRUD Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_clients,filter_params", [
        pytest.param(0, {}, id="no-clients"),
        pytest.param(5, {}, id="all-clients"),
        pytest.param(10, {"enabled": True}, id="enabled-only"),
        pytest.param(8, {"transport": "sse"}, id="sse-clients"),
        pytest.param(12, {"connected": True}, id="connected-only"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    @patch('src.api.mcp_client_api.get_supabase_client')
    async def test_list_clients_with_filters(
        self,
        mock_get_supabase,
        mock_service,
        test_client,
        mock_mcp_client_service,
        mock_supabase_client,
        make_mcp_client,
        num_clients,
        filter_params
    ):
        """Test listing MCP clients with various filters."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        mock_get_supabase.return_value = mock_supabase_client
        
        # Create clients with varied properties
        all_clients = []
        for i in range(num_clients):
            client = make_mcp_client(
                name=f"Client {i+1}",
                transport="sse" if i % 2 == 0 else "websocket",
                enabled=i % 3 != 0,
                connected=i % 4 == 0
            )
            all_clients.append(client)
        
        # Filter clients based on params
        filtered_clients = all_clients
        if "enabled" in filter_params:
            filtered_clients = [c for c in filtered_clients if c["enabled"] == filter_params["enabled"]]
        if "transport" in filter_params:
            filtered_clients = [c for c in filtered_clients if c["transport"] == filter_params["transport"]]
        if "connected" in filter_params:
            filtered_clients = [c for c in filtered_clients if c["connected"] == filter_params["connected"]]
        
        mock_mcp_client_service.list_clients.return_value = filtered_clients
        
        # Act
        query_string = "&".join(f"{k}={v}" for k, v in filter_params.items())
        response = test_client.get(f"/api/mcp/clients?{query_string}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["clients"]) == len(filtered_clients)
        assert result["total"] == len(filtered_clients)
        
        # Verify filter was applied
        for client in result["clients"]:
            for key, value in filter_params.items():
                assert client.get(key) == value
    
    @pytest.mark.parametrize("client_data,expected_status", [
        pytest.param(
            {"name": "Valid Client", "transport": "sse", "endpoint": "http://localhost:3000"},
            201,
            id="valid-sse-client"
        ),
        pytest.param(
            {"name": "WS Client", "transport": "websocket", "endpoint": "ws://localhost:3001"},
            201,
            id="valid-ws-client"
        ),
        pytest.param(
            {"name": "STDIO Client", "transport": "stdio", "command": "node", "args": ["server.js"]},
            201,
            id="valid-stdio-client"
        ),
        pytest.param(
            {"name": "", "transport": "sse", "endpoint": "http://localhost:3000"},
            422,
            id="empty-name"
        ),
        pytest.param(
            {"name": "Client", "transport": "invalid", "endpoint": "http://localhost:3000"},
            422,
            id="invalid-transport"
        ),
        pytest.param(
            {"name": "Client", "transport": "sse", "endpoint": "not-a-url"},
            422,
            id="invalid-endpoint"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_create_client_validation(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client,
        client_data,
        expected_status
    ):
        """Test client creation with validation."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        if expected_status == 201:
            created_client = make_mcp_client(**{k: v for k, v in client_data.items() if k in ["name", "transport", "endpoint"]})
            mock_mcp_client_service.create_client.return_value = created_client
        
        # Act
        response = test_client.post("/api/mcp/clients", json=client_data)
        
        # Assert
        assert response.status_code == expected_status
        
        if expected_status == 201:
            result = response.json()
            assert result["name"] == client_data["name"]
            assert result["transport"] == client_data["transport"]
            assert "id" in result
            mock_mcp_client_service.create_client.assert_called_once()
    
    @pytest.mark.parametrize("update_fields", [
        pytest.param({"name": "Updated Name"}, id="update-name"),
        pytest.param({"endpoint": "http://localhost:4000"}, id="update-endpoint"),
        pytest.param({"enabled": False}, id="disable-client"),
        pytest.param(
            {"name": "New Name", "config": {"timeout": 60}},
            id="multiple-updates"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    @patch('src.api.mcp_client_api.get_supabase_client')
    async def test_update_client(
        self,
        mock_get_supabase,
        mock_service,
        test_client,
        mock_mcp_client_service,
        mock_supabase_client,
        make_mcp_client,
        update_fields
    ):
        """Test updating client configurations."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        mock_get_supabase.return_value = mock_supabase_client
        
        client_id = "client-to-update"
        existing_client = make_mcp_client(client_id=client_id)
        updated_client = {**existing_client, **update_fields}
        
        # Mock get and update
        mock_mcp_client_service.get_client.return_value = existing_client
        mock_mcp_client_service.update_client.return_value = updated_client
        
        # Act
        response = test_client.put(f"/api/mcp/clients/{client_id}", json=update_fields)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        for key, value in update_fields.items():
            if key == "config":
                assert result["config"]["timeout"] == value["timeout"]
            else:
                assert result[key] == value
    
    # =============================================================================
    # Connection Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("initial_state,action,expected_state", [
        pytest.param(False, "connect", True, id="connect-disconnected"),
        pytest.param(True, "disconnect", False, id="disconnect-connected"),
        pytest.param(True, "reconnect", True, id="reconnect-client"),
        pytest.param(False, "disconnect", False, id="disconnect-already-disconnected"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_connection_management(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client,
        initial_state,
        action,
        expected_state
    ):
        """Test client connection management."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        client = make_mcp_client(client_id=client_id, connected=initial_state)
        mock_mcp_client_service.get_client.return_value = client
        
        # Setup action results
        if action == "connect":
            mock_mcp_client_service.connect_client.return_value = {**client, "connected": True}
        elif action == "disconnect":
            mock_mcp_client_service.disconnect_client.return_value = {**client, "connected": False}
        elif action == "reconnect":
            mock_mcp_client_service.disconnect_client.return_value = {**client, "connected": False}
            mock_mcp_client_service.connect_client.return_value = {**client, "connected": True}
        
        # Act
        response = test_client.post(f"/api/mcp/clients/{client_id}/{action}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["client"]["connected"] == expected_state
        
        # Verify correct methods called
        if action == "connect" and not initial_state:
            mock_mcp_client_service.connect_client.assert_called_once_with(client_id)
        elif action == "disconnect" and initial_state:
            mock_mcp_client_service.disconnect_client.assert_called_once_with(client_id)
        elif action == "reconnect":
            mock_mcp_client_service.disconnect_client.assert_called_once()
            mock_mcp_client_service.connect_client.assert_called_once()
    
    @pytest.mark.parametrize("connection_result", [
        pytest.param(
            {"success": True, "latency": 45, "version": "1.0.0"},
            id="successful-test"
        ),
        pytest.param(
            {"success": False, "error": "Connection refused"},
            id="connection-refused"
        ),
        pytest.param(
            {"success": False, "error": "Timeout after 30s"},
            id="timeout"
        ),
        pytest.param(
            {"success": True, "latency": 250, "warning": "High latency detected"},
            id="high-latency"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_connection_testing(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        connection_result
    ):
        """Test connection testing functionality."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-to-test"
        
        mock_mcp_client_service.test_connection.return_value = connection_result
        
        # Act
        response = test_client.post(f"/api/mcp/clients/{client_id}/test")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == connection_result["success"]
        
        if connection_result["success"]:
            assert result["latency"] == connection_result["latency"]
            if "warning" in connection_result:
                assert "warning" in result
        else:
            assert result["error"] == connection_result["error"]
    
    # =============================================================================
    # Tool Execution Tests
    # =============================================================================
    
    @pytest.mark.parametrize("tool_params,execution_result", [
        pytest.param(
            {"tool": "search", "params": {"query": "test"}},
            {"success": True, "result": {"hits": 10}},
            id="successful-execution"
        ),
        pytest.param(
            {"tool": "calculate", "params": {"expression": "2+2"}},
            {"success": True, "result": 4},
            id="simple-calculation"
        ),
        pytest.param(
            {"tool": "invalid_tool", "params": {}},
            {"success": False, "error": "Tool not found"},
            id="tool-not-found"
        ),
        pytest.param(
            {"tool": "search", "params": {"invalid": "param"}},
            {"success": False, "error": "Invalid parameters"},
            id="invalid-params"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_tool_execution(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        tool_params,
        execution_result
    ):
        """Test tool execution on MCP clients."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        if execution_result["success"]:
            mock_mcp_client_service.execute_tool.return_value = execution_result["result"]
        else:
            mock_mcp_client_service.execute_tool.side_effect = HTTPException(
                status_code=400,
                detail=execution_result["error"]
            )
        
        # Act
        response = test_client.post(
            f"/api/mcp/clients/{client_id}/execute",
            json=tool_params
        )
        
        # Assert
        if execution_result["success"]:
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["result"] == execution_result["result"]
        else:
            assert response.status_code == 400
            assert execution_result["error"] in response.json()["detail"]
    
    @pytest.mark.parametrize("available_tools", [
        pytest.param([], id="no-tools"),
        pytest.param([
            {"name": "search", "description": "Search the web"},
            {"name": "calculate", "description": "Perform calculations"}
        ], id="basic-tools"),
        pytest.param([
            {
                "name": "complex_tool",
                "description": "Complex tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "options": {"type": "object"}
                    }
                }
            }
        ], id="complex-tool-schema"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_get_client_tools(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_tool,
        available_tools
    ):
        """Test retrieving available tools from a client."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        tools = [make_mcp_tool(**tool, client_id=client_id) for tool in available_tools]
        mock_mcp_client_service.get_available_tools.return_value = tools
        
        # Act
        response = test_client.get(f"/api/mcp/clients/{client_id}/tools")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["tools"]) == len(available_tools)
        assert result["client_id"] == client_id
    
    # =============================================================================
    # Auto-reconnection Tests
    # =============================================================================
    
    @pytest.mark.parametrize("reconnect_config", [
        pytest.param(
            {"enabled": True, "interval": 30, "max_attempts": 5},
            id="standard-reconnect"
        ),
        pytest.param(
            {"enabled": False},
            id="disabled-reconnect"
        ),
        pytest.param(
            {"enabled": True, "interval": 60, "max_attempts": 3, "backoff": True},
            id="backoff-strategy"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_auto_reconnection_config(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        reconnect_config
    ):
        """Test auto-reconnection configuration."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        # Act
        response = test_client.put(
            f"/api/mcp/clients/{client_id}/reconnection",
            json=reconnect_config
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["config"]["enabled"] == reconnect_config["enabled"]
        
        if reconnect_config["enabled"]:
            assert result["config"]["interval"] == reconnect_config.get("interval", 30)
            assert result["config"]["max_attempts"] == reconnect_config.get("max_attempts", 5)
    
    # =============================================================================
    # Multi-client Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_clients,action", [
        pytest.param(3, "connect_all", id="connect-multiple"),
        pytest.param(5, "disconnect_all", id="disconnect-multiple"),
        pytest.param(4, "enable_all", id="enable-multiple"),
        pytest.param(6, "disable_all", id="disable-multiple"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_batch_client_operations(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client,
        num_clients,
        action
    ):
        """Test batch operations on multiple clients."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        client_ids = [f"client-{i}" for i in range(num_clients)]
        clients = [make_mcp_client(client_id=cid) for cid in client_ids]
        
        # Mock batch operation results
        if action == "connect_all":
            updated_clients = [{**c, "connected": True} for c in clients]
        elif action == "disconnect_all":
            updated_clients = [{**c, "connected": False} for c in clients]
        elif action == "enable_all":
            updated_clients = [{**c, "enabled": True} for c in clients]
        elif action == "disable_all":
            updated_clients = [{**c, "enabled": False} for c in clients]
        
        mock_mcp_client_service.batch_update_clients = AsyncMock(return_value=updated_clients)
        
        # Act
        response = test_client.post(f"/api/mcp/clients/batch/{action}", json={
            "client_ids": client_ids
        })
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["updated_count"] == num_clients
        assert len(result["clients"]) == num_clients
    
    # =============================================================================
    # Logging and Monitoring Tests
    # =============================================================================
    
    @pytest.mark.parametrize("log_params", [
        pytest.param({}, id="default-logs"),
        pytest.param({"level": "error"}, id="error-only"),
        pytest.param({"limit": 50}, id="limited-logs"),
        pytest.param({"since": "2024-01-01T00:00:00Z"}, id="logs-since"),
        pytest.param({"level": "info", "limit": 100}, id="filtered-limited"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_get_client_logs(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        log_params
    ):
        """Test retrieving client logs with filters."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        client_id = "client-123"
        
        # Generate mock logs
        all_logs = []
        for i in range(200):
            level = ["info", "warning", "error"][i % 3]
            all_logs.append({
                "timestamp": f"2024-01-01T{i//60:02d}:{i%60:02d}:00Z",
                "level": level,
                "message": f"Client log message {i}",
                "client_id": client_id
            })
        
        # Apply filters
        filtered_logs = all_logs
        if "level" in log_params:
            filtered_logs = [log for log in filtered_logs if log["level"] == log_params["level"]]
        if "since" in log_params:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= log_params["since"]]
        if "limit" in log_params:
            filtered_logs = filtered_logs[-log_params["limit"]:]
        else:
            filtered_logs = filtered_logs[-100:]
        
        mock_mcp_client_service.get_client_logs.return_value = filtered_logs
        
        # Act
        query_string = "&".join(f"{k}={v}" for k, v in log_params.items())
        response = test_client.get(f"/api/mcp/clients/{client_id}/logs?{query_string}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["logs"]) <= log_params.get("limit", 100)
        
        if "level" in log_params:
            assert all(log["level"] == log_params["level"] for log in result["logs"])
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario", [
        pytest.param("client_not_found", id="404-client"),
        pytest.param("connection_failed", id="connection-error"),
        pytest.param("tool_execution_failed", id="tool-error"),
        pytest.param("invalid_config", id="config-error"),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_error_handling(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        error_scenario
    ):
        """Test error handling for various scenarios."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        if error_scenario == "client_not_found":
            mock_mcp_client_service.get_client.return_value = None
            response = test_client.get("/api/mcp/clients/nonexistent")
            expected_status = 404
            
        elif error_scenario == "connection_failed":
            mock_mcp_client_service.connect_client.side_effect = Exception("Connection failed")
            response = test_client.post("/api/mcp/clients/client-123/connect")
            expected_status = 500
            
        elif error_scenario == "tool_execution_failed":
            mock_mcp_client_service.execute_tool.side_effect = Exception("Tool execution error")
            response = test_client.post("/api/mcp/clients/client-123/execute", json={
                "tool": "test",
                "params": {}
            })
            expected_status = 500
            
        elif error_scenario == "invalid_config":
            response = test_client.put("/api/mcp/clients/client-123", json={
                "config": {"invalid_field": "value"}
            })
            expected_status = 422
        
        # Assert
        assert response.status_code == expected_status
        assert "error" in response.json() or "detail" in response.json()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_clients", [10, 50, 100])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_list_clients_performance(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        make_mcp_client,
        num_clients
    ):
        """Test performance of listing large numbers of clients."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        clients = [
            make_mcp_client(name=f"Client {i}")
            for i in range(num_clients)
        ]
        mock_mcp_client_service.list_clients.return_value = clients
        
        # Act & Assert
        with measure_time(f"list_{num_clients}_clients", threshold=0.5):
            response = test_client.get("/api/mcp/clients")
        
        assert response.status_code == 200
        assert len(response.json()["clients"]) == num_clients
    
    # =============================================================================
    # SSE Transport Tests
    # =============================================================================
    
    @pytest.mark.parametrize("sse_config", [
        pytest.param(
            {"keepalive": 30, "retry": 5000},
            id="standard-sse"
        ),
        pytest.param(
            {"keepalive": 60, "retry": 10000, "headers": {"Authorization": "Bearer token"}},
            id="authenticated-sse"
        ),
        pytest.param(
            {"keepalive": 15, "retry": 3000, "compression": True},
            id="compressed-sse"
        ),
    ])
    @patch('src.api.mcp_client_api.mcp_client_service')
    async def test_sse_transport_configuration(
        self,
        mock_service,
        test_client,
        mock_mcp_client_service,
        sse_config
    ):
        """Test SSE transport specific configurations."""
        # Arrange
        mock_service.return_value = mock_mcp_client_service
        
        client_data = {
            "name": "SSE Client",
            "transport": "sse",
            "endpoint": "http://localhost:3000/events",
            "transport_config": sse_config
        }
        
        created_client = {
            "id": "sse-client-123",
            **client_data
        }
        mock_mcp_client_service.create_client.return_value = created_client
        
        # Act
        response = test_client.post("/api/mcp/clients", json=client_data)
        
        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["transport"] == "sse"
        assert result["transport_config"]["keepalive"] == sse_config["keepalive"]
        assert result["transport_config"]["retry"] == sse_config["retry"]