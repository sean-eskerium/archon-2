"""Unit tests for MCP Client API endpoints."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import uuid
from fastapi.testclient import TestClient
from src.api.mcp_client_api import (
    router, MCPClientConfig, MCPClient, MCPClientManager,
    TransportType, ClientStatus, ToolCallRequest
)


class TestMCPClientManager:
    """Unit tests for MCPClientManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create MCPClientManager instance."""
        return MCPClientManager()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def sample_client_config(self):
        """Sample client configuration."""
        return MCPClientConfig(
            name="Test Client",
            transport_type=TransportType.SSE,
            connection_config={"url": "http://localhost:8051"},
            auto_connect=True,
            health_check_interval=30,
            is_default=False
        )
    
    @pytest.fixture
    def sample_client_data(self):
        """Sample client database data."""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test Client",
            "transport_type": "sse",
            "connection_config": {"url": "http://localhost:8051"},
            "status": "disconnected",
            "auto_connect": True,
            "health_check_interval": 30,
            "last_seen": None,
            "last_error": None,
            "is_default": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_supabase_client')
    async def test_get_all_clients(self, mock_get_client, manager, mock_supabase_client, sample_client_data):
        """Test retrieving all clients from database."""
        mock_get_client.return_value = mock_supabase_client
        mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [sample_client_data]
        
        clients = await manager.get_all_clients()
        
        assert len(clients) == 1
        assert clients[0].name == "Test Client"
        assert clients[0].transport_type == TransportType.SSE
        mock_supabase_client.table.assert_called_with("mcp_clients")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_supabase_client')
    async def test_create_client_success(self, mock_get_client, manager, mock_supabase_client, sample_client_config):
        """Test successful client creation."""
        mock_get_client.return_value = mock_supabase_client
        
        # Mock name check - no existing client
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock insert
        created_data = {
            "id": str(uuid.uuid4()),
            "name": sample_client_config.name,
            "transport_type": sample_client_config.transport_type.value,
            "connection_config": sample_client_config.connection_config,
            "status": ClientStatus.DISCONNECTED.value,
            "auto_connect": sample_client_config.auto_connect,
            "health_check_interval": sample_client_config.health_check_interval,
            "is_default": sample_client_config.is_default,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [created_data]
        
        client = await manager.create_client(sample_client_config)
        
        assert client.name == sample_client_config.name
        assert client.status == ClientStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_supabase_client')
    async def test_create_client_duplicate_name(self, mock_get_client, manager, mock_supabase_client, sample_client_config):
        """Test client creation with duplicate name."""
        mock_get_client.return_value = mock_supabase_client
        
        # Mock existing client with same name
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "existing"}]
        
        with pytest.raises(ValueError, match="already exists"):
            await manager.create_client(sample_client_config)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_supabase_client')
    @patch('src.api.mcp_client_api.get_mcp_client_service')
    async def test_connect_client_success(self, mock_get_service, mock_get_client, manager, mock_supabase_client, sample_client_data):
        """Test successful client connection."""
        mock_get_client.return_value = mock_supabase_client
        
        # Mock MCP service
        mock_service = MagicMock()
        mock_service.add_client = AsyncMock(return_value={"success": True})
        mock_service.connect_client = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        # Mock database operations
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_client_data]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = await manager.connect_client(sample_client_data["id"])
        
        assert result["success"] is True
        assert sample_client_data["id"] in manager.active_clients
        mock_service.connect_client.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_disconnect_client(self, manager):
        """Test client disconnection."""
        client_id = "test-client-123"
        
        # Setup active client
        manager.active_clients[client_id] = {"service_client": True}
        manager.health_check_tasks[client_id] = MagicMock()
        manager.health_check_tasks[client_id].cancel = MagicMock()
        
        with patch('src.api.mcp_client_api.get_supabase_client') as mock_get_client:
            mock_supabase = MagicMock()
            mock_get_client.return_value = mock_supabase
            
            result = await manager.disconnect_client(client_id)
            
            assert result["success"] is True
            assert client_id not in manager.active_clients
            assert client_id not in manager.health_check_tasks
            manager.health_check_tasks[client_id].cancel.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('aiohttp.ClientSession')
    async def test_connect_sse_client(self, mock_session_class, manager):
        """Test SSE client connection."""
        client_id = "test-client"
        config = {"url": "http://localhost:8051"}
        
        # Mock successful HTTP connection
        mock_response = MagicMock()
        mock_response.status = 200
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await manager._connect_sse_client(client_id, config)
        
        assert result["type"] == "sse"
        assert result["url"] == config["url"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_mcp_client_service')
    async def test_perform_health_check(self, mock_get_service, manager):
        """Test health check functionality."""
        client_id = "test-client"
        
        # Mock service
        mock_service = MagicMock()
        mock_service.clients = {client_id: MagicMock()}
        mock_service.is_client_connected = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        is_healthy = await manager._perform_health_check(client_id)
        
        assert is_healthy is True
        mock_service.is_client_connected.assert_called_once_with(client_id)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.mcp_client_api.get_mcp_client_service')
    async def test_discover_tools(self, mock_get_service, manager):
        """Test tool discovery from client."""
        client_id = "test-client"
        
        # Mock tools
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        
        mock_service = MagicMock()
        mock_service.get_client_tools = AsyncMock(return_value=[mock_tool])
        mock_get_service.return_value = mock_service
        
        await manager._discover_tools(client_id)
        
        mock_service.get_client_tools.assert_called_once_with(client_id)


class TestMCPClientAPIEndpoints:
    """Unit tests for MCP Client API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_client_manager(self):
        """Mock client manager."""
        with patch('src.api.mcp_client_api.client_manager') as mock:
            yield mock
    
    @pytest.mark.unit
    def test_list_clients_endpoint(self, test_client, mock_client_manager):
        """Test GET /clients endpoint."""
        # Mock clients
        mock_clients = [
            MCPClient(
                id="client1",
                name="Client 1",
                transport_type=TransportType.SSE,
                connection_config={"url": "http://localhost:8051"},
                status=ClientStatus.CONNECTED,
                auto_connect=True,
                health_check_interval=30,
                last_seen=datetime.now(),
                last_error=None,
                is_default=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        mock_client_manager.get_all_clients = AsyncMock(return_value=mock_clients)
        
        response = test_client.get("/api/mcp/clients/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Client 1"
        assert data[0]["status"] == "connected"
    
    @pytest.mark.unit
    def test_create_client_endpoint(self, test_client, mock_client_manager):
        """Test POST /clients endpoint."""
        request_data = {
            "name": "New Client",
            "transport_type": "sse",
            "connection_config": {"url": "http://localhost:8052"},
            "auto_connect": False,
            "health_check_interval": 60,
            "is_default": False
        }
        
        mock_created_client = MCPClient(
            id="new-client-id",
            name="New Client",
            transport_type=TransportType.SSE,
            connection_config={"url": "http://localhost:8052"},
            status=ClientStatus.DISCONNECTED,
            auto_connect=False,
            health_check_interval=60,
            last_seen=None,
            last_error=None,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_client_manager.create_client = AsyncMock(return_value=mock_created_client)
        
        response = test_client.post("/api/mcp/clients/", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Client"
        assert data["id"] == "new-client-id"
    
    @pytest.mark.unit
    def test_connect_client_endpoint(self, test_client, mock_client_manager):
        """Test POST /clients/{client_id}/connect endpoint."""
        client_id = "test-client-123"
        
        mock_client_manager.connect_client = AsyncMock(return_value={
            "success": True,
            "message": "Connected successfully"
        })
        
        response = test_client.post(f"/api/mcp/clients/{client_id}/connect")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_client_manager.connect_client.assert_called_once_with(client_id)
    
    @pytest.mark.unit
    def test_disconnect_client_endpoint(self, test_client, mock_client_manager):
        """Test POST /clients/{client_id}/disconnect endpoint."""
        client_id = "test-client-123"
        
        mock_client_manager.disconnect_client = AsyncMock(return_value={
            "success": True,
            "message": "Disconnected successfully"
        })
        
        response = test_client.post(f"/api/mcp/clients/{client_id}/disconnect")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.unit
    def test_client_config_validation(self):
        """Test MCPClientConfig validation."""
        # Valid SSE config
        config = MCPClientConfig(
            name="Valid Client",
            transport_type=TransportType.SSE,
            connection_config={"url": "http://localhost:8051"}
        )
        assert config.name == "Valid Client"
        
        # Invalid SSE config - missing URL
        with pytest.raises(ValueError, match="SSE transport requires"):
            MCPClientConfig(
                name="Invalid Client",
                transport_type=TransportType.SSE,
                connection_config={}
            )
        
        # Invalid URL format
        with pytest.raises(ValueError, match="must start with http"):
            MCPClientConfig(
                name="Bad URL Client",
                transport_type=TransportType.SSE,
                connection_config={"url": "not-a-url"}
            )
    
    @pytest.mark.unit
    def test_tool_call_request_model(self):
        """Test ToolCallRequest model."""
        request = ToolCallRequest(
            client_id="client-123",
            tool_name="test_tool",
            arguments={"param1": "value1"}
        )
        
        assert request.client_id == "client-123"
        assert request.tool_name == "test_tool"
        assert request.arguments["param1"] == "value1"
        
        # Test with empty arguments
        request2 = ToolCallRequest(
            client_id="client-456",
            tool_name="another_tool"
        )
        assert request2.arguments == {}
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_monitor_task(self, mock_client_manager):
        """Test health monitoring background task."""
        manager = MCPClientManager()
        client_id = "test-client"
        
        # Mock health check
        manager._perform_health_check = AsyncMock(return_value=True)
        
        with patch('src.api.mcp_client_api.get_supabase_client') as mock_get_client:
            mock_supabase = MagicMock()
            mock_get_client.return_value = mock_supabase
            
            # Set up active client
            manager.active_clients[client_id] = {}
            
            # Run health monitor for one iteration
            health_task = asyncio.create_task(manager._health_monitor(client_id, 1))
            await asyncio.sleep(0.2)
            health_task.cancel()
            
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            # Verify health check was called
            manager._perform_health_check.assert_called()