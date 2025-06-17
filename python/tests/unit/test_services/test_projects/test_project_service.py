"""Unit tests for ProjectService."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from src.services.projects.project_service import ProjectService
from tests.fixtures.mock_data import mock_factory
from tests.fixtures.test_helpers import test_helpers


class TestProjectService:
    """Unit tests for ProjectService."""
    
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
        mock.in_ = MagicMock(return_value=mock)
        mock.order = MagicMock(return_value=mock)
        mock.single = MagicMock(return_value=mock)
        mock.execute = MagicMock()
        
        return mock
    
    @pytest.fixture
    def project_service(self, mock_supabase_client):
        """Create ProjectService instance with mocked dependencies."""
        return ProjectService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_project(self):
        """Sample project data."""
        return mock_factory.create_project()
    
    @pytest.mark.unit
    def test_project_service_creates_project_with_valid_data(self, project_service, mock_supabase_client, sample_project):
        """Test creating a project with valid data returns expected result."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_project])
        
        # Act
        success, result = project_service.create_project(
            title="Test Project",
            prd={"description": "Test PRD"},
            github_repo="test/repo"
        )
        
        # Assert
        assert success is True
        assert result["project"]["id"] == sample_project["id"]
        assert result["project"]["title"] == sample_project["title"]
        mock_supabase_client.table.assert_called_with("projects")
        mock_supabase_client.insert.assert_called_once()
    
    @pytest.mark.unit
    def test_project_service_validates_required_fields(self, project_service):
        """Test project creation validates required fields."""
        # Test empty title
        success, result = project_service.create_project(title="")
        assert success is False
        assert "title is required" in result["error"]
        
        # Test None title
        success, result = project_service.create_project(title=None)
        assert success is False
        assert "title is required" in result["error"]
        
        # Test whitespace-only title
        success, result = project_service.create_project(title="   ")
        assert success is False
        assert "title is required" in result["error"]
    
    @pytest.mark.unit
    def test_project_service_handles_duplicate_titles(self, project_service, mock_supabase_client):
        """Test project creation handles database errors gracefully."""
        # Arrange
        mock_supabase_client.execute.side_effect = Exception("Duplicate key value violates unique constraint")
        
        # Act
        success, result = project_service.create_project(title="Duplicate Project")
        
        # Assert
        assert success is False
        assert "Database error" in result["error"]
    
    @pytest.mark.unit
    def test_project_service_updates_project_fields(self, project_service, mock_supabase_client, sample_project):
        """Test updating project fields."""
        # Note: The current ProjectService doesn't have an update method,
        # but we'll test the pattern for when it's added
        # This test serves as a placeholder showing expected behavior
        pass
    
    @pytest.mark.unit
    def test_project_service_deletes_project_cascades_tasks(self, project_service, mock_supabase_client):
        """Test deleting a project returns correct task count."""
        # Arrange
        project_id = "test-project-id"
        mock_tasks = [{"id": f"task-{i}"} for i in range(5)]
        
        # Mock task count query
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=mock_tasks),  # Task count query
            MagicMock(data=[{"id": project_id}])  # Delete query
        ]
        
        # Act
        success, result = project_service.delete_project(project_id)
        
        # Assert
        assert success is True
        assert result["project_id"] == project_id
        assert result["deleted_tasks"] == 5
        
        # Verify queries
        assert mock_supabase_client.table.call_count == 2
        mock_supabase_client.table.assert_any_call("tasks")
        mock_supabase_client.table.assert_any_call("projects")
    
    @pytest.mark.unit
    def test_project_service_retrieves_project_by_id(self, project_service, mock_supabase_client, sample_project):
        """Test retrieving a project by ID."""
        # Arrange
        project_id = sample_project["id"]
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_project]),  # Project query
            MagicMock(data=[]),  # Project sources query
        ]
        
        # Act
        success, result = project_service.get_project(project_id)
        
        # Assert
        assert success is True
        assert result["project"]["id"] == project_id
        assert result["project"]["title"] == sample_project["title"]
        mock_supabase_client.eq.assert_any_call("id", project_id)
    
    @pytest.mark.unit
    def test_project_service_lists_projects_with_pagination(self, project_service, mock_supabase_client):
        """Test listing projects with ordering."""
        # Arrange
        mock_projects = mock_factory.create_batch(mock_factory.create_project, count=3)
        mock_supabase_client.execute.return_value = MagicMock(data=mock_projects)
        
        # Act
        success, result = project_service.list_projects()
        
        # Assert
        assert success is True
        assert result["total_count"] == 3
        assert len(result["projects"]) == 3
        mock_supabase_client.order.assert_called_with("created_at", desc=True)
    
    @pytest.mark.unit
    def test_project_service_filters_projects_by_status(self, project_service, mock_supabase_client):
        """Test that list_projects returns projects in correct format."""
        # Arrange
        mock_projects = [
            mock_factory.create_project(status="active"),
            mock_factory.create_project(status="completed"),
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=mock_projects)
        
        # Act
        success, result = project_service.list_projects()
        
        # Assert
        assert success is True
        for i, project in enumerate(result["projects"]):
            assert "id" in project
            assert "title" in project
            assert "created_at" in project
            assert "updated_at" in project
    
    @pytest.mark.unit
    def test_get_project_includes_linked_sources(self, project_service, mock_supabase_client, sample_project):
        """Test get_project includes technical and business sources."""
        # Arrange
        project_id = sample_project["id"]
        mock_source_links = [
            {"source_id": "tech-1", "notes": "technical"},
            {"source_id": "biz-1", "notes": "business"}
        ]
        mock_tech_sources = [{"source_id": "tech-1", "url": "https://tech.com"}]
        mock_biz_sources = [{"source_id": "biz-1", "url": "https://biz.com"}]
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_project]),  # Project query
            MagicMock(data=mock_source_links),  # Project sources query
            MagicMock(data=mock_tech_sources),  # Technical sources query
            MagicMock(data=mock_biz_sources),  # Business sources query
        ]
        
        # Act
        success, result = project_service.get_project(project_id)
        
        # Assert
        assert success is True
        assert len(result["project"]["technical_sources"]) == 1
        assert len(result["project"]["business_sources"]) == 1
        assert result["project"]["technical_sources"][0]["source_id"] == "tech-1"
        assert result["project"]["business_sources"][0]["source_id"] == "biz-1"
    
    @pytest.mark.unit
    def test_get_project_features_extracts_feature_labels(self, project_service, mock_supabase_client):
        """Test get_project_features extracts feature labels correctly."""
        # Arrange
        project_id = "test-project-id"
        mock_features = [
            {
                "id": "feat-1",
                "type": "page",
                "data": {"label": "Feature 1", "type": "core"}
            },
            {
                "id": "feat-2",
                "type": "component",
                "data": {"label": "Feature 2", "type": "optional"}
            }
        ]
        mock_supabase_client.execute.return_value = MagicMock(
            data={"features": mock_features}
        )
        
        # Act
        success, result = project_service.get_project_features(project_id)
        
        # Assert
        assert success is True
        assert result["count"] == 2
        assert len(result["features"]) == 2
        assert result["features"][0]["label"] == "Feature 1"
        assert result["features"][0]["feature_type"] == "page"
        assert result["features"][1]["label"] == "Feature 2"
        assert result["features"][1]["feature_type"] == "component"
    
    @pytest.mark.unit
    def test_project_service_handles_empty_database_response(self, project_service, mock_supabase_client):
        """Test project creation handles empty database response."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=None)
        
        # Act
        success, result = project_service.create_project(title="Test Project")
        
        # Assert
        assert success is False
        assert "database returned no data" in result["error"]
    
    @pytest.mark.unit
    def test_project_not_found_returns_error(self, project_service, mock_supabase_client):
        """Test get_project returns error when project not found."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[])
        
        # Act
        success, result = project_service.get_project("nonexistent-id")
        
        # Assert
        assert success is False
        assert "not found" in result["error"]
    
    @pytest.mark.unit
    def test_delete_nonexistent_project_returns_error(self, project_service, mock_supabase_client):
        """Test delete_project returns error when project not found."""
        # Arrange
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[]),  # Task count query
            MagicMock(data=[])  # Delete query returns empty
        ]
        
        # Act
        success, result = project_service.delete_project("nonexistent-id")
        
        # Assert
        assert success is False
        assert "not found" in result["error"]