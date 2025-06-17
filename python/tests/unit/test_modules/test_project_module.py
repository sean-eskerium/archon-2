"""Unit tests for Project Module MCP tools."""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.modules.project_module import register_project_tools
from mcp.server.fastmcp import FastMCP, Context


class TestProjectModule:
    """Unit tests for project module MCP tools."""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP server."""
        return MagicMock(spec=FastMCP)
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context.supabase_client = MagicMock()
        return ctx
    
    @pytest.fixture
    def mock_services(self):
        """Mock all service classes."""
        with patch('src.modules.project_module.ProjectService') as mock_project:
            with patch('src.modules.project_module.TaskService') as mock_task:
                with patch('src.modules.project_module.DocumentService') as mock_doc:
                    with patch('src.modules.project_module.VersioningService') as mock_version:
                        yield {
                            'project': mock_project,
                            'task': mock_task,
                            'document': mock_doc,
                            'version': mock_version
                        }
    
    @pytest.mark.unit
    def test_register_project_tools(self, mock_mcp):
        """Test that all tools are registered with MCP."""
        register_project_tools(mock_mcp)
        
        # Verify all tools were registered
        assert mock_mcp.tool.call_count >= 5  # At least 5 tools should be registered
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_project_create(self, mock_context, mock_services):
        """Test manage_project create action."""
        # Setup mock
        mock_project_service = MagicMock()
        mock_project_service.create_project.return_value = (True, {
            "project": {"id": "project-123", "title": "Test Project"}
        })
        mock_services['project'].return_value = mock_project_service
        
        # Register tools and get manage_project function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_project = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_project' in tool_name:
                manage_project = tool_func
                break
        
        # Test create action
        result = await manage_project(
            mock_context,
            action="create",
            title="Test Project",
            github_repo="https://github.com/test/repo"
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["project"]["id"] == "project-123"
        mock_project_service.create_project.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_project_list(self, mock_context, mock_services):
        """Test manage_project list action."""
        # Setup mock
        mock_project_service = MagicMock()
        mock_project_service.list_projects.return_value = (True, {
            "projects": [
                {"id": "p1", "title": "Project 1"},
                {"id": "p2", "title": "Project 2"}
            ]
        })
        mock_services['project'].return_value = mock_project_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_project = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_project' in tool_name:
                manage_project = tool_func
                break
        
        # Test list action
        result = await manage_project(mock_context, action="list")
        
        data = json.loads(result)
        assert data["success"] is True
        assert len(data["projects"]) == 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_task_create(self, mock_context, mock_services):
        """Test manage_task create action."""
        # Setup mock
        mock_task_service = MagicMock()
        mock_task_service.create_task = AsyncMock(return_value=(True, {
            "task": {"id": "task-123", "title": "Test Task"}
        }))
        mock_services['task'].return_value = mock_task_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_task = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_task' in tool_name:
                manage_task = tool_func
                break
        
        # Test create action
        result = await manage_task(
            mock_context,
            action="create",
            project_id="project-123",
            title="Test Task",
            description="Test description",
            assignee="User"
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["task"]["id"] == "task-123"
        mock_task_service.create_task.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_task_update_with_websocket(self, mock_context, mock_services):
        """Test manage_task update action with WebSocket broadcast."""
        # Setup mock
        mock_task_service = MagicMock()
        mock_task_service.update_task = AsyncMock(return_value=(True, {
            "task": {"id": "task-123", "status": "doing"}
        }))
        mock_services['task'].return_value = mock_task_service
        
        # Add progress callback to context
        mock_context.progress_callback = AsyncMock()
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_task = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_task' in tool_name:
                manage_task = tool_func
                break
        
        # Test update action
        result = await manage_task(
            mock_context,
            action="update",
            task_id="task-123",
            update_fields={"status": "doing"}
        )
        
        data = json.loads(result)
        assert data["success"] is True
        
        # Verify WebSocket broadcast was attempted
        mock_context.progress_callback.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_document_add(self, mock_context, mock_services):
        """Test manage_document add action."""
        # Setup mock
        mock_doc_service = MagicMock()
        mock_doc_service.add_document.return_value = (True, {
            "document": {"id": "doc-123", "title": "Test Doc"}
        })
        mock_services['document'].return_value = mock_doc_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_document = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_document' in tool_name:
                manage_document = tool_func
                break
        
        # Test add action
        result = await manage_document(
            mock_context,
            action="add",
            project_id="project-123",
            document_type="prd",
            title="Test PRD",
            content={"overview": "Test overview"},
            metadata={"tags": ["test"], "author": "TestUser"}
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["document"]["id"] == "doc-123"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_manage_versions_create(self, mock_context, mock_services):
        """Test manage_versions create action."""
        # Setup mock
        mock_version_service = MagicMock()
        mock_version_service.create_version.return_value = (True, {
            "version_number": 1,
            "snapshot_id": "snap-123"
        })
        mock_services['version'].return_value = mock_version_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_versions = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_versions' in tool_name:
                manage_versions = tool_func
                break
        
        # Test create version
        result = await manage_versions(
            mock_context,
            action="create",
            project_id="project-123",
            field_name="docs",
            content={"docs": [{"id": "doc1", "content": "test"}]},
            change_summary="Initial version"
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["version_number"] == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling(self, mock_context, mock_services):
        """Test error handling in tools."""
        # Setup mock to raise exception
        mock_project_service = MagicMock()
        mock_project_service.create_project.side_effect = Exception("Database error")
        mock_services['project'].return_value = mock_project_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_project = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_project' in tool_name:
                manage_project = tool_func
                break
        
        # Test error handling
        result = await manage_project(
            mock_context,
            action="create",
            title="Test Project"
        )
        
        data = json.loads(result)
        assert data["success"] is False
        assert "Database error" in data["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invalid_actions(self, mock_context):
        """Test invalid action handling."""
        # Register tools and get function
        mcp = FastMCP()
        register_project_tools(mcp)
        manage_project = None
        for tool_name, tool_func in mcp._tools.items():
            if 'manage_project' in tool_name:
                manage_project = tool_func
                break
        
        # Test invalid action
        result = await manage_project(
            mock_context,
            action="invalid_action"
        )
        
        data = json.loads(result)
        assert data["success"] is False
        assert "Invalid action" in data["error"]