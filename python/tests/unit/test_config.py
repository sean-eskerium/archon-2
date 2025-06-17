"""Unit tests for config module."""
import pytest
import os
from unittest.mock import patch
from src.config import (
    EnvironmentConfig, RAGStrategyConfig, ConfigurationError,
    validate_openai_api_key, validate_supabase_url,
    load_environment_config, get_rag_strategy_config
)


class TestConfigValidation:
    """Unit tests for configuration validation functions."""
    
    @pytest.mark.unit
    def test_validate_openai_api_key_success(self):
        """Test valid OpenAI API key validation."""
        assert validate_openai_api_key("sk-test123456789") is True
        assert validate_openai_api_key("sk-proj-test123456789") is True
    
    @pytest.mark.unit
    def test_validate_openai_api_key_invalid_format(self):
        """Test invalid OpenAI API key format."""
        with pytest.raises(ConfigurationError, match="must start with 'sk-'"):
            validate_openai_api_key("invalid-key")
        
        with pytest.raises(ConfigurationError, match="cannot be empty"):
            validate_openai_api_key("")
    
    @pytest.mark.unit
    def test_validate_supabase_url_success(self):
        """Test valid Supabase URL validation."""
        assert validate_supabase_url("https://example.supabase.co") is True
        assert validate_supabase_url("https://test.supabase.co/api/v1") is True
    
    @pytest.mark.unit
    def test_validate_supabase_url_invalid(self):
        """Test invalid Supabase URL validation."""
        with pytest.raises(ConfigurationError, match="cannot be empty"):
            validate_supabase_url("")
        
        with pytest.raises(ConfigurationError, match="must use HTTPS"):
            validate_supabase_url("http://example.supabase.co")
        
        with pytest.raises(ConfigurationError, match="Invalid Supabase URL format"):
            validate_supabase_url("https://")


class TestEnvironmentConfig:
    """Unit tests for environment configuration loading."""
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "sk-test123",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-service-key"
    })
    def test_load_environment_config_success(self):
        """Test successful environment configuration loading."""
        config = load_environment_config()
        
        assert config.openai_api_key == "sk-test123"
        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_service_key == "test-service-key"
        assert config.host == "0.0.0.0"  # Default
        assert config.port == 8051  # Default
        assert config.transport == "sse"  # Default
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "HOST": "localhost",
        "PORT": "8080",
        "TRANSPORT": "stdio"
    }, clear=True)
    def test_load_environment_config_custom_values(self):
        """Test environment config with custom values."""
        config = load_environment_config()
        
        assert config.openai_api_key is None  # Optional
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.transport == "stdio"
    
    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_load_environment_config_missing_required(self):
        """Test missing required environment variables."""
        with pytest.raises(ConfigurationError, match="SUPABASE_URL environment variable is required"):
            load_environment_config()
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co"
    }, clear=True)
    def test_load_environment_config_missing_service_key(self):
        """Test missing Supabase service key."""
        with pytest.raises(ConfigurationError, match="SUPABASE_SERVICE_KEY environment variable is required"):
            load_environment_config()
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "invalid"
    })
    def test_load_environment_config_invalid_port(self):
        """Test invalid port configuration."""
        with pytest.raises(ConfigurationError, match="PORT must be a valid integer"):
            load_environment_config()


class TestRAGStrategyConfig:
    """Unit tests for RAG strategy configuration."""
    
    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_get_rag_strategy_config_defaults(self):
        """Test RAG strategy config with default values."""
        config = get_rag_strategy_config()
        
        assert config.use_contextual_embeddings is False
        assert config.use_hybrid_search is False
        assert config.use_agentic_rag is False
        assert config.use_reranking is False
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "USE_CONTEXTUAL_EMBEDDINGS": "true",
        "USE_HYBRID_SEARCH": "1",
        "USE_AGENTIC_RAG": "yes",
        "USE_RERANKING": "on"
    })
    def test_get_rag_strategy_config_true_values(self):
        """Test RAG strategy config with various true values."""
        config = get_rag_strategy_config()
        
        assert config.use_contextual_embeddings is True
        assert config.use_hybrid_search is True
        assert config.use_agentic_rag is True
        assert config.use_reranking is True
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "USE_CONTEXTUAL_EMBEDDINGS": "false",
        "USE_HYBRID_SEARCH": "0",
        "USE_AGENTIC_RAG": "no",
        "USE_RERANKING": "off"
    })
    def test_get_rag_strategy_config_false_values(self):
        """Test RAG strategy config with various false values."""
        config = get_rag_strategy_config()
        
        assert config.use_contextual_embeddings is False
        assert config.use_hybrid_search is False
        assert config.use_agentic_rag is False
        assert config.use_reranking is False
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        "USE_CONTEXTUAL_EMBEDDINGS": "TRUE",
        "USE_HYBRID_SEARCH": "True"
    })
    def test_get_rag_strategy_config_case_insensitive(self):
        """Test RAG strategy config is case insensitive."""
        config = get_rag_strategy_config()
        
        assert config.use_contextual_embeddings is True
        assert config.use_hybrid_search is True


class TestDataClasses:
    """Unit tests for configuration data classes."""
    
    @pytest.mark.unit
    def test_environment_config_creation(self):
        """Test EnvironmentConfig dataclass creation."""
        config = EnvironmentConfig(
            openai_api_key="sk-test",
            supabase_url="https://test.supabase.co",
            supabase_service_key="key",
            host="localhost",
            port=9000,
            transport="sse"
        )
        
        assert config.openai_api_key == "sk-test"
        assert config.port == 9000
    
    @pytest.mark.unit
    def test_rag_strategy_config_creation(self):
        """Test RAGStrategyConfig dataclass creation."""
        config = RAGStrategyConfig(
            use_contextual_embeddings=True,
            use_hybrid_search=False
        )
        
        assert config.use_contextual_embeddings is True
        assert config.use_hybrid_search is False
        assert config.use_agentic_rag is False  # Default
    
    @pytest.mark.unit
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)