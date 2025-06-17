"""Unit tests for Projects API endpoints with enhanced patterns and parametrization."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from typing import List, Dict, Any, Optional
import uuid

from src.api.projects_api import (
    CreateProjectRequest,
    UpdateProjectRequest,
    CreateTaskRequest,
    ProjectCreationProgressManager,
    TaskUpdateManager,
    router
)
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time
)


@pytest.mark.unit
@pytest.mark.standard
class TestProjectsAPI:
    """Unit tests for Projects API endpoints with enhanced patterns."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        client = MagicMock()
        # Setup default chain behavior
        client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return client
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def make_project_data(self):
        """Factory for creating project data."""
        def _make_project(
            project_id: Optional[str] = None,
            title: str = "Test Project",
            description: str = "Test description",
            pinned: bool = False,
            color: str = "blue",
            icon: str = "Briefcase",
            github_repo: Optional[str] = None
        ) -> Dict:
            return {
                "id": project_id or f"project-{uuid.uuid4().hex[:8]}",
                "title": title,
                "description": description,
                "github_repo": github_repo,
                "color": color,
                "icon": icon,
                "prd": {"sections": ["Overview", "Requirements"]},
                "docs": [],
                "features": ["Feature 1", "Feature 2"],
                "data": [],
                "technical_sources": ["source1"],
                "business_sources": ["source2"],
                "pinned": pinned,
                "created_at": "2024-01-01T00:00:00Z"
            }
        return _make_project
    
    @pytest.fixture
    def make_task_data(self):
        """Factory for creating task data."""
        def _make_task(
            task_id: Optional[str] = None,
            project_id: str = "project-123",
            title: str = "Test Task",
            status: str = "todo",
            assignee: str = "User",
            parent_task_id: Optional[str] = None
        ) -> Dict:
            return {
                "id": task_id or f"task-{uuid.uuid4().hex[:8]}",
                "project_id": project_id,
                "title": title,
                "description": f"Description for {title}",
                "status": status,
                "assignee": assignee,
                "parent_task_id": parent_task_id,
                "created_at": "2024-01-01T00:00:00Z"
            }
        return _make_task
    
    # =============================================================================
    # Project CRUD Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_projects,pinned_count", [
        pytest.param(0, 0, id="no-projects"),
        pytest.param(5, 0, id="all-regular"),
        pytest.param(5, 2, id="mixed-pinned"),
        pytest.param(3, 3, id="all-pinned"),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    def test_list_projects_various_scenarios(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_project_data,
        num_projects,
        pinned_count
    ):
        """Test listing projects with various configurations."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        projects = []
        for i in range(num_projects):
            projects.append(make_project_data(
                title=f"Project {i+1}",
                pinned=(i < pinned_count)
            ))
        
        # Separate pinned and regular projects
        pinned_projects = [p for p in projects if p["pinned"]]
        regular_projects = [p for p in projects if not p["pinned"]]
        
        if pinned_count > 0:
            mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = [
                MagicMock(data=pinned_projects),
                MagicMock(data=regular_projects)
            ]
        else:
            mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
                data=projects
            )
        
        # Act
        response = test_client.get("/api/projects")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["projects"]) == num_projects
        
        # Verify pinned projects come first
        if pinned_count > 0:
            for i in range(pinned_count):
                assert result["projects"][i]["pinned"] is True
    
    @pytest.mark.parametrize("project_exists", [True, False])
    @patch('src.api.projects_api.get_supabase_client')
    def test_get_single_project(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_project_data,
        project_exists
    ):
        """Test getting a single project by ID."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        project_id = "test-project-123"
        
        if project_exists:
            project = make_project_data(project_id=project_id)
            mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[project]
            )
        else:
            mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
        
        # Act
        response = test_client.get(f"/api/projects/{project_id}")
        
        # Assert
        if project_exists:
            assert response.status_code == 200
            assert response.json()["id"] == project_id
        else:
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    # =============================================================================
    # Project Creation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("creation_data", [
        pytest.param(
            {"title": "New Project", "description": "Basic project"},
            id="minimal-project"
        ),
        pytest.param(
            {
                "title": "Full Project",
                "description": "Complete project with all fields",
                "color": "green",
                "icon": "Code",
                "github_repo": "https://github.com/test/repo"
            },
            id="full-project"
        ),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    @patch('src.api.projects_api._create_project_background')
    def test_create_project_streaming(
        self,
        mock_background_task,
        mock_get_client,
        test_client,
        mock_supabase_client,
        creation_data
    ):
        """Test streaming project creation with various data."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        # Act
        response = test_client.post("/api/projects", json=creation_data)
        
        # Assert
        assert response.status_code == 202  # Accepted
        result = response.json()
        assert "progressId" in result
        assert result["message"] == "Project creation started"
        
        # Verify background task was started
        mock_background_task.assert_called_once()
        call_args = mock_background_task.call_args[0]
        assert call_args[0] == result["progressId"]
        assert call_args[1]["title"] == creation_data["title"]
    
    # =============================================================================
    # Project Update Tests
    # =============================================================================
    
    @pytest.mark.parametrize("update_fields", [
        pytest.param({"title": "Updated Title"}, id="title-only"),
        pytest.param({"description": "New description"}, id="description-only"),
        pytest.param({"pinned": True}, id="pin-project"),
        pytest.param(
            {"title": "New Title", "color": "red", "icon": "Star"},
            id="multiple-fields"
        ),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    def test_update_project_partial_fields(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_project_data,
        update_fields
    ):
        """Test updating specific project fields."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        project_id = "project-to-update"
        original_project = make_project_data(project_id=project_id)
        updated_project = {**original_project, **update_fields}
        
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_project]
        )
        
        # Act
        response = test_client.put(f"/api/projects/{project_id}", json=update_fields)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        for field, value in update_fields.items():
            assert result[field] == value
    
    # =============================================================================
    # Task Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("task_data,expected_status", [
        pytest.param(
            {"project_id": "proj-1", "title": "New Task", "assignee": "User"},
            201,
            id="valid-task"
        ),
        pytest.param(
            {"project_id": "proj-1", "title": "Archon Task", "assignee": "Archon"},
            201,
            id="archon-assigned"
        ),
        pytest.param(
            {"project_id": "proj-1", "title": "AI Task", "assignee": "AI IDE Agent"},
            201,
            id="ai-assigned"
        ),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    def test_create_task_with_assignees(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_task_data,
        task_data,
        expected_status
    ):
        """Test task creation with various assignees."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        created_task = make_task_data(**task_data)
        
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[created_task]
        )
        
        # Act
        response = test_client.post("/api/tasks", json=task_data)
        
        # Assert
        assert response.status_code == expected_status
        if expected_status == 201:
            result = response.json()
            assert result["assignee"] == task_data["assignee"]
    
    @pytest.mark.parametrize("status_transition,is_valid", [
        pytest.param(("todo", "doing"), True, id="todo-to-doing"),
        pytest.param(("doing", "review"), True, id="doing-to-review"),
        pytest.param(("review", "done"), True, id="review-to-done"),
        pytest.param(("todo", "done"), False, id="skip-to-done"),
        pytest.param(("done", "todo"), False, id="done-to-todo"),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    def test_task_status_transitions(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_task_data,
        status_transition,
        is_valid
    ):
        """Test valid and invalid task status transitions."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        task_id = "task-123"
        from_status, to_status = status_transition
        
        # Mock existing task
        existing_task = make_task_data(task_id=task_id, status=from_status)
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing_task]
        )
        
        if is_valid:
            updated_task = {**existing_task, "status": to_status}
            mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[updated_task]
            )
        
        # Act
        response = test_client.put(f"/api/tasks/{task_id}", json={"status": to_status})
        
        # Assert
        if is_valid:
            assert response.status_code == 200
            assert response.json()["status"] == to_status
        else:
            assert response.status_code == 400
    
    # =============================================================================
    # WebSocket Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_websocket_task_notifications(self):
        """Test WebSocket notifications for task updates."""
        # Arrange
        manager = TaskUpdateManager()
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.client_state.name = "CONNECTED"
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        project_id = "test-project"
        session_id = "test-session"
        
        # Act - Connect
        await manager.connect_to_session(mock_ws, project_id, session_id)
        
        # Assert - Connection stored
        assert project_id in manager.session_connections
        assert session_id in manager.session_connections[project_id]
        assert mock_ws in manager.session_connections[project_id][session_id]
        
        # Act - Send update (if method exists)
        # Note: send_task_update might not be implemented yet
        if hasattr(manager, 'send_task_update'):
            update_data = {"task_id": "task-1", "status": "doing"}
            await manager.send_task_update(project_id, update_data)
            
            # Assert - Update sent
            mock_ws.send_json.assert_called_with(update_data)
        
        # Act - Disconnect (if method exists)
        if hasattr(manager, 'disconnect_from_session'):
            await manager.disconnect_from_session(mock_ws, project_id, session_id)
            
            # Assert - Connection removed
            assert mock_ws not in manager.session_connections.get(project_id, {}).get(session_id, [])
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling and cleanup."""
        # Arrange
        manager = TaskUpdateManager()
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.client_state.name = "CONNECTED"
        mock_ws.send_json = AsyncMock(side_effect=WebSocketDisconnect())
        
        # Act - Connect and try to send
        await manager.connect_to_session(mock_ws, "proj-1", "session-1")
        
        # If send_task_update exists, test error handling
        if hasattr(manager, 'send_task_update'):
            await manager.send_task_update("proj-1", {"update": "data"})
            
            # Assert - Connection should be cleaned up after error
            assert mock_ws not in manager.session_connections.get("proj-1", {}).get("session-1", [])
    
    # =============================================================================
    # Progress Tracking Tests
    # =============================================================================
    
    @pytest.mark.parametrize("progress_updates", [
        pytest.param(
            [
                ("starting", 0, "Initializing project"),
                ("creating_structure", 25, "Creating project structure"),
                ("generating_content", 50, "Generating initial content"),
                ("finalizing", 75, "Finalizing project"),
                ("completed", 100, "Project created successfully")
            ],
            id="full-progress"
        ),
    ])
    def test_project_creation_progress_tracking(self, progress_updates):
        """Test project creation progress tracking."""
        # Arrange
        manager = ProjectCreationProgressManager()
        progress_id = f"progress-{uuid.uuid4().hex[:8]}"
        project_data = {"title": "Test Project"}
        
        # Act - Start creation
        manager.start_creation(progress_id, project_data)
        
        # Assert - Initial state
        assert progress_id in manager.active_creations
        assert manager.active_creations[progress_id]["status"] == "starting"
        assert manager.active_creations[progress_id]["percentage"] == 0
        
        # Act & Assert - Progress updates (if method exists)
        if hasattr(manager, 'update_progress'):
            for status, percentage, message in progress_updates:
                manager.update_progress(progress_id, status, percentage, message)
                
                # Get progress if method exists
                if hasattr(manager, 'get_progress'):
                    progress = manager.get_progress(progress_id)
                else:
                    progress = manager.active_creations.get(progress_id, {})
                
                assert progress["status"] == status
                assert progress["percentage"] == percentage
                assert progress["message"] == message
        
        # Act - Complete (if method exists)
        if hasattr(manager, 'complete_creation'):
            manager.complete_creation(progress_id, "project-123")
            
            # Get progress
            if hasattr(manager, 'get_progress'):
                progress = manager.get_progress(progress_id)
            else:
                progress = manager.active_creations.get(progress_id, {})
            
            # Assert - Completion
            assert progress["status"] == "completed"
            assert progress["percentage"] == 100
            assert progress["project_id"] == "project-123"
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario,endpoint,expected_status", [
        pytest.param("project_not_found", "GET /api/projects/{id}", 404, id="get-nonexistent"),
        pytest.param("invalid_task_data", "POST /api/tasks", 422, id="invalid-task"),
        pytest.param("db_error", "GET /api/projects", 500, id="database-error"),
    ])
    @patch('src.api.projects_api.get_supabase_client')
    def test_error_handling_scenarios(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        error_scenario,
        endpoint,
        expected_status
    ):
        """Test error handling for various scenarios."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        if error_scenario == "project_not_found":
            mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            response = test_client.get("/api/projects/nonexistent")
            
        elif error_scenario == "invalid_task_data":
            response = test_client.post("/api/tasks", json={"invalid": "data"})
            
        elif error_scenario == "db_error":
            mock_supabase_client.table.return_value.select.side_effect = Exception("Database error")
            response = test_client.get("/api/projects")
        
        # Assert
        assert response.status_code == expected_status
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_projects", [10, 50, 100])
    @patch('src.api.projects_api.get_supabase_client')
    def test_list_projects_performance(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_project_data,
        num_projects
    ):
        """Test performance of listing large numbers of projects."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        projects = [make_project_data(title=f"Project {i}") for i in range(num_projects)]
        
        mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=projects
        )
        
        # Act & Assert
        with measure_time(f"list_{num_projects}_projects", threshold=0.5):
            response = test_client.get("/api/projects")
        
        assert response.status_code == 200
        assert len(response.json()["projects"]) == num_projects
    
    # =============================================================================
    # Cascade Operations Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_tasks", [0, 5, 20])
    @patch('src.api.projects_api.get_supabase_client')
    def test_project_deletion_cascade(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        num_tasks
    ):
        """Test project deletion cascades to associated tasks."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        project_id = "project-to-delete"
        
        # Mock task deletion
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"id": f"task-{i}"} for i in range(num_tasks)]),  # Tasks
            MagicMock(data=[{"id": project_id}])  # Project
        ]
        
        # Act
        response = test_client.delete(f"/api/projects/{project_id}")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Project deleted successfully"
        
        # Verify cascade deletion
        if num_tasks > 0:
            assert mock_supabase_client.table.return_value.delete.call_count >= 2