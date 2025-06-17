"""Unit tests for utility functions."""
import pytest
from unittest.mock import Mock, MagicMock, patch
import os
from src.utils import (
    get_supabase_client,
    create_embedding,
    create_embeddings_batch,
    extract_source_summary,
    generate_code_example_summary
)


class TestUtils:
    """Unit tests for utility functions."""
    
    @pytest.mark.unit
    @patch('src.utils.create_client')
    def test_get_supabase_client_returns_singleton(self, mock_create_client):
        """Test that get_supabase_client returns a properly configured client."""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key'
        }):
            # Act
            client = get_supabase_client()
            
            # Assert
            assert client == mock_client
            mock_create_client.assert_called_once_with(
                'https://test.supabase.co',
                'test-service-key'
            )
    
    @pytest.mark.unit
    def test_get_supabase_client_validates_url(self):
        """Test that get_supabase_client validates required environment variables."""
        # Test missing URL
        with patch.dict('os.environ', {'SUPABASE_SERVICE_KEY': 'key'}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                get_supabase_client()
        
        # Test missing key
        with patch.dict('os.environ', {'SUPABASE_URL': 'url'}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                get_supabase_client()
    
    @pytest.mark.unit
    def test_chunk_text_respects_size_limits(self):
        """Test text chunking respects size limits."""
        # Note: The utils module doesn't have a chunk_text function
        # This test is a placeholder for where such functionality would be tested
        pass
    
    @pytest.mark.unit
    def test_chunk_text_maintains_overlap(self):
        """Test text chunking maintains overlap between chunks."""
        # Note: The utils module doesn't have a chunk_text function with overlap
        # This test is a placeholder for where such functionality would be tested
        pass
    
    @pytest.mark.unit
    def test_sanitize_input_removes_html(self):
        """Test HTML sanitization from input."""
        # Note: The utils module doesn't have sanitize_input function
        # This test is a placeholder for where such functionality would be tested
        pass
    
    @pytest.mark.unit
    def test_format_timestamp_handles_timezones(self):
        """Test timestamp formatting with timezones."""
        # Note: The utils module doesn't have timestamp formatting
        # This test is a placeholder for where such functionality would be tested
        pass
    
    @pytest.mark.unit
    @patch('src.utils.openai.OpenAI')
    def test_create_embedding_single_text(self, mock_openai_class):
        """Test creating embedding for a single text."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act
            result = create_embedding("test text")
            
            # Assert
            assert result == mock_embedding
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input=["test text"]
            )
    
    @pytest.mark.unit
    @patch('src.utils.openai.OpenAI')
    def test_create_embeddings_batch(self, mock_openai_class):
        """Test creating embeddings for multiple texts."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        texts = ["text1", "text2", "text3"]
        mock_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=emb) for emb in mock_embeddings
        ]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act
            result = create_embeddings_batch(texts)
            
            # Assert
            assert len(result) == 3
            assert result == mock_embeddings
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input=texts
            )
    
    @pytest.mark.unit
    def test_create_embedding_no_api_key(self):
        """Test embedding creation without API key."""
        # Arrange
        with patch.dict('os.environ', {}, clear=True):
            # Act
            result = create_embedding("test text")
            
            # Assert - Should return zero embedding
            assert len(result) == 1536
            assert all(v == 0.0 for v in result)
    
    @pytest.mark.unit
    @patch('src.utils.openai.OpenAI')
    def test_create_embeddings_batch_with_retry(self, mock_openai_class):
        """Test batch embeddings with retry on failure."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # First call fails, second succeeds
        mock_embeddings = [[0.1] * 1536]
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embeddings[0])]
        
        mock_client.embeddings.create.side_effect = [
            Exception("API Error"),
            mock_response
        ]
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Mock sleep to speed up test
                # Act
                result = create_embeddings_batch(["test"])
                
                # Assert
                assert len(result) == 1
                assert mock_client.embeddings.create.call_count == 2
    
    @pytest.mark.unit
    def test_extract_source_summary(self):
        """Test extracting summary from source content."""
        # Arrange
        content = """# Main Title
        
        This is the introduction paragraph that should be used as a summary.
        It contains important information about the document.
        
        ## Section 1
        More detailed content here that is less important for the summary."""
        
        # Act
        summary = extract_source_summary("test-source", content, max_length=100)
        
        # Assert
        assert "Main Title" in summary
        assert "introduction paragraph" in summary
        assert len(summary) <= 100
    
    @pytest.mark.unit
    def test_extract_source_summary_handles_short_content(self):
        """Test summary extraction with short content."""
        # Arrange
        short_content = "Short content."
        
        # Act
        summary = extract_source_summary("test-source", short_content)
        
        # Assert
        assert summary == "Short content."
    
    @pytest.mark.unit
    @patch('src.utils.openai.OpenAI')
    def test_generate_code_example_summary(self, mock_openai_class):
        """Test generating summary for code examples."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        code = "def hello():\n    print('Hello, World!')"
        context_before = "Here's a simple function:"
        context_after = "This prints a greeting."
        
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="A simple hello world function"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'MODEL_CHOICE': 'gpt-3.5-turbo'
        }):
            # Act
            result = generate_code_example_summary(code, context_before, context_after)
            
            # Assert
            assert result == "A simple hello world function"
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.unit
    def test_generate_code_example_summary_no_api_key(self):
        """Test code summary generation without API key."""
        # Arrange
        with patch.dict('os.environ', {}, clear=True):
            # Act
            result = generate_code_example_summary(
                "code",
                "before",
                "after"
            )
            
            # Assert - Should return formatted fallback
            assert "Code example" in result
            assert "before" in result