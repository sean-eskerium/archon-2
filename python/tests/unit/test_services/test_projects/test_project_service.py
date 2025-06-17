"""Unit tests for ProjectService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.projects.project_service import ProjectService
from tests.fixtures.mock_data import ProjectFactory, IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_subset,
    assert_valid_uuid,
    assert_called_with_subset,
    DatabaseTestHelper,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestProjectService:
    """Unit tests for ProjectService with enhanced patterns."""
    
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
                  "eq", "in_", "order", "single", "execute"]
        
        for method in methods:
            setattr(mock, method, MagicMock(return_value=mock))
        
        return mock
    
    @pytest.fixture
    def project_service(self, mock_supabase_client):
        """Create ProjectService instance with mocked dependencies."""
        return ProjectService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def make_project_data(self):
        """Factory fixture for creating project test data."""
        def _make_project(**kwargs):
            return ProjectFactory.create(**kwargs)
        return _make_project
    
    # =============================================================================
    # Project Creation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("title,prd,github_repo,expected_success", [
        pytest.param("Valid Project", {"description": "Test"}, "org/repo", True, id="valid-all-fields"),
        pytest.param("Minimal Project", None, None, True, id="valid-minimal"),
        pytest.param("", None, None, False, id="invalid-empty-title"),
        pytest.param(None, None, None, False, id="invalid-none-title"),
        pytest.param("   ", None, None, False, id="invalid-whitespace-title"),
    ])
    def test_create_project_validation(
        self, 
        project_service, 
        mock_supabase_client,
        make_project_data,
        title, 
        prd, 
        github_repo, 
        expected_success
    ):
        """Test project creation with various input combinations."""
        # Arrange
        if expected_success:
            mock_project = make_project_data(title=title)
            mock_supabase_client.execute.return_value = MagicMock(data=[mock_project])
        
        # Act
        success, result = project_service.create_project(
            title=title,
            prd=prd,
            github_repo=github_repo
        )
        
        # Assert
        assert success == expected_success
        
        if expected_success:
            assert_valid_uuid(result["project"]["id"])
            assert result["project"]["title"] == title
            assert_called_with_subset(mock_supabase_client.insert, title=title)
        else:
            assert "error" in result
            if not title or (isinstance(title, str) and not title.strip()):
                assert "title is required" in result["error"]
    
    @pytest.mark.parametrize("exception,expected_error", [
        pytest.param(
            Exception("Duplicate key value violates unique constraint"),
            "Duplicate key",
            id="duplicate-title"
        ),
        pytest.param(
            Exception("Connection timeout"),
            "Connection timeout",
            id="connection-error"
        ),
        pytest.param(
            Exception("Unknown database error"),
            "Database error",
            id="generic-error"
        ),
    ])
    def test_create_project_handles_database_errors(
        self,
        project_service,
        mock_supabase_client,
        exception,
        expected_error
    ):
        """Test project creation handles various database errors gracefully."""
        # Arrange
        mock_supabase_client.execute.side_effect = exception
        
        # Act
        success, result = project_service.create_project(title="Test Project")
        
        # Assert
        assert success is False
        assert expected_error in result["error"]
        assert mock_supabase_client.table.called
    
    def test_create_project_handles_empty_response(
        self,
        project_service,
        mock_supabase_client
    ):
        """Test project creation handles empty database response."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=None)
        
        # Act
        success, result = project_service.create_project(title="Test Project")
        
        # Assert
        assert success is False
        assert "database returned no data" in result["error"]
    
    # =============================================================================
    # Project Retrieval Tests
    # =============================================================================
    
    @pytest.mark.parametrize("project_exists", [True, False])
    def test_get_project_by_id(
        self,
        project_service,
        mock_supabase_client,
        make_project_data,
        db_helper,
        project_exists
    ):
        """Test retrieving a project by ID with parametrized existence."""
        # Arrange
        project_id = IDGenerator.generate("proj")
        
        if project_exists:
            mock_project = make_project_data(id=project_id)
            mock_supabase_client.execute.side_effect = [
                db_helper.create_mock_query_result([mock_project]),  # Project query
                db_helper.create_mock_query_result([]),  # Project sources query
            ]
        else:
            mock_supabase_client.execute.return_value = db_helper.create_mock_query_result([])
        
        # Act
        success, result = project_service.get_project(project_id)
        
        # Assert
        assert success == project_exists
        
        if project_exists:
            assert result["project"]["id"] == project_id
            assert_called_with_subset(mock_supabase_client.eq, id=project_id)
        else:
            assert "not found" in result["error"]
    
    @pytest.mark.parametrize("tech_sources,biz_sources", [
        pytest.param(0, 0, id="no-sources"),
        pytest.param(2, 0, id="tech-only"),
        pytest.param(0, 3, id="biz-only"),
        pytest.param(2, 2, id="mixed-sources"),
    ])
    def test_get_project_with_linked_sources(
        self,
        project_service,
        mock_supabase_client,
        make_project_data,
        db_helper,
        tech_sources,
        biz_sources
    ):
        """Test get_project includes correct number of linked sources."""
        # Arrange
        project = make_project_data()
        project_id = project["id"]
        
        # Create source links
        source_links = []
        tech_source_data = []
        biz_source_data = []
        
        for i in range(tech_sources):
            source_id = f"tech-{i}"
            source_links.append({"source_id": source_id, "notes": "technical"})
            tech_source_data.append({"source_id": source_id, "url": f"https://tech{i}.com"})
        
        for i in range(biz_sources):
            source_id = f"biz-{i}"
            source_links.append({"source_id": source_id, "notes": "business"})
            biz_source_data.append({"source_id": source_id, "url": f"https://biz{i}.com"})
        
        mock_supabase_client.execute.side_effect = [
            db_helper.create_mock_query_result([project]),  # Project query
            db_helper.create_mock_query_result(source_links),  # Project sources query
            db_helper.create_mock_query_result(tech_source_data),  # Technical sources
            db_helper.create_mock_query_result(biz_source_data),  # Business sources
        ]
        
        # Act
        success, result = project_service.get_project(project_id)
        
        # Assert
        assert success is True
        assert len(result["project"]["technical_sources"]) == tech_sources
        assert len(result["project"]["business_sources"]) == biz_sources
    
    # =============================================================================
    # Project Listing Tests
    # =============================================================================
    
    @pytest.mark.parametrize("project_count", [0, 1, 5, 10])
    def test_list_projects_pagination(
        self,
        project_service,
        mock_supabase_client,
        make_project_data,
        db_helper,
        project_count
    ):
        """Test listing projects with different counts."""
        # Arrange
        projects = [make_project_data() for _ in range(project_count)]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(projects)
        
        # Act
        success, result = project_service.list_projects()
        
        # Assert
        assert success is True
        assert result["total_count"] == project_count
        assert len(result["projects"]) == project_count
        
        # Verify ordering was applied
        assert_called_with_subset(mock_supabase_client.order, "created_at", desc=True)
    
    @pytest.mark.parametrize("fields", [
        ["id", "title", "created_at", "updated_at"],
        ["id", "title", "status", "created_at", "updated_at", "metadata"],
    ])
    def test_list_projects_returns_required_fields(
        self,
        project_service,
        mock_supabase_client,
        make_project_data,
        db_helper,
        fields
    ):
        """Test that list_projects returns all required fields."""
        # Arrange
        projects = [make_project_data() for _ in range(2)]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(projects)
        
        # Act
        success, result = project_service.list_projects()
        
        # Assert
        assert success is True
        for project in result["projects"]:
            for field in fields[:4]:  # First 4 fields are always required
                assert field in project, f"Missing required field: {field}"
    
    # =============================================================================
    # Project Deletion Tests
    # =============================================================================
    
    @pytest.mark.parametrize("task_count,project_exists", [
        pytest.param(0, True, id="no-tasks"),
        pytest.param(5, True, id="with-tasks"),
        pytest.param(0, False, id="project-not-found"),
    ])
    def test_delete_project_with_cascading_tasks(
        self,
        project_service,
        mock_supabase_client,
        db_helper,
        task_count,
        project_exists
    ):
        """Test deleting a project with various task configurations."""
        # Arrange
        project_id = IDGenerator.generate("proj")
        mock_tasks = [{"id": f"task-{i}"} for i in range(task_count)]
        
        if project_exists:
            mock_supabase_client.execute.side_effect = [
                db_helper.create_mock_query_result(mock_tasks),  # Task count query
                db_helper.create_mock_query_result([{"id": project_id}])  # Delete query
            ]
        else:
            mock_supabase_client.execute.side_effect = [
                db_helper.create_mock_query_result([]),  # Task count query
                db_helper.create_mock_query_result([])  # Delete returns empty
            ]
        
        # Act
        success, result = project_service.delete_project(project_id)
        
        # Assert
        assert success == project_exists
        
        if project_exists:
            assert result["project_id"] == project_id
            assert result["deleted_tasks"] == task_count
        else:
            assert "not found" in result["error"]
    
    # =============================================================================
    # Feature Extraction Tests
    # =============================================================================
    
    @pytest.mark.parametrize("features_data", [
        pytest.param([], id="no-features"),
        pytest.param([
            {"id": "f1", "type": "page", "data": {"label": "Home", "type": "core"}},
        ], id="single-feature"),
        pytest.param([
            {"id": "f1", "type": "page", "data": {"label": "Home", "type": "core"}},
            {"id": "f2", "type": "component", "data": {"label": "Header", "type": "optional"}},
            {"id": "f3", "type": "api", "data": {"label": "Auth API", "type": "required"}},
        ], id="multiple-features"),
        pytest.param([
            {"id": "f1", "type": "unknown", "data": {}},  # Missing label
        ], id="malformed-feature"),
    ])
    def test_get_project_features_extraction(
        self,
        project_service,
        mock_supabase_client,
        db_helper,
        features_data
    ):
        """Test feature extraction with various data structures."""
        # Arrange
        project_id = IDGenerator.generate("proj")
        mock_supabase_client.execute.return_value = MagicMock(
            data={"features": features_data}
        )
        
        # Act
        success, result = project_service.get_project_features(project_id)
        
        # Assert
        assert success is True
        
        # Count valid features (those with labels)
        valid_features = [f for f in features_data if f.get("data", {}).get("label")]
        assert result["count"] == len(valid_features)
        assert len(result["features"]) == len(valid_features)
        
        # Verify feature structure
        for i, feature in enumerate(result["features"]):
            if i < len(valid_features):
                assert "label" in feature
                assert "feature_type" in feature
                assert feature["feature_type"] == valid_features[i]["type"]
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("record_count", [100, 500, 1000])
    def test_list_projects_performance_with_large_datasets(
        self,
        project_service,
        mock_supabase_client,
        make_project_data,
        db_helper,
        record_count
    ):
        """Test list_projects performance with large datasets."""
        # Arrange
        projects = [make_project_data() for _ in range(record_count)]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(projects)
        
        # Act & Assert
        with measure_time(f"list_projects with {record_count} records", threshold=0.1):
            success, result = project_service.list_projects()
        
        assert success is True
        assert result["total_count"] == record_count