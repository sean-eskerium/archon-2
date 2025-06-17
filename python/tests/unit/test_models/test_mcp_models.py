"""Unit tests for MCP models."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.mcp_models import (
    SSEConfig, StdioConfig, DockerConfig, NPXConfig,
    MCPTool, MCPClientBase, MCPClient, MCPClientCreate,
    MCPClientUpdate, MCPClientStatus, MCPClientSession,
    MCPHealthCheck, MCPToolCall, MCPToolCallResponse,
    MCPClientListResponse, MCPClientToolsResponse,
    MCP_CLIENT_TEMPLATES
)


class TestTransportConfigs:
    """Unit tests for transport configuration models."""
    
    @pytest.mark.unit
    def test_sse_config_defaults(self):
        """Test SSEConfig with default values."""
        config = SSEConfig(host="example.com", port=8080)
        
        assert config.host == "example.com"
        assert config.port == 8080
        assert config.endpoint == "/sse"
        assert config.timeout == 30
        assert config.auth_headers is None
    
    @pytest.mark.unit
    def test_stdio_config_validation(self):
        """Test StdioConfig validation."""
        config = StdioConfig(command="python", args=["-m", "server"])
        
        assert config.command == "python"
        assert config.args == ["-m", "server"]
        assert config.timeout == 30
        assert config.env_vars is None
    
    @pytest.mark.unit
    def test_docker_config_with_options(self):
        """Test DockerConfig with all options."""
        config = DockerConfig(
            image="mcp-server:latest",
            command=["python", "server.py"],
            ports={"8080": "8080"},
            env_vars={"API_KEY": "test"},
            volumes={"/data": "/app/data"},
            auto_remove=False,
            network="bridge"
        )
        
        assert config.image == "mcp-server:latest"
        assert config.ports == {"8080": "8080"}
        assert config.auto_remove is False
    
    @pytest.mark.unit
    def test_npx_config_defaults(self):
        """Test NPXConfig with defaults."""
        config = NPXConfig(package="@example/mcp-server")
        
        assert config.package == "@example/mcp-server"
        assert config.version == "latest"
        assert config.timeout == 60
        assert config.registry is None


class TestMCPTool:
    """Unit tests for MCPTool model."""
    
    @pytest.mark.unit
    def test_mcp_tool_creation(self):
        """Test MCPTool creation."""
        tool = MCPTool(
            name="search",
            description="Search the web",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}},
            client_id="client-123",
            client_name="Brave Search",
            client_status="connected",
            discovered_at=datetime.now()
        )
        
        assert tool.name == "search"
        assert tool.description == "Search the web"
        assert "query" in tool.inputSchema["properties"]
        assert tool.client_status == "connected"
    
    @pytest.mark.unit
    def test_mcp_tool_minimal(self):
        """Test MCPTool with minimal fields."""
        tool = MCPTool(
            name="test",
            description="Test tool",
            inputSchema={}
        )
        
        assert tool.client_id is None
        assert tool.client_status is None
        assert tool.discovered_at is None


class TestMCPClientModels:
    """Unit tests for MCP client models."""
    
    @pytest.mark.unit
    def test_mcp_client_base_validation(self):
        """Test MCPClientBase validation."""
        # Valid client
        client = MCPClientBase(
            name="Test Client",
            transport_type="sse",
            connection_config={"host": "localhost", "port": 8080}
        )
        
        assert client.name == "Test Client"
        assert client.transport_type == "sse"
        assert client.auto_connect is True
        assert client.health_check_interval == 30
    
    @pytest.mark.unit
    def test_mcp_client_base_name_validation(self):
        """Test name validation in MCPClientBase."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            MCPClientBase(
                name="",
                transport_type="sse",
                connection_config={}
            )
        
        # Whitespace-only name should fail
        with pytest.raises(ValidationError):
            MCPClientBase(
                name="   ",
                transport_type="sse",
                connection_config={}
            )
    
    @pytest.mark.unit
    def test_mcp_client_base_config_validation(self):
        """Test connection config validation based on transport type."""
        # Valid SSE config
        client = MCPClientBase(
            name="SSE Client",
            transport_type="sse",
            connection_config={"host": "localhost", "port": 8080}
        )
        assert client.transport_type == "sse"
        
        # Invalid SSE config (missing required fields)
        with pytest.raises(ValidationError):
            MCPClientBase(
                name="Bad SSE",
                transport_type="sse",
                connection_config={"invalid": "config"}
            )
    
    @pytest.mark.unit
    def test_mcp_client_full_model(self):
        """Test complete MCPClient model."""
        now = datetime.now()
        client = MCPClient(
            id="client-123",
            name="Test Client",
            transport_type="stdio",
            connection_config={"command": "python"},
            status="connected",
            last_seen=now,
            last_error=None,
            is_default=True,
            tools_count=5,
            created_at=now,
            updated_at=now
        )
        
        assert client.id == "client-123"
        assert client.status == "connected"
        assert client.is_default is True
        assert client.tools_count == 5
    
    @pytest.mark.unit
    def test_mcp_client_update_model(self):
        """Test MCPClientUpdate model."""
        update = MCPClientUpdate(
            name="Updated Name",
            auto_connect=False,
            health_check_interval=60
        )
        
        assert update.name == "Updated Name"
        assert update.auto_connect is False
        assert update.connection_config is None
    
    @pytest.mark.unit
    def test_health_check_interval_validation(self):
        """Test health check interval validation."""
        # Valid range
        client = MCPClientBase(
            name="Test",
            transport_type="sse",
            connection_config={},
            health_check_interval=60
        )
        assert client.health_check_interval == 60
        
        # Too low
        with pytest.raises(ValidationError):
            MCPClientBase(
                name="Test",
                transport_type="sse",
                connection_config={},
                health_check_interval=5
            )
        
        # Too high
        with pytest.raises(ValidationError):
            MCPClientBase(
                name="Test",
                transport_type="sse",
                connection_config={},
                health_check_interval=4000
            )


