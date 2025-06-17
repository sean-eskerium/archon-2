"""Unit tests for TaskService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.services.projects.task_service import TaskService
from tests.fixtures.mock_data import TaskFactory, IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_valid_uuid,
    assert_called_with_subset,
    DatabaseTestHelper,
    wait_for_condition,
    async_timeout
)


@pytest.mark.unit
@pytest.mark.critical
class TestTaskService:
    """Unit tests for TaskService with enhanced patterns."""
    
    @pytest.fixture(scope="class")
    def db_helper(self):
        """Database test helper for creating mock results."""
        return DatabaseTestHelper()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client with chained method support."""
        mock = MagicMock()
        
        # Setup chainable methods
        methods = ["table", "select", "insert", "update", "delete", 
                  "eq", "neq", "or_", "in_", "order", "execute"]
        
        for method in methods:
            setattr(mock, method, MagicMock(return_value=mock))
        
        return mock
    
    @pytest.fixture
    def task_service(self, mock_supabase_client):
        """Create TaskService instance with mocked dependencies."""
        return TaskService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def make_task_data(self):
        """Factory fixture for creating task test data."""
        def _make_task(**kwargs):
            return TaskFactory.create(**kwargs)
        return _make_task
    
    @pytest.fixture
    def mock_task_update_manager(self):
        """Mock task update manager for WebSocket broadcasting."""
        manager = AsyncMock()
        manager.broadcast_task_update = AsyncMock()
        return manager
    
    # =============================================================================
    # Task Creation Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("title,project_id,assignee,expected_success", [
        pytest.param("Valid Task", "proj_123", "Archon", True, id="valid-all-fields"),
        pytest.param("Minimal Task", "proj_123", None, True, id="valid-minimal"),
        pytest.param("", "proj_123", None, False, id="invalid-empty-title"),
        pytest.param("Valid Task", "", None, False, id="invalid-empty-project"),
        pytest.param("Valid Task", "proj_123", "InvalidUser", False, id="invalid-assignee"),
    ])
    async def test_create_task_validation(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        title,
        project_id,
        assignee,
        expected_success
    ):
        """Test task creation with various input combinations."""
        # Arrange
        if expected_success:
            mock_task = make_task_data(title=title, project_id=project_id, assignee=assignee)
            mock_supabase_client.execute.return_value = MagicMock(data=[mock_task])
        
        # Act
        success, result = await task_service.create_task(
            project_id=project_id,
            title=title,
            assignee=assignee
        )
        
        # Assert
        assert success == expected_success
        
        if expected_success:
            assert_valid_uuid(result["task"]["id"])
            assert result["task"]["title"] == title
            if assignee:
                assert result["task"]["assignee"] == assignee
        else:
            assert "error" in result
            if not title:
                assert "title is required" in result["error"]
            elif not project_id:
                assert "Project ID is required" in result["error"]
            elif assignee == "InvalidUser":
                assert "Invalid assignee" in result["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("parent_task_id,expected_parent", [
        pytest.param(None, None, id="no-parent"),
        pytest.param("task_parent_123", "task_parent_123", id="with-parent"),
    ])
    async def test_create_subtask_hierarchy(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        parent_task_id,
        expected_parent
    ):
        """Test creating tasks with parent-child relationships."""
        # Arrange
        task_data = make_task_data(parent_task_id=parent_task_id)
        mock_supabase_client.execute.return_value = MagicMock(data=[task_data])
        
        # Act
        success, result = await task_service.create_task(
            project_id="proj_123",
            title="Subtask",
            parent_task_id=parent_task_id
        )
        
        # Assert
        assert success is True
        assert result["task"]["parent_task_id"] == expected_parent
        if parent_task_id:
            assert_called_with_subset(mock_supabase_client.insert, parent_task_id=parent_task_id)
    
    # =============================================================================
    # Task Status Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("status,is_valid", [
        pytest.param("todo", True, id="valid-todo"),
        pytest.param("doing", True, id="valid-doing"),
        pytest.param("review", True, id="valid-review"),
        pytest.param("done", True, id="valid-done"),
        pytest.param("invalid", False, id="invalid-status"),
        pytest.param("", False, id="empty-status"),
        pytest.param(None, False, id="none-status"),
    ])
    def test_validate_task_status(self, task_service, status, is_valid):
        """Test task status validation with various inputs."""
        # Act
        valid, error = task_service.validate_status(status)
        
        # Assert
        assert valid == is_valid
        if not is_valid:
            assert "Invalid status" in error
        else:
            assert error == ""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("initial_status,new_status,allowed", [
        pytest.param("todo", "doing", True, id="todo-to-doing"),
        pytest.param("doing", "review", True, id="doing-to-review"),
        pytest.param("review", "done", True, id="review-to-done"),
        pytest.param("done", "todo", True, id="done-to-todo-allowed"),
        pytest.param("todo", "done", True, id="skip-to-done-allowed"),
    ])
    async def test_update_task_status_transitions(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        initial_status,
        new_status,
        allowed
    ):
        """Test task status transitions."""
        # Arrange
        task = make_task_data(status=initial_status)
        task_id = task["id"]
        updated_task = {**task, "status": new_status}
        mock_supabase_client.execute.return_value = MagicMock(data=[updated_task])
        
        # Act
        success, result = await task_service.update_task(
            task_id=task_id,
            update_fields={"status": new_status}
        )
        
        # Assert
        assert success == allowed
        if allowed:
            assert result["task"]["status"] == new_status
            assert_called_with_subset(mock_supabase_client.update, status=new_status)
    
    # =============================================================================
    # Task Assignment Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("assignee", [
        pytest.param("User", id="assign-to-user"),
        pytest.param("Archon", id="assign-to-archon"),
        pytest.param("AI IDE Agent", id="assign-to-ai-agent"),
        pytest.param(None, id="unassign"),
    ])
    async def test_assign_task_to_valid_assignees(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        assignee
    ):
        """Test assigning tasks to various valid assignees."""
        # Arrange
        task = make_task_data()
        task_id = task["id"]
        updated_task = {**task, "assignee": assignee}
        mock_supabase_client.execute.return_value = MagicMock(data=[updated_task])
        
        # Act
        success, result = await task_service.update_task(
            task_id=task_id,
            update_fields={"assignee": assignee}
        )
        
        # Assert
        assert success is True
        assert result["task"]["assignee"] == assignee
    
    # =============================================================================
    # Task Filtering and Listing Tests
    # =============================================================================
    
    @pytest.mark.parametrize("filters,expected_calls", [
        pytest.param(
            {"status": "todo"},
            [("eq", "status", "todo")],
            id="filter-by-status"
        ),
        pytest.param(
            {"project_id": "proj_123"},
            [("eq", "project_id", "proj_123")],
            id="filter-by-project"
        ),
        pytest.param(
            {"assignee": "Archon"},
            [("eq", "assignee", "Archon")],
            id="filter-by-assignee"
        ),
        pytest.param(
            {"status": "doing", "project_id": "proj_123"},
            [("eq", "status", "doing"), ("eq", "project_id", "proj_123")],
            id="multiple-filters"
        ),
    ])
    def test_list_tasks_with_filters(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        db_helper,
        filters,
        expected_calls
    ):
        """Test listing tasks with various filter combinations."""
        # Arrange
        tasks = [make_task_data(**filters) for _ in range(3)]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(tasks)
        
        # Act
        success, result = task_service.list_tasks(**filters)
        
        # Assert
        assert success is True
        assert len(result["tasks"]) == 3
        
        # Verify filters were applied
        for method, field, value in expected_calls:
            getattr(mock_supabase_client, method).assert_any_call(field, value)
    
    @pytest.mark.parametrize("include_archived,expected_filter", [
        pytest.param(False, "archived.is.null,archived.eq.false", id="exclude-archived"),
        pytest.param(True, None, id="include-archived"),
    ])
    def test_list_tasks_archived_filtering(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        db_helper,
        include_archived,
        expected_filter
    ):
        """Test archived task filtering behavior."""
        # Arrange
        tasks = [
            make_task_data(archived=False),
            make_task_data(archived=True),
            make_task_data(archived=None),
        ]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(
            tasks if include_archived else [t for t in tasks if not t.get("archived")]
        )
        
        # Act
        success, result = task_service.list_tasks(include_archived=include_archived)
        
        # Assert
        assert success is True
        if expected_filter and not include_archived:
            mock_supabase_client.or_.assert_called_with(expected_filter)
    
    # =============================================================================
    # Task Archiving Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("subtask_count", [0, 3, 10])
    async def test_archive_task_with_subtasks(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        db_helper,
        subtask_count
    ):
        """Test archiving tasks with various numbers of subtasks."""
        # Arrange
        task = make_task_data()
        task_id = task["id"]
        subtasks = [make_task_data(parent_task_id=task_id) for _ in range(subtask_count)]
        
        mock_supabase_client.execute.side_effect = [
            db_helper.create_mock_query_result([task]),  # Task exists check
            db_helper.create_mock_query_result(subtasks),  # Subtasks query
            db_helper.create_mock_query_result([{**task, "archived": True}]),  # Archive task
            db_helper.create_mock_query_result(subtasks)  # Archive subtasks
        ]
        
        # Act
        success, result = await task_service.archive_task(task_id)
        
        # Assert
        assert success is True
        assert result["task_id"] == task_id
        assert result["archived_subtasks"] == subtask_count
        
        # Verify archive was set
        assert_called_with_subset(mock_supabase_client.update, archived=True)
    
    # =============================================================================
    # Task Hierarchy Tests
    # =============================================================================
    
    @pytest.mark.parametrize("hierarchy_depth,task_count", [
        pytest.param(1, 5, id="flat-hierarchy"),
        pytest.param(2, 10, id="two-level-hierarchy"),
        pytest.param(3, 15, id="three-level-hierarchy"),
    ])
    def test_list_tasks_maintains_hierarchy(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        db_helper,
        hierarchy_depth,
        task_count
    ):
        """Test that task listing maintains parent-child relationships."""
        # Arrange
        tasks = []
        parent_ids = [None]  # Start with root tasks
        
        for level in range(hierarchy_depth):
            level_tasks = []
            tasks_per_parent = task_count // len(parent_ids)
            
            for parent_id in parent_ids:
                for _ in range(tasks_per_parent):
                    task = make_task_data(parent_task_id=parent_id)
                    level_tasks.append(task)
                    tasks.append(task)
            
            # Next level's parents are this level's tasks
            parent_ids = [t["id"] for t in level_tasks[:3]]  # Limit branching
        
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(tasks)
        
        # Act
        success, result = task_service.list_tasks()
        
        # Assert
        assert success is True
        assert len(result["tasks"]) == len(tasks)
        
        # Verify hierarchy is preserved
        task_by_id = {t["id"]: t for t in result["tasks"]}
        for task in result["tasks"]:
            if task.get("parent_task_id"):
                assert task["parent_task_id"] in task_by_id
    
    # =============================================================================
    # WebSocket Broadcasting Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    @pytest.mark.websocket
    @patch('src.services.projects.task_service.get_task_update_manager')
    async def test_task_operations_broadcast_updates(
        self,
        mock_get_manager,
        task_service,
        mock_supabase_client,
        mock_task_update_manager,
        make_task_data
    ):
        """Test that task operations broadcast WebSocket updates."""
        # Arrange
        mock_get_manager.return_value = mock_task_update_manager
        task = make_task_data()
        mock_supabase_client.execute.return_value = MagicMock(data=[task])
        
        # Act - Create task
        success, result = await task_service.create_task(
            project_id=task["project_id"],
            title="Test Task"
        )
        
        # Assert
        assert success is True
        
        # Verify broadcast was called with timeout
        await async_timeout(
            mock_task_update_manager.broadcast_task_update.assert_called_once(),
            timeout=1.0
        )
        
        call_args = mock_task_update_manager.broadcast_task_update.call_args[1]
        assert call_args["event_type"] == "task_created"
        assert call_args["project_id"] == task["project_id"]
        assert "task" in call_args
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("task_count", [100, 500, 1000])
    def test_list_tasks_performance_with_hierarchy(
        self,
        task_service,
        mock_supabase_client,
        make_task_data,
        db_helper,
        task_count
    ):
        """Test task listing performance with hierarchical data."""
        # Arrange
        tasks = []
        # Create a hierarchy: 20% parent tasks, 80% subtasks
        parent_count = task_count // 5
        
        # Create parent tasks
        parent_tasks = [make_task_data() for _ in range(parent_count)]
        tasks.extend(parent_tasks)
        
        # Create subtasks
        for i in range(task_count - parent_count):
            parent = parent_tasks[i % parent_count]
            subtask = make_task_data(parent_task_id=parent["id"])
            tasks.append(subtask)
        
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(tasks)
        
        # Act & Assert
        import time
        start_time = time.perf_counter()
        
        success, result = task_service.list_tasks()
        
        duration = time.perf_counter() - start_time
        
        assert success is True
        assert len(result["tasks"]) == task_count
        # Performance assertion: should handle 1000 tasks in < 200ms
        assert duration < 0.2, f"Performance degradation: {duration:.3f}s for {task_count} tasks"
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("exception,expected_error", [
        pytest.param(
            Exception("Connection refused"),
            "Database connection error",
            id="connection-error"
        ),
        pytest.param(
            Exception("Timeout"),
            "Operation timed out",
            id="timeout-error"
        ),
    ])
    async def test_task_operations_handle_database_errors(
        self,
        task_service,
        mock_supabase_client,
        exception,
        expected_error
    ):
        """Test graceful handling of database errors."""
        # Arrange
        mock_supabase_client.execute.side_effect = exception
        
        # Act
        success, result = await task_service.create_task(
            project_id="proj_123",
            title="Test Task"
        )
        
        # Assert
        assert success is False
        assert expected_error in result["error"] or "Database error" in result["error"]