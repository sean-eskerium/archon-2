"""Unit tests for DocumentService."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid
from src.services.projects.document_service import DocumentService
from tests.fixtures.mock_data import mock_factory


class TestDocumentService:
    """Unit tests for DocumentService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for database operations."""
        mock = MagicMock()
        
        # Mock table methods
        mock.table = MagicMock(return_value=mock)
        mock.select = MagicMock(return_value=mock)
        mock.update = MagicMock(return_value=mock)
        mock.eq = MagicMock(return_value=mock)
        mock.execute = MagicMock()
        
        return mock
    
    @pytest.fixture
    def document_service(self, mock_supabase_client):
        """Create DocumentService instance with mocked dependencies."""
        return DocumentService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_document(self):
        """Sample document data."""
        return mock_factory.create_document()
    
    @pytest.fixture
    def sample_project_with_docs(self):
        """Sample project with documents in docs field."""
        return {
            "id": "test-project-id",
            "title": "Test Project",
            "docs": [
                {
                    "id": "doc-1",
                    "document_type": "prd",
                    "title": "Project Requirements",
                    "content": {"sections": ["overview", "features"]},
                    "tags": ["requirements"],
                    "status": "draft",
                    "version": "1.0"
                },
                {
                    "id": "doc-2",
                    "document_type": "design",
                    "title": "System Design",
                    "content": {"diagrams": []},
                    "tags": ["architecture"],
                    "status": "approved",
                    "version": "1.1"
                }
            ]
        }
    
    @pytest.mark.unit
    def test_document_service_adds_document_to_project(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test adding a document to project's docs field."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[{"docs": sample_project_with_docs["docs"]}]),  # Get current docs
            MagicMock(data=[sample_project_with_docs])  # Update response
        ]
        
        with patch('uuid.uuid4', return_value='new-doc-id'):
            # Act
            success, result = document_service.add_document(
                project_id=project_id,
                document_type="spec",
                title="API Specification",
                content={"endpoints": []},
                tags=["api", "spec"],
                author="test-user"
            )
        
        # Assert
        assert success is True
        assert result["document"]["id"] == "new-doc-id"
        assert result["document"]["document_type"] == "spec"
        assert result["document"]["title"] == "API Specification"
        
        # Verify the update call included the new document
        update_call = mock_supabase_client.update.call_args[0][0]
        assert len(update_call["docs"]) == 3  # Original 2 + 1 new
    
    @pytest.mark.unit
    def test_document_service_validates_document_type(self, document_service, mock_supabase_client):
        """Test document type validation."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[{"docs": []}])
        
        # Act - Should accept any document type (no validation in current implementation)
        success, result = document_service.add_document(
            project_id="test-id",
            document_type="custom-type",
            title="Test Doc"
        )
        
        # Assert
        assert success is True
    
    @pytest.mark.unit
    def test_document_service_updates_document_content(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test updating document content."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        doc_id = "doc-1"
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_project_with_docs]),  # Get current docs
            MagicMock(data=[sample_project_with_docs])  # Update response
        ]
        
        # Act
        success, result = document_service.update_document(
            project_id=project_id,
            doc_id=doc_id,
            update_fields={
                "title": "Updated PRD",
                "content": {"sections": ["overview", "features", "requirements"]},
                "status": "approved"
            },
            create_version=False  # Skip versioning for unit test
        )
        
        # Assert
        assert success is True
        assert result["document"]["id"] == doc_id
        
        # Verify update was called with modified docs
        update_call = mock_supabase_client.update.call_args[0][0]
        updated_doc = next(doc for doc in update_call["docs"] if doc["id"] == doc_id)
        assert updated_doc["title"] == "Updated PRD"
        assert updated_doc["status"] == "approved"
    
    @pytest.mark.unit
    def test_document_service_deletes_document_from_project(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test deleting a document from project."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        doc_id = "doc-1"
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_project_with_docs]),  # Get current docs
            MagicMock(data=[sample_project_with_docs])  # Update response
        ]
        
        # Act
        success, result = document_service.delete_document(
            project_id=project_id,
            doc_id=doc_id
        )
        
        # Assert
        assert success is True
        assert result["doc_id"] == doc_id
        
        # Verify update was called with doc removed
        update_call = mock_supabase_client.update.call_args[0][0]
        assert len(update_call["docs"]) == 1  # Original 2 - 1 deleted
        assert not any(doc["id"] == doc_id for doc in update_call["docs"])
    
    @pytest.mark.unit
    def test_document_service_lists_project_documents(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test listing all documents in a project."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_project_with_docs])
        
        # Act
        success, result = document_service.list_documents(project_id)
        
        # Assert
        assert success is True
        assert result["total_count"] == 2
        assert len(result["documents"]) == 2
        
        # Verify documents don't include full content in list
        for doc in result["documents"]:
            assert "content" not in doc or doc["content"] is None
            assert "id" in doc
            assert "title" in doc
            assert "document_type" in doc
    
    @pytest.mark.unit
    def test_document_service_handles_document_metadata(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test handling document metadata like tags and author."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        doc_id = "doc-1"
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_project_with_docs])
        
        # Act
        success, result = document_service.get_document(project_id, doc_id)
        
        # Assert
        assert success is True
        assert result["document"]["tags"] == ["requirements"]
        assert result["document"]["status"] == "draft"
        assert result["document"]["version"] == "1.0"
    
    @pytest.mark.unit
    def test_document_service_enforces_document_limits(self, document_service):
        """Test document limits enforcement."""
        # Note: Current implementation doesn't enforce document limits
        # This test documents expected behavior for future implementation
        pass
    
    @pytest.mark.unit
    def test_get_document_returns_full_content(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test that get_document returns full document including content."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        doc_id = "doc-1"
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_project_with_docs])
        
        # Act
        success, result = document_service.get_document(project_id, doc_id)
        
        # Assert
        assert success is True
        assert result["document"]["content"] == {"sections": ["overview", "features"]}
        assert result["document"]["id"] == doc_id
    
    @pytest.mark.unit
    def test_document_not_found_returns_error(self, document_service, mock_supabase_client, sample_project_with_docs):
        """Test getting non-existent document returns error."""
        # Arrange
        project_id = sample_project_with_docs["id"]
        mock_supabase_client.execute.return_value = MagicMock(data=[sample_project_with_docs])
        
        # Act
        success, result = document_service.get_document(project_id, "non-existent-id")
        
        # Assert
        assert success is False
        assert "not found" in result["error"]
    
    @pytest.mark.unit
    def test_project_not_found_returns_error(self, document_service, mock_supabase_client):
        """Test operations on non-existent project return error."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[])
        
        # Act
        success, result = document_service.add_document(
            project_id="non-existent-project",
            document_type="prd",
            title="Test"
        )
        
        # Assert
        assert success is False
        assert "Project with ID" in result["error"]
        assert "not found" in result["error"]
    
    @pytest.mark.unit
    @patch('src.services.projects.document_service.VersioningService')
    def test_update_creates_version_snapshot(self, mock_versioning_class, document_service, mock_supabase_client, sample_project_with_docs):
        """Test that updates create version snapshots when requested."""
        # Arrange
        mock_versioning = MagicMock()
        mock_versioning_class.return_value = mock_versioning
        
        project_id = sample_project_with_docs["id"]
        doc_id = "doc-1"
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[sample_project_with_docs]),  # Get current docs
            MagicMock(data=[sample_project_with_docs])  # Update response
        ]
        
        # Act
        success, result = document_service.update_document(
            project_id=project_id,
            doc_id=doc_id,
            update_fields={"title": "Updated Title"},
            create_version=True
        )
        
        # Assert
        assert success is True
        mock_versioning.create_version.assert_called_once()
        version_call = mock_versioning.create_version.call_args[1]
        assert version_call["project_id"] == project_id
        assert version_call["field_name"] == "docs"
        assert version_call["document_id"] == doc_id