"""Unit tests for DocumentStorageService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any, Optional

from src.services.rag.document_storage_service import DocumentStorageService
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_called_with_subset,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestDocumentStorageService:
    """Unit tests for DocumentStorageService with enhanced patterns."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def document_storage_service(self, mock_supabase_client):
        """Create DocumentStorageService instance with mocked dependencies."""
        return DocumentStorageService(supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def make_document_content(self):
        """Factory for creating test document content."""
        def _make_content(
            size: str = "medium",
            include_code: bool = False,
            include_headers: bool = True,
            language: str = "markdown"
        ) -> str:
            base_content = []
            
            if include_headers:
                base_content.append("# Test Document\n")
                base_content.append("## Introduction\n")
            
            if size == "small":
                base_content.append("This is a small test document.")
            elif size == "medium":
                base_content.extend([
                    "This is a medium-sized document with multiple sections.\n",
                    "It contains various types of content for testing.\n\n",
                    "## Section 1\n",
                    "Content for section 1 with multiple sentences. ",
                    "Each sentence adds meaningful information. ",
                    "This helps test chunking behavior.\n\n"
                ])
            elif size == "large":
                # Generate large content
                for i in range(50):
                    base_content.append(f"## Section {i+1}\n")
                    base_content.append(f"This is paragraph {i+1} with substantial content. " * 10)
                    base_content.append("\n\n")
            
            if include_code:
                base_content.extend([
                    "\n## Code Example\n",
                    "```python\n",
                    "def example_function(param1, param2):\n",
                    "    '''Example function with documentation.'''\n",
                    "    result = param1 + param2\n",
                    "    return result\n",
                    "```\n\n"
                ])
            
            return "".join(base_content)
        return _make_content
    
    # =============================================================================
    # Document Chunking Tests
    # =============================================================================
    
    @pytest.mark.parametrize("content_size,chunk_size,expected_chunks", [
        pytest.param("small", 100, 1, id="small-doc-large-chunks"),
        pytest.param("medium", 100, 3, id="medium-doc-small-chunks"),
        pytest.param("large", 500, 50, id="large-doc-medium-chunks"),
    ])
    def test_chunk_documents_various_sizes(
        self,
        document_storage_service,
        make_document_content,
        content_size,
        chunk_size,
        expected_chunks
    ):
        """Test document chunking with various document and chunk sizes."""
        # Arrange
        content = make_document_content(size=content_size)
        
        # Act
        chunks = document_storage_service.smart_chunk_markdown(
            content,
            chunk_size=chunk_size
        )
        
        # Assert
        assert len(chunks) >= expected_chunks
        assert all(len(chunk) <= chunk_size * 1.5 for chunk in chunks)  # Allow some overflow
        assert all(chunk.strip() for chunk in chunks)  # No empty chunks
        
        # Verify content preservation
        if content:
            reconstructed = "\n".join(chunks)
            assert "Test Document" in reconstructed or content_size == "small"
    
    @pytest.mark.parametrize("code_content,chunk_size", [
        pytest.param(
            """```python
def long_function():
    # This is a very long function
    step1 = process_data()
    step2 = transform_data(step1)
    step3 = validate_data(step2)
    return finalize(step3)
```""",
            50,
            id="code-block-preservation"
        ),
        pytest.param(
            """```sql
SELECT * FROM users
WHERE status = 'active'
AND created_at > '2024-01-01'
ORDER BY created_at DESC;
```""",
            30,
            id="sql-block-preservation"
        ),
    ])
    def test_preserve_code_blocks_during_chunking(
        self,
        document_storage_service,
        code_content,
        chunk_size
    ):
        """Test that code blocks are not split during chunking."""
        # Arrange
        full_content = f"Some text before.\n\n{code_content}\n\nSome text after."
        
        # Act
        chunks = document_storage_service.smart_chunk_markdown(
            full_content,
            chunk_size=chunk_size
        )
        
        # Assert
        # Find chunk containing code
        code_chunks = [chunk for chunk in chunks if "```" in chunk]
        assert len(code_chunks) >= 1
        
        # Verify code block is complete in one chunk
        for chunk in code_chunks:
            if "def long_function():" in chunk or "SELECT * FROM users" in chunk:
                # Count opening and closing backticks
                opening_count = chunk.count("```")
                assert opening_count % 2 == 0  # Should have matching pairs
    
    # =============================================================================
    # Embedding Generation Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("knowledge_type,tags,expected_metadata", [
        pytest.param(
            "technical",
            ["api", "documentation"],
            {"knowledge_type": "technical", "tags": ["api", "documentation"]},
            id="technical-docs"
        ),
        pytest.param(
            "business",
            ["strategy", "planning"],
            {"knowledge_type": "business", "tags": ["strategy", "planning"]},
            id="business-docs"
        ),
        pytest.param(
            "general",
            [],
            {"knowledge_type": "general", "tags": []},
            id="general-docs"
        ),
    ])
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    @patch('src.services.rag.document_storage_service.update_source_info')
    async def test_document_upload_with_metadata(
        self,
        mock_update_source,
        mock_add_docs,
        document_storage_service,
        make_document_content,
        knowledge_type,
        tags,
        expected_metadata
    ):
        """Test document upload with various metadata configurations."""
        # Arrange
        content = make_document_content(size="medium")
        mock_add_docs.return_value = None
        
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=content,
            filename="test_doc.md",
            knowledge_type=knowledge_type,
            tags=tags
        )
        
        # Assert
        assert success is True
        assert result["chunks_stored"] > 0
        
        # Verify metadata
        call_args = mock_add_docs.call_args[1]
        metadatas = call_args["metadatas"]
        
        for metadata in metadatas:
            assert_subset(expected_metadata, metadata)
            assert metadata["filename"] == "test_doc.md"
            assert "word_count" in metadata
            assert "char_count" in metadata
    
    # =============================================================================
    # File Type Processing Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("filename,content_type,content_sample", [
        pytest.param("doc.md", "markdown", "# Header\n\n**Bold** text", id="markdown-file"),
        pytest.param("readme.txt", "text", "Plain text content", id="text-file"),
        pytest.param("script.py", "code", "def main():\n    pass", id="python-file"),
        pytest.param("style.css", "code", ".class { color: red; }", id="css-file"),
        pytest.param("data.json", "code", '{"key": "value"}', id="json-file"),
    ])
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    async def test_process_various_file_types(
        self,
        mock_add_docs,
        document_storage_service,
        filename,
        content_type,
        content_sample
    ):
        """Test processing various file types."""
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=content_sample,
            filename=filename
        )
        
        # Assert
        assert success is True
        assert result["chunks_stored"] >= 1
        
        # Verify appropriate processing based on file type
        call_args = mock_add_docs.call_args[1]
        assert len(call_args["contents"]) >= 1
    
    # =============================================================================
    # Content Size and Validation Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("content_size_mb,chunk_size,should_succeed", [
        pytest.param(0.1, 1000, True, id="small-file"),
        pytest.param(1, 5000, True, id="medium-file"),
        pytest.param(5, 10000, True, id="large-file"),
        pytest.param(10, 20000, True, id="very-large-file"),
    ])
    async def test_file_size_handling(
        self,
        document_storage_service,
        content_size_mb,
        chunk_size,
        should_succeed
    ):
        """Test handling of various file sizes."""
        # Arrange
        content = "x" * int(content_size_mb * 1024 * 1024)
        
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=content,
            filename=f"large_{content_size_mb}mb.txt",
            chunk_size=chunk_size
        )
        
        # Assert
        assert success == should_succeed
        if should_succeed:
            assert result["chunks_stored"] > 0
            # Larger files should create more chunks
            expected_min_chunks = int(len(content) / chunk_size * 0.8)
            assert result["chunks_stored"] >= expected_min_chunks
    
    # =============================================================================
    # Section Information Extraction Tests
    # =============================================================================
    
    @pytest.mark.parametrize("chunk_content,expected_headers", [
        pytest.param(
            "# Main Title\n## Subtitle\nContent here",
            ["# Main Title", "## Subtitle"],
            id="markdown-headers"
        ),
        pytest.param(
            "### Deep Section\n#### Subsection\nText content",
            ["### Deep Section", "#### Subsection"],
            id="deep-headers"
        ),
        pytest.param(
            "No headers here, just plain text.",
            [],
            id="no-headers"
        ),
    ])
    def test_extract_section_information(
        self,
        document_storage_service,
        chunk_content,
        expected_headers
    ):
        """Test extraction of section information from chunks."""
        # Act
        info = document_storage_service.extract_section_info(chunk_content)
        
        # Assert
        assert "headers" in info
        assert info["headers"] == expected_headers
        assert info["word_count"] > 0
        assert info["char_count"] == len(chunk_content)
    
    # =============================================================================
    # Code Example Storage Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_examples", [0, 1, 5, 20])
    @patch('src.services.rag.document_storage_service.add_code_examples_to_supabase')
    def test_store_code_examples_batch(
        self,
        mock_add_code,
        document_storage_service,
        num_examples
    ):
        """Test storing batches of code examples."""
        # Arrange
        code_examples = []
        for i in range(num_examples):
            code_examples.append({
                "url": f"https://example.com/code{i}",
                "code_block": f"def function_{i}():\n    return {i}",
                "summary": f"Function {i} example"
            })
        
        # Act
        success, result = document_storage_service.store_code_examples(code_examples)
        
        # Assert
        assert success is True
        assert result["code_examples_stored"] == num_examples
        
        if num_examples > 0:
            mock_add_code.assert_called_once()
            call_args = mock_add_code.call_args[1]
            assert len(call_args["urls"]) == num_examples
            assert len(call_args["code_examples"]) == num_examples
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("input_content,expected_result", [
        pytest.param("", [], id="empty-string"),
        pytest.param(None, [], id="none-input"),
        pytest.param("   \n\t   ", [], id="whitespace-only"),
        pytest.param("\n\n\n", [], id="newlines-only"),
    ])
    def test_handle_invalid_input(
        self,
        document_storage_service,
        input_content,
        expected_result
    ):
        """Test handling of invalid or empty input."""
        # Act
        chunks = document_storage_service.smart_chunk_markdown(input_content)
        
        # Assert
        assert chunks == expected_result or (
            len(chunks) <= 1 and all(not chunk.strip() for chunk in chunks)
        )
    
    @pytest.mark.asyncio
    @patch('src.services.rag.document_storage_service.add_documents_to_supabase')
    async def test_handle_storage_errors(
        self,
        mock_add_docs,
        document_storage_service,
        make_document_content
    ):
        """Test error handling during document storage."""
        # Arrange
        mock_add_docs.side_effect = Exception("Storage error")
        content = make_document_content(size="small")
        
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=content,
            filename="error_test.md"
        )
        
        # Assert
        assert success is False
        assert "error" in result
        assert "Storage error" in str(result["error"])
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("doc_size_mb", [1, 5, 10])
    def test_chunking_performance(
        self,
        document_storage_service,
        doc_size_mb
    ):
        """Test chunking performance with large documents."""
        # Arrange
        # Generate content with realistic structure
        content_parts = []
        words_per_mb = 150000  # Approximate words per MB
        total_words = words_per_mb * doc_size_mb
        
        for i in range(0, total_words, 1000):
            if i % 5000 == 0:
                content_parts.append(f"\n## Section {i//5000}\n")
            content_parts.append("Sample text content. " * 100)
        
        content = "".join(content_parts)
        
        # Act & Assert
        with measure_time(f"chunk_{doc_size_mb}mb_document", threshold=2.0):
            chunks = document_storage_service.smart_chunk_markdown(
                content,
                chunk_size=5000
            )
        
        assert len(chunks) > 0
        assert all(chunk for chunk in chunks)  # All chunks have content
    
    # =============================================================================
    # Encoding and Special Characters Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("content,description", [
        pytest.param("Hello 世界! 🌍", "unicode-emoji", id="unicode-with-emoji"),
        pytest.param("Café, naïve, résumé", "accented-chars", id="accented-characters"),
        pytest.param("¿Cómo estás? ¡Hola!", "spanish-chars", id="spanish-punctuation"),
        pytest.param("Здравствуйте мир", "cyrillic", id="cyrillic-text"),
    ])
    async def test_handle_various_encodings(
        self,
        document_storage_service,
        content,
        description
    ):
        """Test handling of various character encodings."""
        # Act
        success, result = await document_storage_service.upload_document(
            file_content=content,
            filename=f"{description}.txt"
        )
        
        # Assert
        assert success is True
        assert result["chunks_stored"] >= 1


def assert_subset(subset: Dict, superset: Dict):
    """Helper to assert subset dictionary is contained in superset."""
    for key, value in subset.items():
        assert key in superset
        assert superset[key] == value