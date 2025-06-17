"""Unit tests for TaskService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from src.services.projects.task_service import TaskService
from tests.fixtures.mock_data import mock_factory
from tests.fixtures.test_helpers import test_helpers


class TestTaskService:
    """Unit tests for TaskService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for database operations."""
        mock = MagicMock()
        
        # Mock table methods
        mock.table = MagicMock(return_value=mock)
        mock.select = MagicMock(return_value=mock)
        mock.insert = MagicMock(return_value=mock)
        mock.update = MagicMock(return_value=mock)
        mock.delete = MagicMock(return_value=mock)
        mock.eq = MagicMock(return_value=mock)
        mock.neq = MagicMock(return_value=mock)
        mock.or_ = MagicMock(return_value=mock)
        mock.order = MagicMock(return_value=mock)
        mock.execute = MagicMock()
        
        return mock
    
    @pytest.fixture
    def task_service(self, mock_supabase_client):
        """Create TaskService instance with mocked dependencies."""
        return TaskService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_task(self):
        """Sample task data."""
        return mock_factory.create_task()
    
    @pytest.fixture
    def mock_task_update_manager(self):
        """Mock task update manager for WebSocket broadcasting."""
        manager = AsyncMock()
        manager.broadcast_task_update = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_creates_task_with_project_id(self, task_service, mock_supabase_client, sample_task):
        """Test creating a task with valid project ID."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_task])
        
        # Act
        success, result = await task_service.create_task(
            project_id="test-project-id",
            title="Test Task",
            description="Task description",
            assignee="Archon"
        )
        
        # Assert
        assert success is True
        assert result["task"]["id"] == sample_task["id"]
        assert result["task"]["title"] == sample_task["title"]
        assert result["task"]["assignee"] == sample_task["assignee"]
        mock_supabase_client.table.assert_called_with("tasks")
        mock_supabase_client.insert.assert_called_once()
    
    @pytest.mark.unit
    def test_task_service_validates_task_status_values(self, task_service):
        """Test task status validation."""
        # Valid statuses
        for status in ["todo", "doing", "review", "done"]:
            is_valid, error = task_service.validate_status(status)
            assert is_valid is True
            assert error == ""
        
        # Invalid status
        is_valid, error = task_service.validate_status("invalid")
        assert is_valid is False
        assert "Invalid status" in error
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_creates_subtask_with_parent_id(self, task_service, mock_supabase_client, sample_task):
        """Test creating a subtask with parent ID."""
        # Arrange
        parent_id = "parent-task-id"
        subtask = {**sample_task, "parent_task_id": parent_id}
        mock_supabase_client.execute.return_value = MagicMock(data=[subtask])
        
        # Act
        success, result = await task_service.create_task(
            project_id="test-project-id",
            title="Subtask",
            parent_task_id=parent_id
        )
        
        # Assert
        assert success is True
        assert result["task"]["parent_task_id"] == parent_id
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_updates_task_status(self, task_service, mock_supabase_client, sample_task):
        """Test updating task status."""
        # Arrange
        task_id = sample_task["id"]
        updated_task = {**sample_task, "status": "doing"}
        mock_supabase_client.execute.return_value = MagicMock(data=[updated_task])
        
        # Act
        success, result = await task_service.update_task(
            task_id=task_id,
            update_fields={"status": "doing"}
        )
        
        # Assert
        assert success is True
        assert result["task"]["status"] == "doing"
        assert mock_supabase_client.update.call_args[0][0]["status"] == "doing"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_assigns_task_to_user(self, task_service, mock_supabase_client, sample_task):
        """Test assigning task to valid assignees."""
        # Arrange
        task_id = sample_task["id"]
        
        for assignee in ["User", "Archon", "AI IDE Agent"]:
            updated_task = {**sample_task, "assignee": assignee}
            mock_supabase_client.execute.return_value = MagicMock(data=[updated_task])
            
            # Act
            success, result = await task_service.update_task(
                task_id=task_id,
                update_fields={"assignee": assignee}
            )
            
            # Assert
            assert success is True
            assert result["task"]["assignee"] == assignee
    
    @pytest.mark.unit
    def test_task_service_filters_tasks_by_status(self, task_service, mock_supabase_client):
        """Test filtering tasks by status."""
        # Arrange
        tasks = [
            mock_factory.create_task(status="todo"),
            mock_factory.create_task(status="doing"),
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=[tasks[0]])
        
        # Act
        success, result = task_service.list_tasks(status="todo")
        
        # Assert
        assert success is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "todo"
        mock_supabase_client.eq.assert_any_call("status", "todo")
    
    @pytest.mark.unit
    def test_task_service_filters_tasks_by_project(self, task_service, mock_supabase_client):
        """Test filtering tasks by project ID."""
        # Arrange
        project_id = "test-project-id"
        tasks = mock_factory.create_batch(
            mock_factory.create_task,
            count=3,
            project_id=project_id
        )
        mock_supabase_client.execute.return_value = MagicMock(data=tasks)
        
        # Act
        success, result = task_service.list_tasks(project_id=project_id)
        
        # Assert
        assert success is True
        assert result["total_count"] == 3
        mock_supabase_client.eq.assert_any_call("project_id", project_id)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_archives_completed_tasks(self, task_service, mock_supabase_client, sample_task):
        """Test archiving tasks and subtasks."""
        # Arrange
        task_id = sample_task["id"]
        subtasks = mock_factory.create_batch(
            mock_factory.create_task,
            count=3,
            parent_task_id=task_id
        )
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_task]),  # Task exists check
            MagicMock(data=subtasks),  # Subtasks query
            MagicMock(data=[{**sample_task, "archived": True}]),  # Archive task
            MagicMock(data=subtasks)  # Archive subtasks
        ]
        
        # Act
        success, result = await task_service.archive_task(task_id)
        
        # Assert
        assert success is True
        assert result["task_id"] == task_id
        assert result["archived_subtasks"] == 3
        assert mock_supabase_client.update.call_args[0][0]["archived"] is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_prevents_circular_subtask_references(self, task_service):
        """Test that task service validates against circular references."""
        # Note: Current implementation doesn't have circular reference prevention
        # This test documents expected behavior for future implementation
        pass
    
    @pytest.mark.unit
    def test_task_service_calculates_task_hierarchy(self, task_service, mock_supabase_client):
        """Test listing tasks maintains proper hierarchy with parent_task_id."""
        # Arrange
        parent_task = mock_factory.create_task(id="parent-1")
        child_tasks = [
            mock_factory.create_task(parent_task_id="parent-1"),
            mock_factory.create_task(parent_task_id="parent-1"),
        ]
        all_tasks = [parent_task] + child_tasks
        mock_supabase_client.execute.return_value = MagicMock(data=all_tasks)
        
        # Act
        success, result = task_service.list_tasks()
        
        # Assert
        assert success is True
        assert len(result["tasks"]) == 3
        # Verify parent tasks and child tasks are returned
        parent_count = sum(1 for t in result["tasks"] if t.get("parent_task_id") is None)
        child_count = sum(1 for t in result["tasks"] if t.get("parent_task_id") == "parent-1")
        assert parent_count == 1
        assert child_count == 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_validates_required_fields(self, task_service):
        """Test task creation validates required fields."""
        # Test empty title
        success, result = await task_service.create_task(
            project_id="test-id",
            title=""
        )
        assert success is False
        assert "title is required" in result["error"]
        
        # Test missing project_id
        success, result = await task_service.create_task(
            project_id="",
            title="Test Task"
        )
        assert success is False
        assert "Project ID is required" in result["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_task_service_validates_assignee(self, task_service):
        """Test task assignee validation."""
        # Invalid assignee
        success, result = await task_service.create_task(
            project_id="test-id",
            title="Test Task",
            assignee="InvalidUser"
        )
        assert success is False
        assert "Invalid assignee" in result["error"]
    
    @pytest.mark.unit
    def test_task_service_excludes_archived_tasks(self, task_service, mock_supabase_client):
        """Test that archived tasks are excluded by default."""
        # Arrange
        tasks = [
            mock_factory.create_task(archived=False),
            mock_factory.create_task(archived=None),
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=tasks)
        
        # Act
        success, result = task_service.list_tasks()
        
        # Assert
        assert success is True
        # Verify archived filter is applied
        mock_supabase_client.or_.assert_called_with("archived.is.null,archived.eq.false")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.projects.task_service.get_task_update_manager')
    async def test_task_broadcasts_websocket_updates(self, mock_get_manager, task_service, mock_supabase_client, mock_task_update_manager):
        """Test that task operations broadcast WebSocket updates."""
        # Arrange
        mock_get_manager.return_value = mock_task_update_manager
        sample_task = mock_factory.create_task()
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_task])
        
        # Act
        success, result = await task_service.create_task(
            project_id="test-project-id",
            title="Test Task"
        )
        
        # Assert
        assert success is True
        mock_task_update_manager.broadcast_task_update.assert_called_once()
        call_args = mock_task_update_manager.broadcast_task_update.call_args[1]
        assert call_args["event_type"] == "task_created"
        assert call_args["project_id"] == sample_task["project_id"]