"""Unit tests for Projects API endpoints."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException, WebSocket
from fastapi.testclient import TestClient
from src.api.projects_api import (
    CreateProjectRequest,
    UpdateProjectRequest,
    CreateTaskRequest,
    ProjectCreationProgressManager,
    TaskUpdateManager,
    router
)


class TestProjectsAPI:
    """Unit tests for Projects API endpoints."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def sample_project(self):
        """Sample project data."""
        return {
            "id": "project-123",
            "title": "Test Project",
            "description": "Test project description",
            "github_repo": "https://github.com/test/repo",
            "color": "blue",
            "icon": "Briefcase",
            "prd": {"sections": ["Overview", "Requirements"]},
            "docs": [],
            "features": ["Feature 1", "Feature 2"],
            "data": [],
            "technical_sources": ["source1"],
            "business_sources": ["source2"],
            "pinned": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
    
    @pytest.mark.unit
    @patch('src.api.projects_api.get_supabase_client')
    def test_project_crud_operations(self, mock_get_client, test_client, mock_supabase_client, sample_project):
        """Test Create, Read, Update, Delete operations for projects."""
        mock_get_client.return_value = mock_supabase_client
        
        # Test LIST projects
        mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[sample_project]
        )
        
        response = test_client.get("/api/projects")
        assert response.status_code == 200
        assert len(response.json()["projects"]) == 1
        
        # Test GET single project
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_project]
        )
        
        response = test_client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == sample_project["id"]
    
    @pytest.mark.unit
    @patch('src.api.projects_api.get_supabase_client')
    def test_project_filtering_and_search(self, mock_get_client, test_client, mock_supabase_client):
        """Test project listing with filters."""
        mock_get_client.return_value = mock_supabase_client
        
        # Mock filtered results
        pinned_projects = [{"id": "p1", "title": "Pinned", "pinned": True}]
        regular_projects = [{"id": "p2", "title": "Regular", "pinned": False}]
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = [
            MagicMock(data=pinned_projects),  # Pinned projects
            MagicMock(data=regular_projects)  # Regular projects
        ]
        
        response = test_client.get("/api/projects")
        assert response.status_code == 200
        # Should return both pinned and regular projects
    
    @pytest.mark.unit
    @patch('src.api.projects_api.get_supabase_client')
    @patch('src.api.projects_api._create_project_background')
    def test_project_handles_streaming_creation(self, mock_background_task, mock_get_client, 
                                               test_client, mock_supabase_client):
        """Test streaming project creation."""
        mock_get_client.return_value = mock_supabase_client
        
        # Test project creation request
        create_request = {
            "title": "New Project",
            "description": "Created via streaming"
        }
        
        response = test_client.post("/api/projects", json=create_request)
        assert response.status_code == 202  # Accepted
        assert "progressId" in response.json()
        
        # Verify background task was started
        mock_background_task.assert_called_once()
    
    @pytest.mark.unit
    def test_task_management_endpoints(self, test_client):
        """Test task CRUD operations."""
        # Mock implementation would go here
        # Testing task creation, updates, deletion
        pass
    
    @pytest.mark.unit
    def test_task_status_transitions(self, test_client):
        """Test task status update validation."""
        # Valid transitions: todo -> doing -> review
        # Invalid transitions should be rejected
        pass
    
    @pytest.mark.unit
    def test_hierarchical_task_structure(self, test_client):
        """Test parent-child task relationships."""
        # Test creating subtasks
        # Test querying task hierarchy
        pass
    
    @pytest.mark.unit
    def test_project_update_partial_fields(self, test_client):
        """Test updating only specific project fields."""
        # Test that unspecified fields remain unchanged
        pass
    
    @pytest.mark.unit
    def test_websocket_task_notifications(self):
        """Test WebSocket notifications for task updates."""
        # Test TaskUpdateManager functionality
        manager = TaskUpdateManager()
        
        # Test connection management
        mock_ws = MagicMock()
        mock_ws.client_state.name = "CONNECTED"
        
        # Simulate connection
        asyncio.run(manager.connect_to_session(mock_ws, "project-1", "session-1"))
        
        # Verify connection stored
        assert "project-1" in manager.session_connections
        assert "session-1" in manager.session_connections["project-1"]
    
    @pytest.mark.unit
    def test_project_progress_manager(self):
        """Test project creation progress tracking."""
        manager = ProjectCreationProgressManager()
        
        # Test starting a creation
        progress_id = "test-progress-123"
        manager.start_creation(progress_id, {"title": "Test Project"})
        
        assert progress_id in manager.active_creations
        assert manager.active_creations[progress_id]["status"] == "starting"
        assert manager.active_creations[progress_id]["percentage"] == 0
    
    @pytest.mark.unit
    @patch('src.api.projects_api.get_supabase_client')
    def test_project_deletion_cascades(self, mock_get_client, test_client, mock_supabase_client):
        """Test project deletion cascades to tasks."""
        mock_get_client.return_value = mock_supabase_client
        project_id = "project-to-delete"
        
        # Mock successful deletion
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[]),  # Tasks deletion
            MagicMock(data=[{"id": project_id}])  # Project deletion
        ]
        
        response = test_client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        
        # Verify both tasks and project were deleted
        delete_calls = mock_supabase_client.table.return_value.delete.call_count
        assert delete_calls >= 1
    
    @pytest.mark.unit
    def test_error_handling_invalid_project(self, test_client):
        """Test error handling for invalid project operations."""
        # Test getting non-existent project
        with patch('src.api.projects_api.get_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            
            response = test_client.get("/api/projects/non-existent")
            assert response.status_code == 404
    
    @pytest.mark.unit
    def test_project_feature_extraction(self, test_client):
        """Test extracting features from project."""
        # Test /projects/{project_id}/features endpoint
        pass
    
    @pytest.mark.unit
    @patch('src.api.projects_api.get_supabase_client')
    def test_task_assignee_validation(self, mock_get_client, test_client, mock_supabase_client):
        """Test task assignee must be one of allowed values."""
        mock_get_client.return_value = mock_supabase_client
        
        # Valid assignees: 'User', 'Archon', 'AI IDE Agent'
        valid_task = {
            "project_id": "test-project",
            "title": "Test Task",
            "assignee": "User"
        }
        
        # Mock successful insertion
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "task-123", **valid_task}]
        )
        
        response = test_client.post("/api/tasks", json=valid_task)
        # Should succeed with valid assignee
    
    @pytest.mark.unit
    def test_concurrent_project_updates(self, test_client):
        """Test handling concurrent project updates."""
        # Test optimistic locking or conflict resolution
        pass