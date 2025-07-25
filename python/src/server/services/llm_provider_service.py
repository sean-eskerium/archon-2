"""
LLM Provider Service

Provides a unified interface for creating OpenAI-compatible clients for different LLM providers.
Supports OpenAI, Ollama, and Google Gemini.
"""
import os
import openai
from typing import Optional, Union, Dict, Any
from contextlib import asynccontextmanager

from ..config.logfire_config import get_logger
from .credential_service import credential_service

logger = get_logger(__name__)


@asynccontextmanager
async def get_llm_client(provider: Optional[str] = None, use_embedding_provider: bool = False):
    """
    Create an async OpenAI-compatible client based on the configured provider.
    
    This context manager handles client creation for different LLM providers
    that support the OpenAI API format.
    
    Args:
        provider: Override provider selection
        use_embedding_provider: Use the embedding-specific provider if different
    
    Yields:
        openai.AsyncOpenAI: An OpenAI-compatible client configured for the selected provider
    """
    client = None
    
    try:
        # Get provider configuration from database settings
        if provider:
            # Explicit provider requested - get minimal config
            provider_name = provider
            api_key = await credential_service._get_provider_api_key(provider)
            rag_settings = await credential_service.get_credentials_by_category("rag_strategy")
            base_url = credential_service._get_provider_base_url(provider, rag_settings)
        else:
            # Get configured provider from database
            service_type = "embedding" if use_embedding_provider else "llm"
            provider_config = await credential_service.get_active_provider(service_type)
            provider_name = provider_config["provider"]
            api_key = provider_config["api_key"]
            base_url = provider_config["base_url"]
        
        logger.info(f"Creating LLM client for provider: {provider_name}")
        
        if provider_name == "openai":
            if not api_key:
                raise ValueError("OpenAI API key not found")
            
            client = openai.AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client created successfully")
            
        elif provider_name == "ollama":
            # Ollama requires an API key in the client but doesn't actually use it
            client = openai.AsyncOpenAI(
                api_key="ollama",  # Required but unused by Ollama
                base_url=base_url or "http://localhost:11434/v1"
            )
            logger.info(f"Ollama client created successfully with base URL: {base_url}")
            
        elif provider_name == "google":
            if not api_key:
                raise ValueError("Google API key not found")
            
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            logger.info("Google Gemini client created successfully")
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
        
        yield client
        
    except Exception as e:
        logger.error(f"Error creating LLM client for provider {provider_name if 'provider_name' in locals() else 'unknown'}: {e}")
        raise
    finally:
        # Cleanup if needed
        pass


def _get_active_provider_sync() -> Dict[str, Any]:
    """Get active provider configuration synchronously using proper credential service methods."""
    try:
        from .credential_service import credential_service
        
        # Try to use credential service's own methods
        if credential_service._cache_initialized:
            # Get RAG strategy settings (plain text values)
            rag_settings = {}
            cache = credential_service._cache
            
            # Look for rag_strategy category items
            for key, value in cache.items():
                if isinstance(value, str):  # Plain text values from rag_strategy
                    rag_settings[key] = value
                    
            provider = rag_settings.get("LLM_PROVIDER", "openai")
            
            # Get API key based on provider - API keys are encrypted so we need to decrypt them
            api_key = None
            if provider == "openai":
                openai_key_data = cache.get("OPENAI_API_KEY")
                if isinstance(openai_key_data, dict) and openai_key_data.get("is_encrypted"):
                    # Decrypt the API key
                    try:
                        api_key = credential_service._decrypt_value(openai_key_data["encrypted_value"])
                    except Exception as e:
                        logger.error(f"Failed to decrypt OpenAI API key: {e}")
                elif isinstance(openai_key_data, str):
                    api_key = openai_key_data
            elif provider == "google":
                google_key_data = cache.get("GOOGLE_API_KEY")
                if isinstance(google_key_data, dict) and google_key_data.get("is_encrypted"):
                    # Decrypt the API key
                    try:
                        api_key = credential_service._decrypt_value(google_key_data["encrypted_value"])
                    except Exception as e:
                        logger.error(f"Failed to decrypt Google API key: {e}")
                elif isinstance(google_key_data, str):
                    api_key = google_key_data
            elif provider == "ollama":
                api_key = "ollama"  # Not needed
            
            # Get base URL
            if provider == "ollama":
                base_url = rag_settings.get("LLM_BASE_URL", "http://localhost:11434/v1")
            elif provider == "google":
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            else:
                base_url = None
            
            logger.info(f"Sync provider config - Provider: {provider}, API key present: {bool(api_key)}")
            
            return {
                "provider": provider,
                "api_key": api_key,
                "base_url": base_url,
                "chat_model": rag_settings.get("MODEL_CHOICE", "gpt-4.1-nano"),
                "embedding_model": rag_settings.get("EMBEDDING_MODEL", "")
            }
        else:
            # Fallback to environment variables
            logger.warning("Credential service cache not initialized, using environment variables")
            provider = os.getenv("LLM_PROVIDER", "openai")
            if provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            elif provider == "google":
                api_key = os.getenv("GOOGLE_API_KEY")
            else:
                api_key = None
                
            return {
                "provider": provider,
                "api_key": api_key,
                "base_url": None,
                "chat_model": os.getenv("MODEL_CHOICE", "gpt-4.1-nano"),
                "embedding_model": os.getenv("EMBEDDING_MODEL", "")
            }
            
    except Exception as e:
        logger.error(f"Error getting provider config sync: {e}")
        return {
            "provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None,
            "chat_model": "gpt-4.1-nano",
            "embedding_model": ""
        }


