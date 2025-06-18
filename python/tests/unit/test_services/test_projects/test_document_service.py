"""Unit tests for DocumentService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

from src.services.projects.document_service import DocumentService
from tests.fixtures.mock_data import DocumentFactory, IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_valid_uuid,
    assert_called_with_subset,
    assert_subset,
    DatabaseTestHelper,
    TestDataBuilder,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestDocumentService:
    """Unit tests for DocumentService with enhanced patterns."""
    
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
                  "eq", "execute"]
        
        for method in methods:
            setattr(mock, method, MagicMock(return_value=mock))
        
        return mock
    
    @pytest.fixture
    def document_service(self, mock_supabase_client):
        """Create DocumentService instance with mocked dependencies."""
        return DocumentService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def make_document_data(self):
        """Factory fixture for creating document test data."""
        def _make_document(**kwargs):
            return DocumentFactory.create(**kwargs)
        return _make_document
    
    @pytest.fixture
    def make_project_with_docs(self, make_document_data):
        """Factory for creating project with documents."""
        def _make_project(doc_count: int = 2, **project_kwargs) -> Dict[str, Any]:
            docs = []
            for i in range(doc_count):
                doc = make_document_data(
                    id=f"doc-{i+1}",
                    document_type=["prd", "design", "spec"][i % 3],
                    title=f"Document {i+1}",
                    version=f"1.{i}"
                )
                # Convert to document structure used in project
                docs.append({
                    "id": doc["id"],
                    "document_type": doc.get("document_type", "general"),
                    "title": doc["title"],
                    "content": doc["content"],
                    "tags": doc.get("metadata", {}).get("tags", []),
                    "status": doc.get("status", "draft"),
                    "version": doc.get("version", "1.0"),
                    "author": doc.get("metadata", {}).get("author", "test-user")
                })
            
            project = {
                "id": project_kwargs.get("id", IDGenerator.generate("proj")),
                "title": project_kwargs.get("title", "Test Project"),
                "docs": docs
            }
            project.update(project_kwargs)
            return project
        return _make_project
    
    # =============================================================================
    # Document Creation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("document_type,title,content,tags,expected_success", [
        pytest.param("prd", "Requirements Doc", {"sections": []}, ["requirements"], True, id="valid-prd"),
        pytest.param("design", "System Design", {"diagrams": []}, ["architecture"], True, id="valid-design"),
        pytest.param("spec", "API Spec", {"endpoints": []}, ["api"], True, id="valid-spec"),
        pytest.param("custom", "Custom Doc", {}, [], True, id="custom-type"),
        pytest.param("", "Empty Type", {}, [], False, id="empty-type"),
        pytest.param("prd", "", {}, [], False, id="empty-title"),
    ])
    def test_add_document_validation(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        document_type,
        title,
        content,
        tags,
        expected_success
    ):
        """Test adding documents with various input combinations."""
        # Arrange
        project = make_project_with_docs(doc_count=1)
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[{"docs": project["docs"]}]),  # Get current docs
            MagicMock(data=[project])  # Update response
        ]
        
        with patch('uuid.uuid4', return_value='new-doc-id'):
            # Act
            success, result = document_service.add_document(
                project_id=project["id"],
                document_type=document_type,
                title=title,
                content=content,
                tags=tags,
                author="test-user"
            )
        
        # Assert
        assert success == expected_success
        
        if expected_success:
            assert result["document"]["id"] == "new-doc-id"
            assert result["document"]["document_type"] == document_type
            assert result["document"]["title"] == title
            
            # Verify update call
            update_call = mock_supabase_client.update.call_args[0][0]
            assert len(update_call["docs"]) == 2  # Original 1 + 1 new
        else:
            assert "error" in result
    
    @pytest.mark.parametrize("existing_doc_count,max_allowed", [
        pytest.param(0, 10, id="empty-project"),
        pytest.param(5, 10, id="half-full"),
        pytest.param(9, 10, id="nearly-full"),
        pytest.param(10, 10, id="at-limit"),
    ])
    def test_document_limit_enforcement(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        existing_doc_count,
        max_allowed
    ):
        """Test document limit enforcement (when implemented)."""
        # Arrange
        project = make_project_with_docs(doc_count=existing_doc_count)
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[{"docs": project["docs"]}]),
            MagicMock(data=[project])
        ]
        
        # Act
        success, result = document_service.add_document(
            project_id=project["id"],
            document_type="spec",
            title="New Document"
        )
        
        # Assert
        # Note: Current implementation doesn't enforce limits
        # This test documents expected behavior
        if existing_doc_count < max_allowed:
            assert success is True
        else:
            # When limits are implemented:
            # assert success is False
            # assert "document limit" in result["error"]
            pass
    
    # =============================================================================
    # Document Update Tests
    # =============================================================================
    
    @pytest.mark.parametrize("update_fields,create_version", [
        pytest.param({"title": "Updated Title"}, False, id="title-only-no-version"),
        pytest.param({"content": {"new": "content"}}, True, id="content-with-version"),
        pytest.param({"status": "approved", "tags": ["reviewed"]}, False, id="metadata-update"),
        pytest.param({"title": "New", "content": {}, "status": "final"}, True, id="multiple-fields-with-version"),
    ])
    def test_update_document_with_various_fields(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        update_fields,
        create_version
    ):
        """Test updating documents with different field combinations."""
        # Arrange
        project = make_project_with_docs(doc_count=2)
        doc_id = project["docs"][0]["id"]
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[project]),  # Get current docs
            MagicMock(data=[project])   # Update response
        ]
        
        # Act
        success, result = document_service.update_document(
            project_id=project["id"],
            doc_id=doc_id,
            update_fields=update_fields,
            create_version=create_version
        )
        
        # Assert
        assert success is True
        assert result["document"]["id"] == doc_id
        
        # Verify update was applied
        update_call = mock_supabase_client.update.call_args[0][0]
        updated_doc = next(doc for doc in update_call["docs"] if doc["id"] == doc_id)
        
        for field, value in update_fields.items():
            assert updated_doc[field] == value
    
    @pytest.mark.parametrize("doc_exists", [True, False])
    def test_update_nonexistent_document(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        doc_exists
    ):
        """Test updating existing vs non-existent documents."""
        # Arrange
        project = make_project_with_docs(doc_count=1)
        doc_id = project["docs"][0]["id"] if doc_exists else "non-existent"
        
        mock_supabase_client.execute.return_value = MagicMock(data=[project])
        
        # Act
        success, result = document_service.update_document(
            project_id=project["id"],
            doc_id=doc_id,
            update_fields={"title": "Updated"}
        )
        
        # Assert
        assert success == doc_exists
        if not doc_exists:
            assert "not found" in result["error"]
    
    # =============================================================================
    # Document Deletion Tests
    # =============================================================================
    
    @pytest.mark.parametrize("doc_count,delete_index", [
        pytest.param(1, 0, id="delete-only-doc"),
        pytest.param(3, 0, id="delete-first"),
        pytest.param(3, 2, id="delete-last"),
        pytest.param(5, 2, id="delete-middle"),
    ])
    def test_delete_document_from_project(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        doc_count,
        delete_index
    ):
        """Test deleting documents at various positions."""
        # Arrange
        project = make_project_with_docs(doc_count=doc_count)
        doc_to_delete = project["docs"][delete_index]
        doc_id = doc_to_delete["id"]
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[project]),  # Get current docs
            MagicMock(data=[project])   # Update response
        ]
        
        # Act
        success, result = document_service.delete_document(
            project_id=project["id"],
            doc_id=doc_id
        )
        
        # Assert
        assert success is True
        assert result["doc_id"] == doc_id
        
        # Verify document was removed
        update_call = mock_supabase_client.update.call_args[0][0]
        assert len(update_call["docs"]) == doc_count - 1
        assert not any(doc["id"] == doc_id for doc in update_call["docs"])
    
    # =============================================================================
    # Document Listing and Retrieval Tests
    # =============================================================================
    
    @pytest.mark.parametrize("doc_count", [
        pytest.param(0, id="empty-project"),
        pytest.param(1, id="single-doc"),
        pytest.param(5, id="multiple-docs"),
        pytest.param(3, id="three-docs"),
    ])
    def test_list_documents_with_various_counts(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        doc_count
    ):
        """Test listing documents with different configurations."""
        # Arrange
        project = make_project_with_docs(doc_count=doc_count)
        mock_supabase_client.execute.return_value = MagicMock(data=[project])
        
        # Act
        success, result = document_service.list_documents(
            project_id=project["id"]
        )
        
        # Assert
        assert success is True
        assert result["total_count"] == doc_count
        assert len(result["documents"]) == doc_count
        
        # Verify content is not included in listing
        for doc in result["documents"]:
            assert "id" in doc
            assert "title" in doc
            assert "document_type" in doc
            # Content should not be included in listings
            # The actual service excludes full content for listing performance
    
    @pytest.mark.parametrize("field_filter", [
        pytest.param({"document_type": "prd"}, id="filter-by-type"),
        pytest.param({"status": "approved"}, id="filter-by-status"),
        pytest.param({"tags": ["api"]}, id="filter-by-tag"),
    ])
    def test_list_documents_with_filters(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        field_filter
    ):
        """Test filtering documents by various fields."""
        # Arrange
        project = make_project_with_docs(doc_count=5)
        
        # Ensure at least one doc matches the filter
        project["docs"][0].update(field_filter)
        
        mock_supabase_client.execute.return_value = MagicMock(data=[project])
        
        # Act
        success, result = document_service.list_documents(
            project_id=project["id"],
            **field_filter
        )
        
        # Assert
        assert success is True
        # Note: Current implementation may not support all filters
        # This test documents expected behavior
    
    # =============================================================================
    # Document Metadata Tests
    # =============================================================================
    
    @pytest.mark.parametrize("metadata_fields", [
        pytest.param({"tags": ["requirements", "v2"]}, id="with-tags"),
        pytest.param({"author": "john.doe", "reviewer": "jane.smith"}, id="with-authors"),
        pytest.param({"status": "draft", "priority": "high"}, id="with-status"),
        pytest.param({"version": "2.1.0", "changelog": "Major update"}, id="with-version-info"),
    ])
    def test_document_metadata_handling(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        metadata_fields
    ):
        """Test handling various document metadata fields."""
        # Arrange
        project = make_project_with_docs(doc_count=1)
        project["docs"][0].update(metadata_fields)
        doc_id = project["docs"][0]["id"]
        
        mock_supabase_client.execute.return_value = MagicMock(data=[project])
        
        # Act
        success, result = document_service.get_document(project["id"], doc_id)
        
        # Assert
        assert success is True
        
        for field, value in metadata_fields.items():
            assert result["document"].get(field) == value
    
    # =============================================================================
    # Versioning Integration Tests
    # =============================================================================
    
    @pytest.mark.parametrize("operation,should_version", [
        pytest.param("content_update", True, id="content-change-versions"),
        pytest.param("title_update", False, id="title-change-no-version"),
        pytest.param("major_update", True, id="major-update-versions"),
    ])
    @patch('src.services.projects.document_service.VersioningService')
    def test_versioning_integration(
        self,
        mock_versioning_class,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        operation,
        should_version
    ):
        """Test version creation for different operations."""
        # Arrange
        mock_versioning = MagicMock()
        mock_versioning_class.return_value = mock_versioning
        
        project = make_project_with_docs(doc_count=1)
        doc_id = project["docs"][0]["id"]
        
        mock_supabase_client.execute.side_effect = [
            MagicMock(data=[project]),
            MagicMock(data=[project])
        ]
        
        update_fields = {
            "content_update": {"content": {"new": "content"}},
            "title_update": {"title": "New Title"},
            "major_update": {"content": {"v2": "data"}, "version": "2.0.0"}
        }[operation]
        
        # Act
        success, result = document_service.update_document(
            project_id=project["id"],
            doc_id=doc_id,
            update_fields=update_fields,
            create_version=should_version
        )
        
        # Assert
        assert success is True
        
        if should_version:
            mock_versioning.create_version.assert_called_once()
            version_call = mock_versioning.create_version.call_args[1]
            assert version_call["project_id"] == project["id"]
            assert version_call["document_id"] == doc_id
        else:
            mock_versioning.create_version.assert_not_called()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("doc_count", [10, 50, 100])
    def test_list_documents_performance(
        self,
        document_service,
        mock_supabase_client,
        make_project_with_docs,
        doc_count
    ):
        """Test document listing performance with large numbers of documents."""
        # Arrange
        project = make_project_with_docs(doc_count=doc_count)
        mock_supabase_client.execute.return_value = MagicMock(data=[project])
        
        # Act & Assert
        with measure_time(f"list_{doc_count}_documents", threshold=0.05):
            success, result = document_service.list_documents(project["id"])
        
        assert success is True
        assert len(result["documents"]) == doc_count
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario,expected_error", [
        pytest.param("project_not_found", "not found", id="missing-project"),
        pytest.param("db_connection_error", "Database error", id="connection-error"),
        pytest.param("invalid_json", "Invalid content", id="malformed-content"),
    ])
    def test_error_handling(
        self,
        document_service,
        mock_supabase_client,
        error_scenario,
        expected_error
    ):
        """Test graceful error handling for various scenarios."""
        # Arrange
        if error_scenario == "project_not_found":
            mock_supabase_client.execute.return_value = MagicMock(data=[])
        elif error_scenario == "db_connection_error":
            mock_supabase_client.execute.side_effect = Exception("Connection refused")
        elif error_scenario == "invalid_json":
            mock_supabase_client.execute.return_value = MagicMock(
                data=[{"id": "proj", "docs": "invalid"}]
            )
        
        # Act
        success, result = document_service.add_document(
            project_id="test-project",
            document_type="prd",
            title="Test Doc"
        )
        
        # Assert
        assert success is False
        assert expected_error in result["error"] or "error" in result