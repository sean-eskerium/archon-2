"""Unit tests for utility functions with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
from typing import List, Dict, Any, Optional
import time

from src.utils import (
    get_supabase_client,
    create_embedding,
    create_embeddings_batch,
    extract_source_summary,
    generate_code_example_summary
)
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestUtils:
    """Unit tests for utility functions with enhanced patterns."""
    
    # =============================================================================
    # Supabase Client Tests
    # =============================================================================
    
    @pytest.mark.parametrize("env_vars,should_succeed", [
        pytest.param(
            {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_SERVICE_KEY': 'test-key'},
            True,
            id="valid-credentials"
        ),
        pytest.param(
            {'SUPABASE_URL': '', 'SUPABASE_SERVICE_KEY': 'test-key'},
            False,
            id="empty-url"
        ),
        pytest.param(
            {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_SERVICE_KEY': ''},
            False,
            id="empty-key"
        ),
        pytest.param(
            {},
            False,
            id="missing-credentials"
        ),
    ])
    @patch('src.utils.create_client')
    def test_supabase_client_initialization(
        self,
        mock_create_client,
        env_vars,
        should_succeed
    ):
        """Test Supabase client initialization with various configurations."""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch.dict('os.environ', env_vars, clear=True):
            if should_succeed:
                # Act
                client = get_supabase_client()
                
                # Assert
                assert client == mock_client
                mock_create_client.assert_called_once_with(
                    env_vars['SUPABASE_URL'],
                    env_vars['SUPABASE_SERVICE_KEY']
                )
            else:
                # Act & Assert
                with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                    get_supabase_client()
    
    @patch('src.utils.create_client')
    def test_supabase_client_singleton_pattern(self, mock_create_client):
        """Test that get_supabase_client returns singleton instance."""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            # Act - Get client multiple times
            client1 = get_supabase_client()
            client2 = get_supabase_client()
            client3 = get_supabase_client()
            
            # Assert
            assert client1 is client2 is client3
            mock_create_client.assert_called_once()  # Only called once
    
    # =============================================================================
    # Embedding Creation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("text,model", [
        pytest.param("simple text", "text-embedding-3-small", id="small-model"),
        pytest.param("longer text with multiple sentences", "text-embedding-3-small", id="long-text"),
        pytest.param("", "text-embedding-3-small", id="empty-text"),
        pytest.param("特殊字符 🚀", "text-embedding-3-small", id="unicode-text"),
    ])
    @patch('src.utils.openai.OpenAI')
    def test_create_single_embedding(
        self,
        mock_openai_class,
        text,
        model
    ):
        """Test creating embeddings for various text inputs."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_embedding = [0.1 * i for i in range(1536)]  # Realistic embedding
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act
            result = create_embedding(text)
            
            # Assert
            assert len(result) == 1536
            assert result == mock_embedding
            mock_client.embeddings.create.assert_called_once_with(
                model=model,
                input=[text]
            )
    
    @pytest.mark.parametrize("batch_size", [1, 5, 10, 50, 100])
    @patch('src.utils.openai.OpenAI')
    def test_create_embeddings_batch_various_sizes(
        self,
        mock_openai_class,
        batch_size
    ):
        """Test batch embedding creation with various batch sizes."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        texts = [f"Text {i}" for i in range(batch_size)]
        mock_embeddings = [[0.1 * j for j in range(1536)] for i in range(batch_size)]
        
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=emb) for emb in mock_embeddings
        ]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act
            result = create_embeddings_batch(texts)
            
            # Assert
            assert len(result) == batch_size
            assert all(len(emb) == 1536 for emb in result)
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input=texts
            )
    
    @pytest.mark.parametrize("api_key_present", [True, False])
    def test_embedding_fallback_without_api_key(self, api_key_present):
        """Test embedding creation fallback when API key is missing."""
        # Arrange
        env_vars = {'OPENAI_API_KEY': 'test-key'} if api_key_present else {}
        
        with patch.dict('os.environ', env_vars, clear=True):
            if not api_key_present:
                # Act
                result = create_embedding("test text")
                
                # Assert - Should return zero embedding
                assert len(result) == 1536
                assert all(v == 0.0 for v in result)
            else:
                # With API key, it should try to call OpenAI
                with patch('src.utils.openai.OpenAI') as mock_openai:
                    mock_client = MagicMock()
                    mock_openai.return_value = mock_client
                    mock_response = MagicMock()
                    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
                    mock_client.embeddings.create.return_value = mock_response
                    
                    result = create_embedding("test text")
                    assert mock_client.embeddings.create.called
    
    @pytest.mark.parametrize("failure_count,max_retries", [
        pytest.param(0, 3, id="no-failures"),
        pytest.param(1, 3, id="one-retry"),
        pytest.param(2, 3, id="two-retries"),
        pytest.param(3, 3, id="max-retries"),
    ])
    @patch('src.utils.openai.OpenAI')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_embedding_retry_logic(
        self,
        mock_sleep,
        mock_openai_class,
        failure_count,
        max_retries
    ):
        """Test retry logic for embedding creation."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Create side effects - failures followed by success
        side_effects = [Exception("API Error")] * failure_count
        
        if failure_count < max_retries:
            # Add successful response after failures
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            side_effects.append(mock_response)
        
        mock_client.embeddings.create.side_effect = side_effects
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act
            result = create_embeddings_batch(["test"])
            
            # Assert
            if failure_count < max_retries:
                assert len(result) == 1
                assert len(result[0]) == 1536
                assert mock_client.embeddings.create.call_count == failure_count + 1
            else:
                # Should return zero embeddings after max retries
                assert len(result) == 1
                assert all(v == 0.0 for v in result[0])
    
    # =============================================================================
    # Text Processing Tests
    # =============================================================================
    
    @pytest.mark.parametrize("content,max_length,expected_contains", [
        pytest.param(
            "# Title\n\nShort intro.",
            100,
            ["Title", "Short intro"],
            id="short-content"
        ),
        pytest.param(
            "# Main Title\n\nThis is a long introduction that should be truncated because it exceeds the maximum length limit set for the summary extraction.",
            50,
            ["Main Title"],
            id="truncated-content"
        ),
        pytest.param(
            "No headers here, just plain text content.",
            100,
            ["No headers here"],
            id="no-headers"
        ),
        pytest.param(
            "",
            100,
            [],
            id="empty-content"
        ),
    ])
    def test_extract_source_summary_various_content(
        self,
        content,
        max_length,
        expected_contains
    ):
        """Test source summary extraction with various content types."""
        # Act
        summary = extract_source_summary("test-source", content, max_length=max_length)
        
        # Assert
        assert len(summary) <= max_length
        for expected in expected_contains:
            assert expected in summary
    
    @pytest.mark.parametrize("content_size", [10, 100, 1000, 10000])
    def test_extract_summary_performance(self, content_size):
        """Test summary extraction performance with various content sizes."""
        # Arrange
        content = "Lorem ipsum dolor sit amet. " * (content_size // 30)
        
        # Act & Assert
        with measure_time(f"extract_summary_{content_size}_chars", threshold=0.1):
            summary = extract_source_summary("source", content, max_length=200)
        
        assert len(summary) <= 200
    
    # =============================================================================
    # Code Summary Generation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("code,context_before,context_after,has_api_key", [
        pytest.param(
            "def add(a, b):\n    return a + b",
            "Here's a simple addition function:",
            "This adds two numbers.",
            True,
            id="simple-function-with-key"
        ),
        pytest.param(
            "class Calculator:\n    pass",
            "Calculator class:",
            "",
            True,
            id="class-definition"
        ),
        pytest.param(
            "print('Hello')",
            "",
            "",
            False,
            id="no-api-key"
        ),
    ])
    @patch('src.utils.openai.OpenAI')
    def test_generate_code_summary_various_inputs(
        self,
        mock_openai_class,
        code,
        context_before,
        context_after,
        has_api_key
    ):
        """Test code summary generation with various inputs."""
        # Arrange
        env_vars = {'OPENAI_API_KEY': 'test-key', 'MODEL_CHOICE': 'gpt-3.5-turbo'} if has_api_key else {}
        
        if has_api_key:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Generated summary for the code"))
            ]
            mock_client.chat.completions.create.return_value = mock_response
        
        with patch.dict('os.environ', env_vars, clear=True):
            # Act
            result = generate_code_example_summary(code, context_before, context_after)
            
            # Assert
            if has_api_key:
                assert result == "Generated summary for the code"
                mock_client.chat.completions.create.assert_called_once()
            else:
                # Should return fallback
                assert "Code example" in result
                if context_before:
                    assert context_before in result
    
    @pytest.mark.parametrize("error_type", [
        pytest.param(Exception("API Error"), id="generic-error"),
        pytest.param(ValueError("Invalid input"), id="value-error"),
        pytest.param(ConnectionError("Network error"), id="connection-error"),
    ])
    @patch('src.utils.openai.OpenAI')
    def test_code_summary_error_handling(
        self,
        mock_openai_class,
        error_type
    ):
        """Test code summary generation error handling."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = error_type
        
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'MODEL_CHOICE': 'gpt-3.5-turbo'
        }):
            # Act
            result = generate_code_example_summary("code", "before", "after")
            
            # Assert - Should return fallback on error
            assert "Code example" in result
            assert "before" in result
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("batch_size", [100, 500, 1000])
    @patch('src.utils.openai.OpenAI')
    def test_batch_embedding_performance(
        self,
        mock_openai_class,
        batch_size
    ):
        """Test batch embedding performance at scale."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        texts = [f"Text content {i}" for i in range(batch_size)]
        
        # Mock fast response
        mock_embeddings = [[0.1] * 1536 for _ in range(batch_size)]
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=emb) for emb in mock_embeddings
        ]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Act & Assert
            with measure_time(f"batch_embedding_{batch_size}", threshold=1.0):
                result = create_embeddings_batch(texts)
            
            assert len(result) == batch_size
    
    # =============================================================================
    # Edge Cases and Validation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("invalid_input", [
        pytest.param(None, id="none-input"),
        pytest.param([], id="empty-list"),
        pytest.param([""], id="empty-string-list"),
        pytest.param([None, "text"], id="mixed-none"),
    ])
    def test_embedding_invalid_inputs(self, invalid_input):
        """Test embedding creation with invalid inputs."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            if invalid_input is None:
                # Single embedding
                result = create_embedding(invalid_input)
                assert len(result) == 1536
                assert all(v == 0.0 for v in result)
            else:
                # Batch embedding
                result = create_embeddings_batch(invalid_input)
                assert len(result) == len(invalid_input)
                for emb in result:
                    assert len(emb) == 1536