class TestMCPStatusModels:
    """Unit tests for status and monitoring models."""
    
    @pytest.mark.unit
    def test_mcp_client_status(self):
        """Test MCPClientStatus model."""
        status = MCPClientStatus(
            id="client-123",
            name="Test Client",
            status="connected",
            transport_type="sse",
            last_seen=datetime.now(),
            tools_count=10,
            uptime_seconds=3600
        )
        
        assert status.uptime_seconds == 3600
        assert status.tools_count == 10
        assert status.health_checks is None
    
    @pytest.mark.unit
    def test_mcp_client_session(self):
        """Test MCPClientSession model."""
        session = MCPClientSession(
            id="session-123",
            client_id="client-123",
            session_start=datetime.now(),
            total_tool_calls=50,
            successful_calls=48,
            failed_calls=2,
            avg_response_time_ms=125.5
        )
        
        assert session.total_tool_calls == 50
        assert session.successful_calls == 48
        assert session.is_active is True
        assert session.memory_usage_mb is None
    
    @pytest.mark.unit
    def test_mcp_health_check(self):
        """Test MCPHealthCheck model."""
        check = MCPHealthCheck(
            id="check-123",
            client_id="client-123",
            check_time=datetime.now(),
            status="success",
            response_time_ms=50
        )
        
        assert check.status == "success"
        assert check.response_time_ms == 50
        assert check.error_message is None


class TestMCPToolModels:
    """Unit tests for tool-related models."""
    
    @pytest.mark.unit
    def test_mcp_tool_call(self):
        """Test MCPToolCall model."""
        call = MCPToolCall(
            tool_name="search",
            arguments={"query": "test search", "limit": 10}
        )
        
        assert call.tool_name == "search"
        assert call.arguments["query"] == "test search"
        assert call.client_id is None
    
    @pytest.mark.unit
    def test_mcp_tool_call_response(self):
        """Test MCPToolCallResponse model."""
        response = MCPToolCallResponse(
            success=True,
            result={"results": ["item1", "item2"]},
            client_id="client-123",
            client_name="Search Client",
            execution_time_ms=150,
            timestamp=datetime.now()
        )
        
        assert response.success is True
        assert len(response.result["results"]) == 2
        assert response.execution_time_ms == 150


class TestMCPResponseModels:
    """Unit tests for response models."""
    
    @pytest.mark.unit
    def test_mcp_client_list_response(self):
        """Test MCPClientListResponse model."""
        response = MCPClientListResponse(
            success=True,
            clients=[],
            total_count=0,
            connected_count=0,
            total_tools=0
        )
        
        assert response.success is True
        assert response.total_count == 0
    
    @pytest.mark.unit
    def test_mcp_client_tools_response(self):
        """Test MCPClientToolsResponse model."""
        tool = MCPTool(
            name="test",
            description="Test",
            inputSchema={}
        )
        
        response = MCPClientToolsResponse(
            success=True,
            client={"id": "123", "name": "Test"},
            tools=[tool],
            tools_count=1
        )
        
        assert response.tools_count == 1
        assert response.tools[0].name == "test"


class TestMCPTemplates:
    """Unit tests for MCP client templates."""
    
    @pytest.mark.unit
    def test_mcp_client_templates_structure(self):
        """Test MCP_CLIENT_TEMPLATES structure."""
        assert "brave-search" in MCP_CLIENT_TEMPLATES
        assert "weather" in MCP_CLIENT_TEMPLATES
        assert "filesystem" in MCP_CLIENT_TEMPLATES
        assert "postgres" in MCP_CLIENT_TEMPLATES
        
        # Check brave-search template
        brave = MCP_CLIENT_TEMPLATES["brave-search"]
        assert brave["name"] == "Brave Search"
        assert brave["transport_type"] == "npx"
        assert brave["connection_config"]["package"] == "@modelcontextprotocol/server-brave-search"
        assert "description" in brave