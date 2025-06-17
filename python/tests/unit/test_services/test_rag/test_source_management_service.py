"""Unit tests for SourceManagementService."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from src.services.rag.source_management_service import SourceManagementService


class TestSourceManagementService:
    """Unit tests for SourceManagementService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def source_management_service(self, mock_supabase_client):
        """Create SourceManagementService instance with mocked dependencies."""
        return SourceManagementService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_sources(self):
        """Sample source data."""
        return [
            {
                "source_id": "docs.python.org",
                "title": "Python Documentation",
                "description": "Official Python documentation",
                "knowledge_type": "technical",
                "tags": ["python", "documentation", "programming"],
                "word_count": 50000,
                "created_at": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T00:00:00Z"
            },
            {
                "source_id": "blog.example.com",
                "title": "Example Blog",
                "description": "A technical blog about web development",
                "knowledge_type": "business",
                "tags": ["blog", "web", "tutorials"],
                "word_count": 15000,
                "created_at": "2024-01-02T00:00:00Z",
                "last_updated": "2024-01-10T00:00:00Z"
            }
        ]
    
    @pytest.mark.unit
    def test_source_management_lists_knowledge_sources(self, source_management_service, 
                                                      mock_supabase_client, sample_sources):
        """Test listing all available knowledge sources."""
        # Arrange
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=sample_sources
        )
        
        # Act
        success, result = source_management_service.get_available_sources()
        
        # Assert
        assert success is True
        assert len(result["sources"]) == 2
        assert result["total_count"] == 2
        assert result["sources"][0]["source_id"] == "docs.python.org"
        assert result["sources"][1]["source_id"] == "blog.example.com"
        mock_supabase_client.table.assert_called_with("sources")
    
    @pytest.mark.unit
    def test_source_management_deletes_sources(self, source_management_service, mock_supabase_client):
        """Test deleting a source and all associated data."""
        # Arrange
        source_id = "test-source"
        
        # Mock successful deletions
        mock_delete_response = MagicMock(data=[{"id": "deleted"}])
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_delete_response
        
        # Act
        success, result = source_management_service.delete_source(source_id)
        
        # Assert
        assert success is True
        assert result["source_id"] == source_id
        assert result["pages_deleted"] == 1
        assert result["code_examples_deleted"] == 1
        assert result["source_records_deleted"] == 1
        
        # Verify deletion order (pages -> code_examples -> sources)
        table_calls = [call[0][0] for call in mock_supabase_client.table.call_args_list]
        assert table_calls == ["crawled_pages", "code_examples", "sources"]
    
    @pytest.mark.unit
    def test_source_management_manages_source_metadata(self, source_management_service, mock_supabase_client):
        """Test updating source metadata."""
        # Arrange
        source_id = "test-source"
        new_title = "Updated Title"
        new_description = "Updated description"
        new_tags = ["updated", "tags"]
        
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"source_id": source_id}]
        )
        
        # Act
        success, result = source_management_service.update_source_metadata(
            source_id=source_id,
            title=new_title,
            description=new_description,
            tags=new_tags
        )
        
        # Assert
        assert success is True
        assert result["source_id"] == source_id
        assert "title" in result["updated_fields"]
        assert "description" in result["updated_fields"]
        assert "tags" in result["updated_fields"]
        
        # Verify update data
        update_call = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert update_call["title"] == new_title
        assert update_call["description"] == new_description
        assert update_call["tags"] == new_tags
    
    @pytest.mark.unit
    def test_source_management_provides_source_statistics(self, source_management_service, mock_supabase_client):
        """Test getting detailed source statistics."""
        # Arrange
        source_id = "test-source"
        source_data = {
            "source_id": source_id,
            "title": "Test Source",
            "word_count": 10000
        }
        
        # Mock responses
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[source_data]),  # Source data
            MagicMock(data=[{"id": 1}, {"id": 2}, {"id": 3}]),  # 3 pages
            MagicMock(data=[{"id": 1}, {"id": 2}])  # 2 code examples
        ]
        
        # Act
        success, result = source_management_service.get_source_details(source_id)
        
        # Assert
        assert success is True
        assert result["source"]["source_id"] == source_id
        assert result["page_count"] == 3
        assert result["code_example_count"] == 2
    
    @pytest.mark.unit
    def test_source_management_filters_by_type(self, source_management_service, 
                                              mock_supabase_client, sample_sources):
        """Test filtering sources by knowledge type."""
        # Arrange
        technical_sources = [s for s in sample_sources if s["knowledge_type"] == "technical"]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=technical_sources
        )
        
        # Act
        success, result = source_management_service.list_sources_by_type("technical")
        
        # Assert
        assert success is True
        assert len(result["sources"]) == 1
        assert result["sources"][0]["knowledge_type"] == "technical"
        assert result["knowledge_type_filter"] == "technical"
        
        # Verify filter was applied
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_with(
            "knowledge_type", "technical"
        )
    
    @pytest.mark.unit
    def test_source_management_handles_sync_operations(self, source_management_service):
        """Test that source management operations are synchronous."""
        # Note: All SourceManagementService methods are synchronous
        # This test documents this design decision
        
        # Verify methods are not async
        assert not asyncio.iscoroutinefunction(source_management_service.get_available_sources)
        assert not asyncio.iscoroutinefunction(source_management_service.delete_source)
        assert not asyncio.iscoroutinefunction(source_management_service.update_source_metadata)
    
    @pytest.mark.unit
    @patch('src.services.rag.source_management_service.extract_source_summary')
    @patch('src.services.rag.source_management_service.update_source_info')
    def test_create_source_info(self, mock_update_info, mock_extract_summary, 
                               source_management_service):
        """Test creating source information entry."""
        # Arrange
        source_id = "new-source"
        content_sample = "This is sample content for the source"
        mock_extract_summary.return_value = "Extracted summary"
        
        # Act
        success, result = source_management_service.create_source_info(
            source_id=source_id,
            content_sample=content_sample,
            word_count=1000,
            knowledge_type="technical",
            tags=["test", "sample"]
        )
        
        # Assert
        assert success is True
        assert result["source_id"] == source_id
        assert result["description"] == "Extracted summary"
        assert result["word_count"] == 1000
        assert result["knowledge_type"] == "technical"
        assert result["tags"] == ["test", "sample"]
        
        # Verify functions were called
        mock_extract_summary.assert_called_once_with(source_id, content_sample)
        mock_update_info.assert_called_once()
    
    @pytest.mark.unit
    def test_update_source_metadata_no_data(self, source_management_service):
        """Test updating source metadata with no data provided."""
        # Act
        success, result = source_management_service.update_source_metadata("test-source")
        
        # Assert
        assert success is False
        assert result["error"] == "No update data provided"
    
    @pytest.mark.unit
    def test_get_source_details_not_found(self, source_management_service, mock_supabase_client):
        """Test getting details for non-existent source."""
        # Arrange
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Act
        success, result = source_management_service.get_source_details("non-existent")
        
        # Assert
        assert success is False
        assert "not found" in result["error"]
    
    @pytest.mark.unit
    def test_error_handling_in_delete_source(self, source_management_service, mock_supabase_client):
        """Test error handling during source deletion."""
        # Arrange - Make crawled_pages deletion fail
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception(
            "Database error"
        )
        
        # Act
        success, result = source_management_service.delete_source("test-source")
        
        # Assert
        assert success is False
        assert "Failed to delete crawled pages" in result["error"]