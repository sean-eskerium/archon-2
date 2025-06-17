"""Unit tests for DocumentStorageService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.services.rag.document_storage_service import DocumentStorageService


class TestDocumentStorageService:
    """Unit tests for DocumentStorageService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def document_storage_service(self, mock_supabase_client):
        """Create DocumentStorageService instance with mocked dependencies."""
        return DocumentStorageService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def sample_document_content(self):
        """Sample document content for testing."""
        return """# Test Document

This is a test document with multiple sections.

## Section 1
This section contains some text that should be chunked properly.
It has multiple sentences. Each sentence adds to the content.

## Section 2
```python
def hello_world():
    print("Hello, World!")
    return True
```

This section has code examples that should be preserved.

## Section 3
Final section with more content to ensure proper chunking behavior."""
    
    @pytest.mark.unit
    def test_storage_chunks_large_documents(self, document_storage_service, sample_document_content):
        """Test document chunking for large documents."""
        # Arrange
        chunk_size = 100  # Small chunk size for testing
        
        # Act
        chunks = document_storage_service.smart_chunk_markdown(
            sample_document_content,
            chunk_size=chunk_size
        )
        
        # Assert
        assert len(chunks) > 1  # Should create multiple chunks
        assert all(len(chunk) <= chunk_size * 1.5 for chunk in chunks)  # Allow some overflow
        assert all(chunk.strip() for chunk in chunks)  # No empty chunks
        
        # Verify content preservation
        reconstructed = "\n".join(chunks)
        assert "# Test Document" in reconstructed
        assert "def hello_world():" in reconstructed
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    @patch('src.services.rag.document_storage_service.update_source_info')
    async def test_storage_generates_embeddings(self, mock_update_source, mock_add_docs, 
                                               document_storage_service, sample_document_content):
        """Test that document storage triggers embedding generation."""
        # Arrange
        mock_add_docs.return_value = None
        
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=sample_document_content,
            filename="test.md",
            knowledge_type="technical"
        )
        
        # Assert
        assert success is True
        assert result["chunks_stored"] > 0
        mock_add_docs.assert_called_once()
        
        # Verify embeddings were requested
        call_args = mock_add_docs.call_args[1]
        assert "contents" in call_args
        assert len(call_args["contents"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    async def test_storage_stores_document_metadata(self, mock_add_docs, 
                                                   document_storage_service, sample_document_content):
        """Test metadata storage for documents."""
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=sample_document_content,
            filename="test_doc.md",
            knowledge_type="business",
            tags=["test", "documentation"]
        )
        
        # Assert
        assert success is True
        
        # Check metadata in the call
        call_args = mock_add_docs.call_args[1]
        metadatas = call_args["metadatas"]
        
        assert len(metadatas) > 0
        for metadata in metadatas:
            assert metadata["knowledge_type"] == "business"
            assert metadata["filename"] == "test_doc.md"
            assert metadata["tags"] == ["test", "documentation"]
            assert "word_count" in metadata
            assert "char_count" in metadata
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_storage_handles_duplicate_content(self, document_storage_service, mock_supabase_client):
        """Test handling of duplicate content."""
        # Note: Current implementation doesn't check for duplicates
        # This test documents expected behavior
        # The add_documents_to_supabase function should handle duplicates
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    async def test_storage_processes_different_file_types(self, mock_add_docs, document_storage_service):
        """Test processing different file types based on content."""
        # Test markdown
        markdown_content = "# Markdown\n\nThis is **bold** text."
        success, result = await document_storage_service.upload_document(
            file_content=markdown_content,
            filename="test.md"
        )
        assert success is True
        
        # Test plain text
        text_content = "Plain text without any formatting."
        success, result = await document_storage_service.upload_document(
            file_content=text_content,
            filename="test.txt"
        )
        assert success is True
        
        # Test code file
        code_content = "function test() {\n  return true;\n}"
        success, result = await document_storage_service.upload_document(
            file_content=code_content,
            filename="test.js"
        )
        assert success is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_storage_validates_file_size_limits(self, document_storage_service):
        """Test file size validation."""
        # Create a very large document
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        
        # Current implementation doesn't have size limits
        # This test documents where size validation could be added
        success, result = await document_storage_service.upload_document(
            file_content=large_content,
            filename="large.txt",
            chunk_size=5000
        )
        
        # Should still succeed but create many chunks
        assert success is True
        assert result["chunks_stored"] > 1000
    
    @pytest.mark.unit
    def test_storage_extracts_text_from_pdf(self, document_storage_service):
        """Test PDF text extraction."""
        # Note: Current implementation expects text content
        # PDF extraction would happen before calling upload_document
        # This test documents the expected interface
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_storage_handles_encoding_issues(self, document_storage_service):
        """Test handling of various text encodings."""
        # Test UTF-8 with special characters
        utf8_content = "Test with émojis 🚀 and spëcial characters: café"
        
        success, result = await document_storage_service.upload_document(
            file_content=utf8_content,
            filename="utf8.txt"
        )
        
        assert success is True
        assert result["chunks_stored"] >= 1
    
    @pytest.mark.unit
    def test_extract_section_info(self, document_storage_service):
        """Test section info extraction from chunks."""
        # Arrange
        chunk_with_headers = """## Section Header
Some content here.

### Subsection
More content with details."""
        
        # Act
        info = document_storage_service.extract_section_info(chunk_with_headers)
        
        # Assert
        assert "headers" in info
        assert "## Section Header" in info["headers"]
        assert "### Subsection" in info["headers"]
        assert info["word_count"] == 9
        assert info["char_count"] == len(chunk_with_headers)
    
    @pytest.mark.unit
    def test_smart_chunk_preserves_code_blocks(self, document_storage_service):
        """Test that code blocks are preserved during chunking."""
        # Arrange
        content_with_code = """Some text before code.

```python
def important_function():
    # This should not be split
    result = complex_operation()
    return result
```

Text after code block."""
        
        # Act
        chunks = document_storage_service.smart_chunk_markdown(
            content_with_code,
            chunk_size=50  # Small size to force chunking
        )
        
        # Assert
        # Code block should be kept together
        code_block_found = False
        for chunk in chunks:
            if "def important_function():" in chunk:
                code_block_found = True
                assert "return result" in chunk  # Complete function in same chunk
                break
        
        assert code_block_found
    
    @pytest.mark.unit
    def test_smart_chunk_handles_empty_input(self, document_storage_service):
        """Test chunking with empty or invalid input."""
        # Test empty string
        assert document_storage_service.smart_chunk_markdown("") == []
        
        # Test None
        assert document_storage_service.smart_chunk_markdown(None) == []
        
        # Test whitespace only
        chunks = document_storage_service.smart_chunk_markdown("   \n\n   ")
        assert len(chunks) <= 1
    
    @pytest.mark.unit
    @patch('src.services.rag.document_storage_service.add_code_examples_to_supabase')
    def test_store_code_examples(self, mock_add_code, document_storage_service):
        """Test storing code examples."""
        # Arrange
        code_examples = [
            {
                "url": "https://example.com/code",
                "code_block": "def test():\n    pass",
                "summary": "Test function"
            },
            {
                "url": "https://example.com/code2",
                "code_block": "class Example:\n    pass",
                "summary": "Example class"
            }
        ]
        
        # Act
        success, result = document_storage_service.store_code_examples(code_examples)
        
        # Assert
        assert success is True
        assert result["code_examples_stored"] == 2
        mock_add_code.assert_called_once()
        
        # Verify call arguments
        call_args = mock_add_code.call_args[1]
        assert len(call_args["urls"]) == 2
        assert len(call_args["code_examples"]) == 2
        assert call_args["summaries"] == ["Test function", "Example class"]
    
    @pytest.mark.unit
    def test_process_code_example(self, document_storage_service):
        """Test processing individual code examples."""
        # Test dict format
        code_dict = {
            "code": "print('Hello')",
            "context_before": "This is a greeting:",
            "context_after": "Output: Hello"
        }
        
        with patch('src.services.rag.document_storage_service.generate_code_example_summary',
                  return_value="Print greeting example"):
            summary = document_storage_service.process_code_example(code_dict)
            assert summary == "Print greeting example"
        
        # Test error handling
        with patch('src.services.rag.document_storage_service.generate_code_example_summary',
                  side_effect=Exception("Processing error")):
            summary = document_storage_service.process_code_example(code_dict)
            assert "processing failed" in summary