def get_llm_client_sync():
    """
    Create a synchronous OpenAI-compatible client based on the configured provider.
    
    This is a synchronous wrapper for backward compatibility with ThreadPoolExecutor.
    
    Returns:
        openai.OpenAI: An OpenAI-compatible client configured for the selected provider
    """
    # Get provider configuration using the sync helper
    provider_config = _get_active_provider_sync()
    provider = provider_config["provider"]
    api_key = provider_config["api_key"]
    base_url = provider_config["base_url"]
    
    logger.info(f"Creating sync LLM client for provider: {provider}")
    
    try:
        if provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key not found in credential service")
            return openai.OpenAI(api_key=api_key)
            
        elif provider == "ollama":
            return openai.OpenAI(
                api_key="ollama",  # Required but unused
                base_url=base_url or "http://localhost:11434/v1"
            )
            
        elif provider == "google":
            if not api_key:
                raise ValueError("Google API key not found in credential service")
            return openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
        else:
            # Fallback to OpenAI
            logger.warning(f"Unsupported provider {provider}, falling back to OpenAI")
            fallback_key = os.getenv("OPENAI_API_KEY")
            if not fallback_key:
                raise ValueError("OpenAI API key not found in environment")
            return openai.OpenAI(api_key=fallback_key)
            
    except Exception as e:
        logger.error(f"Error creating sync LLM client: {e}")
        raise


async def get_embedding_model(provider: Optional[str] = None) -> str:
    """
    Get the configured embedding model based on the provider.
    
    Args:
        provider: Override provider selection
    
    Returns:
        str: The embedding model to use
    """
    try:
        # Get provider configuration
        if provider:
            # Explicit provider requested
            provider_name = provider
            # Get custom model from settings if any
            rag_settings = await credential_service.get_credentials_by_category("rag_strategy")
            custom_model = rag_settings.get("EMBEDDING_MODEL", "")
        else:
            # Get configured provider from database
            provider_config = await credential_service.get_active_provider("embedding")
            provider_name = provider_config["provider"]
            custom_model = provider_config["embedding_model"]
        
        # Use custom model if specified
        if custom_model:
            return custom_model
        
        # Return provider-specific defaults
        if provider_name == "openai":
            return "text-embedding-3-small"
        elif provider_name == "ollama":
            # Ollama default embedding model
            return "nomic-embed-text"
        elif provider_name == "google":
            # Google's embedding model
            return "text-embedding-004"
        else:
            # Fallback to OpenAI's model
            return "text-embedding-3-small"
            
    except Exception as e:
        logger.error(f"Error getting embedding model: {e}")
        # Fallback to OpenAI default
        return "text-embedding-3-small"


def get_embedding_model_sync() -> str:
    """
    Get the configured embedding model synchronously.
    
    Returns:
        str: The embedding model to use
    """
    # Get provider configuration using the sync helper
    provider_config = _get_active_provider_sync()
    provider = provider_config["provider"]
    custom_model = provider_config["embedding_model"]
    
    # Check for custom model
    if custom_model:
        return custom_model
    
    # Return provider-specific defaults
    if provider == "openai":
        return "text-embedding-3-small"
    elif provider == "ollama":
        return "nomic-embed-text"
    elif provider == "google":
        return "text-embedding-004"
    else:
        return "text-embedding-3-small"