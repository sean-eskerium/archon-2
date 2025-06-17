"""Unit tests for VersioningService."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from src.services.projects.versioning_service import VersioningService


class TestVersioningService:
    """Unit tests for VersioningService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for database operations."""
        mock = MagicMock()
        
        # Mock table methods
        mock.table = MagicMock(return_value=mock)
        mock.select = MagicMock(return_value=mock)
        mock.insert = MagicMock(return_value=mock)
        mock.update = MagicMock(return_value=mock)
        mock.eq = MagicMock(return_value=mock)
        mock.order = MagicMock(return_value=mock)
        mock.limit = MagicMock(return_value=mock)
        mock.execute = MagicMock()
        
        return mock
    
    @pytest.fixture
    def versioning_service(self, mock_supabase_client):
        """Create VersioningService instance with mocked dependencies."""
        return VersioningService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_version_data(self):
        """Sample version data."""
        return {
            "id": "version-1",
            "project_id": "test-project-id",
            "field_name": "docs",
            "version_number": 1,
            "content": {"test": "data", "items": ["item1", "item2"]},
            "change_summary": "Initial version",
            "change_type": "create",
            "document_id": "doc-1",
            "created_by": "test-user",
            "created_at": datetime.now().isoformat()
        }
    
    @pytest.mark.unit
    def test_versioning_creates_snapshot_of_jsonb_field(self, versioning_service, mock_supabase_client):
        """Test creating a version snapshot of a JSONB field."""
        # Arrange
        project_id = "test-project-id"
        field_name = "docs"
        content = {"documents": [{"id": "1", "title": "Doc 1"}]}
        
        # Mock no existing versions
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[]),  # No existing versions
            MagicMock(data=[{
                "version_number": 1,
                "content": content
            }])  # Insert result
        ]
        
        # Act
        success, result = versioning_service.create_version(
            project_id=project_id,
            field_name=field_name,
            content=content,
            change_summary="Added new document",
            change_type="update"
        )
        
        # Assert
        assert success is True
        assert result["version_number"] == 1
        assert result["field_name"] == field_name
        mock_supabase_client.insert.assert_called_once()
        insert_data = mock_supabase_client.insert.call_args[0][0]
        assert insert_data["content"] == content
        assert insert_data["version_number"] == 1
    
    @pytest.mark.unit
    def test_versioning_tracks_change_history(self, versioning_service, mock_supabase_client):
        """Test tracking version history with incremental version numbers."""
        # Arrange
        project_id = "test-project-id"
        field_name = "features"
        
        # Mock existing version
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[{"version_number": 3}]),  # Existing highest version
            MagicMock(data=[{"version_number": 4}])   # Insert result
        ]
        
        # Act
        success, result = versioning_service.create_version(
            project_id=project_id,
            field_name=field_name,
            content={"features": ["f1", "f2", "f3"]},
            change_type="update"
        )
        
        # Assert
        assert success is True
        assert result["version_number"] == 4
        insert_data = mock_supabase_client.insert.call_args[0][0]
        assert insert_data["version_number"] == 4
    
    @pytest.mark.unit
    def test_versioning_restores_previous_version(self, versioning_service, mock_supabase_client, sample_version_data):
        """Test restoring a field to a previous version."""
        # Arrange
        project_id = sample_version_data["project_id"]
        field_name = sample_version_data["field_name"]
        version_number = 2
        
        # Mock responses
        mock_supabase_client.execute.side_effect = [
            # Get version to restore
            MagicMock(data=[{
                "version_number": version_number,
                "content": {"restored": "content"}
            }]),
            # Get current content
            MagicMock(data=[{field_name: {"current": "content"}}]),
            # Create backup version - no existing versions
            MagicMock(data=[]),
            # Insert backup version
            MagicMock(data=[{"version_number": 3}]),
            # Update project
            MagicMock(data=[{"id": project_id}]),
            # Create restore version - get existing versions
            MagicMock(data=[{"version_number": 3}]),
            # Insert restore version
            MagicMock(data=[{"version_number": 4}])
        ]
        
        # Act
        success, result = versioning_service.restore_version(
            project_id=project_id,
            field_name=field_name,
            version_number=version_number,
            restored_by="test-user"
        )
        
        # Assert
        assert success is True
        assert result["restored_version"] == version_number
        assert result["restored_by"] == "test-user"
        
        # Verify project was updated with restored content
        update_call = mock_supabase_client.update.call_args[0][0]
        assert update_call[field_name] == {"restored": "content"}
    
    @pytest.mark.unit
    def test_versioning_lists_version_history(self, versioning_service, mock_supabase_client):
        """Test listing version history for a field."""
        # Arrange
        project_id = "test-project-id"
        field_name = "docs"
        mock_versions = [
            {"version_number": 3, "change_summary": "Latest change"},
            {"version_number": 2, "change_summary": "Middle change"},
            {"version_number": 1, "change_summary": "Initial version"}
        ]
        
        mock_supabase_client.execute.return_value = MagicMock(data=mock_versions)
        
        # Act
        success, result = versioning_service.list_versions(
            project_id=project_id,
            field_name=field_name
        )
        
        # Assert
        assert success is True
        assert result["total_count"] == 3
        assert len(result["versions"]) == 3
        assert result["versions"][0]["version_number"] == 3
        mock_supabase_client.order.assert_called_with("version_number", desc=True)
    
    @pytest.mark.unit
    def test_versioning_limits_version_retention(self, versioning_service):
        """Test version retention limits."""
        # Note: Current implementation doesn't have retention limits
        # This test documents expected behavior for future implementation
        pass
    
    @pytest.mark.unit
    def test_versioning_handles_large_jsonb_data(self, versioning_service, mock_supabase_client):
        """Test handling large JSONB data in versions."""
        # Arrange
        large_content = {
            "data": [{"id": str(i), "content": f"Item {i}" * 100} for i in range(100)]
        }
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[]),  # No existing versions
            MagicMock(data=[{"version_number": 1}])  # Insert result
        ]
        
        # Act
        success, result = versioning_service.create_version(
            project_id="test-project",
            field_name="large_data",
            content=large_content
        )
        
        # Assert
        assert success is True
        insert_data = mock_supabase_client.insert.call_args[0][0]
        assert insert_data["content"] == large_content
    
    @pytest.mark.unit
    def test_versioning_validates_field_names(self, versioning_service, mock_supabase_client):
        """Test field name validation."""
        # Arrange
        valid_field_names = ["docs", "features", "data", "settings"]
        
        for field_name in valid_field_names:
            mock_supabase_client.execute.side_effect = [
                MagicMock(data=[]),
                MagicMock(data=[{"version_number": 1}])
            ]
            
            # Act
            success, result = versioning_service.create_version(
                project_id="test-project",
                field_name=field_name,
                content={"test": "data"}
            )
            
            # Assert
            assert success is True
            assert result["field_name"] == field_name
    
    @pytest.mark.unit
    def test_get_version_content(self, versioning_service, mock_supabase_client, sample_version_data):
        """Test retrieving specific version content."""
        # Arrange
        project_id = sample_version_data["project_id"]
        field_name = sample_version_data["field_name"]
        version_number = sample_version_data["version_number"]
        
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_version_data])
        
        # Act
        success, result = versioning_service.get_version_content(
            project_id=project_id,
            field_name=field_name,
            version_number=version_number
        )
        
        # Assert
        assert success is True
        assert result["content"] == sample_version_data["content"]
        assert result["version_number"] == version_number
        mock_supabase_client.eq.assert_any_call("version_number", version_number)
    
    @pytest.mark.unit
    def test_version_not_found_returns_error(self, versioning_service, mock_supabase_client):
        """Test getting non-existent version returns error."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[])
        
        # Act
        success, result = versioning_service.get_version_content(
            project_id="test-project",
            field_name="docs",
            version_number=999
        )
        
        # Assert
        assert success is False
        assert "not found" in result["error"]
    
    @pytest.mark.unit
    def test_create_version_with_metadata(self, versioning_service, mock_supabase_client):
        """Test creating version with document_id and created_by metadata."""
        # Arrange
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"version_number": 1}])
        ]
        
        # Act
        success, result = versioning_service.create_version(
            project_id="test-project",
            field_name="docs",
            content={"test": "data"},
            change_summary="User updated document",
            change_type="update",
            document_id="doc-123",
            created_by="user@example.com"
        )
        
        # Assert
        assert success is True
        insert_data = mock_supabase_client.insert.call_args[0][0]
        assert insert_data["document_id"] == "doc-123"
        assert insert_data["created_by"] == "user@example.com"
        assert insert_data["change_summary"] == "User updated document"