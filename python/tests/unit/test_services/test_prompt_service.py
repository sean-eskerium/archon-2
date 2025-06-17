"""Unit tests for PromptService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from src.services.prompt_service import PromptService, prompt_service


class TestPromptService:
    """Unit tests for PromptService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def fresh_prompt_service(self):
        """Create a fresh PromptService instance."""
        # Reset singleton
        PromptService._instance = None
        PromptService._prompts = {}
        PromptService._last_loaded = None
        return PromptService()
    
    @pytest.fixture
    def sample_prompts(self):
        """Sample prompt data."""
        return [
            {
                "prompt_name": "document_agent",
                "prompt": "You are a document processing agent. Analyze and extract key information."
            },
            {
                "prompt_name": "rag_agent",
                "prompt": "You are a RAG agent. Search and retrieve relevant information."
            },
            {
                "prompt_name": "code_reviewer",
                "prompt": "You are a code review agent. Analyze code for quality and bugs."
            }
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.prompt_service.get_supabase_client')
    async def test_prompt_service_loads_prompts_on_startup(self, mock_get_client, 
                                                           fresh_prompt_service, 
                                                           mock_supabase_client,
                                                           sample_prompts):
        """Test loading prompts from database on startup."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=sample_prompts
        )
        
        # Act
        await fresh_prompt_service.load_prompts()
        
        # Assert
        assert len(fresh_prompt_service._prompts) == 3
        assert fresh_prompt_service.get_prompt("document_agent") == sample_prompts[0]["prompt"]
        assert fresh_prompt_service.get_prompt("rag_agent") == sample_prompts[1]["prompt"]
        assert fresh_prompt_service._last_loaded is not None
        mock_supabase_client.table.assert_called_with('prompts')
    
    @pytest.mark.unit
    def test_prompt_service_caches_prompts_in_memory(self, fresh_prompt_service):
        """Test that prompts are cached in memory for fast access."""
        # Arrange
        fresh_prompt_service._prompts = {
            "test_prompt": "This is a test prompt",
            "another_prompt": "Another test prompt"
        }
        
        # Act - Access prompts multiple times
        prompt1 = fresh_prompt_service.get_prompt("test_prompt")
        prompt2 = fresh_prompt_service.get_prompt("test_prompt")
        prompt3 = fresh_prompt_service.get_prompt("another_prompt")
        
        # Assert - Should return cached values without database calls
        assert prompt1 == "This is a test prompt"
        assert prompt2 == "This is a test prompt"  # Same instance
        assert prompt3 == "Another test prompt"
    
    @pytest.mark.unit
    def test_prompt_service_provides_dynamic_prompts(self, fresh_prompt_service):
        """Test retrieving prompts by name with fallback."""
        # Arrange
        fresh_prompt_service._prompts = {
            "existing_prompt": "This prompt exists"
        }
        
        # Act & Assert - Existing prompt
        assert fresh_prompt_service.get_prompt("existing_prompt") == "This prompt exists"
        
        # Act & Assert - Non-existing prompt with default
        custom_default = "Custom default prompt"
        assert fresh_prompt_service.get_prompt("missing_prompt", custom_default) == custom_default
        
        # Act & Assert - Non-existing prompt without custom default
        assert fresh_prompt_service.get_prompt("missing_prompt") == "You are a helpful AI assistant."
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.prompt_service.get_supabase_client')
    async def test_prompt_service_handles_database_errors(self, mock_get_client, 
                                                         fresh_prompt_service,
                                                         mock_supabase_client):
        """Test graceful handling of database errors."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        mock_supabase_client.table.side_effect = Exception("Database connection error")
        
        # Act
        await fresh_prompt_service.load_prompts()
        
        # Assert - Should not crash, prompts should be empty
        assert fresh_prompt_service._prompts == {}
        assert fresh_prompt_service.get_prompt("any_prompt") == "You are a helpful AI assistant."
    
    @pytest.mark.unit
    def test_prompt_service_singleton_pattern(self):
        """Test that PromptService follows singleton pattern."""
        # Reset singleton
        PromptService._instance = None
        
        # Create multiple instances
        service1 = PromptService()
        service2 = PromptService()
        service3 = prompt_service
        
        # All should be the same instance
        assert service1 is service2
        # Note: prompt_service is created at module import, might be different instance
    
    @pytest.mark.unit
    def test_get_all_prompt_names(self, fresh_prompt_service):
        """Test getting list of all available prompt names."""
        # Arrange
        fresh_prompt_service._prompts = {
            "prompt1": "Content 1",
            "prompt2": "Content 2",
            "prompt3": "Content 3"
        }
        
        # Act
        names = fresh_prompt_service.get_all_prompt_names()
        
        # Assert
        assert len(names) == 3
        assert "prompt1" in names
        assert "prompt2" in names
        assert "prompt3" in names
    
    @pytest.mark.unit
    def test_get_last_loaded_time(self, fresh_prompt_service):
        """Test getting the last loaded timestamp."""
        # Initially None
        assert fresh_prompt_service.get_last_loaded_time() is None
        
        # Set a timestamp
        test_time = datetime.now()
        fresh_prompt_service._last_loaded = test_time
        
        # Should return the timestamp
        assert fresh_prompt_service.get_last_loaded_time() == test_time
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.prompt_service.get_supabase_client')
    async def test_reload_prompts(self, mock_get_client, fresh_prompt_service, 
                                  mock_supabase_client, sample_prompts):
        """Test reloading prompts from database."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        # Initial load with 2 prompts
        initial_prompts = sample_prompts[:2]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=initial_prompts
        )
        await fresh_prompt_service.load_prompts()
        
        initial_count = len(fresh_prompt_service._prompts)
        initial_time = fresh_prompt_service._last_loaded
        
        # Update with all 3 prompts
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=sample_prompts
        )
        
        # Act
        await fresh_prompt_service.reload_prompts()
        
        # Assert
        assert len(fresh_prompt_service._prompts) == 3
        assert len(fresh_prompt_service._prompts) > initial_count
        assert fresh_prompt_service._last_loaded > initial_time
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.prompt_service.get_supabase_client')
    async def test_empty_database_response(self, mock_get_client, fresh_prompt_service,
                                          mock_supabase_client):
        """Test handling empty database response."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Act
        await fresh_prompt_service.load_prompts()
        
        # Assert
        assert fresh_prompt_service._prompts == {}
        assert fresh_prompt_service.get_all_prompt_names() == []
    
    @pytest.mark.unit
    @patch('src.services.prompt_service.logger')
    def test_logging_on_missing_prompt(self, mock_logger, fresh_prompt_service):
        """Test that missing prompts are logged."""
        # Arrange
        fresh_prompt_service._prompts = {}
        
        # Act
        result = fresh_prompt_service.get_prompt("missing_prompt")
        
        # Assert
        assert result == "You are a helpful AI assistant."
        mock_logger.warning.assert_called_with("Prompt 'missing_prompt' not found, using default")