"""
Contextual Embedding Service

Handles generation of contextual embeddings for improved RAG retrieval.
Includes proper rate limiting for OpenAI API calls.
"""
import os
import time
import asyncio
from typing import List, Tuple, Optional
import openai

from ...config.logfire_config import search_logger
from ..threading_service import get_threading_service
from ..llm_provider_service import get_llm_client, get_llm_client_sync


def generate_contextual_embedding(full_document: str, chunk: str, provider: str = None) -> Tuple[str, bool]:
    """
    Generate contextual information for a chunk within a document to improve retrieval.
    
    This synchronous version is kept for ThreadPoolExecutor compatibility.
    Uses a small delay to prevent rate limiting when running in parallel.
    
    Args:
        full_document: The complete document text
        chunk: The specific chunk of text to generate context for
        provider: Optional provider override
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    # Create LLM client using the provider service
    try:
        client = get_llm_client_sync()
    except Exception as e:
        print(f"Error: Failed to create LLM client: {e}")
        return chunk, False
    
    # Get model choice from environment (sync version)
    model_choice = _get_model_choice()
    
    try:
        # Create the prompt for generating contextual information
        # Reduced from 25000 to 5000 to avoid token rate limits
        prompt = f"""<document> 
{full_document[:5000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Call the OpenAI API to generate contextual information
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise contextual information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Extract the generated context
        context = response.choices[0].message.content.strip()
        
        # Combine the context with the original chunk
        contextual_text = f"{context}\n---\n{chunk}"
        
        # No delay needed when using batch processing
        # The batch function handles rate limiting better
        
        return contextual_text, True
    
    except Exception as e:
        error_str = str(e)
        if "rate_limit_exceeded" in error_str:
            print(f"RATE LIMIT HIT in contextual embedding: {error_str[:200]}...")
        else:
            print(f"Error generating contextual embedding: {e}. Using original chunk instead.")
        return chunk, False


async def generate_contextual_embedding_async(full_document: str, chunk: str, provider: str = None) -> Tuple[str, bool]:
    """
    Generate contextual information for a chunk with proper rate limiting.
    
    This async version uses the threading service for rate limiting.
    
    Args:
        full_document: The complete document text
        chunk: The specific chunk of text to generate context for
        provider: Optional provider override
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    # Model choice is a RAG setting, get from credential service
    try:
        from ...services.credential_service import credential_service
        model_choice = await credential_service.get_credential("MODEL_CHOICE", "gpt-4.1-nano")
    except Exception as e:
        # Fallback to environment variable or default
        search_logger.warning(f"Failed to get MODEL_CHOICE from credential service: {e}, using fallback")
        model_choice = os.getenv("MODEL_CHOICE", "gpt-4.1-nano")
    
    search_logger.debug(f"Using MODEL_CHOICE: {model_choice}")
    
    threading_service = get_threading_service()
    
    # Estimate tokens: document preview (5000 chars ≈ 1250 tokens) + chunk + prompt
    estimated_tokens = 1250 + len(chunk.split()) + 100  # Rough estimate
    
    try:
        # Use rate limiting before making the API call
        async with threading_service.rate_limited_operation(estimated_tokens):
            async with get_llm_client(provider=provider) as client:
                prompt = f"""<document> 
{full_document[:5000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

                # Get model from provider configuration
                model = await _get_model_choice_async(provider)
                
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that provides concise contextual information."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                
                context = response.choices[0].message.content.strip()
                contextual_text = f"{context}\n---\n{chunk}"
                
                return contextual_text, True
            
    except Exception as e:
        if "rate_limit_exceeded" in str(e) or "429" in str(e):
            search_logger.warning(f"Rate limit hit in contextual embedding: {e}")
        else:
            search_logger.error(f"Error generating contextual embedding: {e}")
        return chunk, False


def process_chunk_with_context(args):
    """
    Process a single chunk with contextual embedding.
    This function is designed to be used with concurrent.futures.
    
    Args:
        args: Tuple containing (url, content, full_document)
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    url, content, full_document = args
    return generate_contextual_embedding(full_document, content)


async def process_chunk_with_context_async(url: str, content: str, full_document: str) -> Tuple[str, bool]:
    """
    Process a single chunk with contextual embedding using async/await.
    
    Args:
        url: URL of the document
        content: The chunk content
        full_document: The complete document text
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    return await generate_contextual_embedding_async(full_document, content)

async def _get_model_choice_async(provider: Optional[str] = None) -> str:
    """Get model choice from credential service."""
    from ..credential_service import credential_service
    
    # Get the active provider configuration
    provider_config = await credential_service.get_active_provider("llm")
    model = provider_config.get("chat_model", "gpt-4.1-nano")
    
    search_logger.debug(f"Using model from credential service: {model}")
    
    return model
  
def _get_model_choice() -> str:
    """Get MODEL_CHOICE from credential service."""
    try:
        # Import here to avoid circular dependency
        from ...services.credential_service import credential_service
        # Use asyncio to run the async credential lookup
        import asyncio
        
        # Try to get the current event loop, or create one if none exists
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't use run_until_complete
                # Fall back to environment variable or default
                model = os.getenv("MODEL_CHOICE", "gpt-4.1-nano")
            else:
                model = loop.run_until_complete(credential_service.get_credential("MODEL_CHOICE", "gpt-4.1-nano"))
        except RuntimeError:
            # No event loop exists, create one
            model = asyncio.run(credential_service.get_credential("MODEL_CHOICE", "gpt-4.1-nano"))
            
    except Exception as e:
        # Fallback to environment variable or default if credential service fails
        search_logger.warning(f"Failed to get MODEL_CHOICE from credential service: {e}, using fallback")
        model = os.getenv("MODEL_CHOICE", "gpt-4.1-nano")
    
    search_logger.debug(f"Using MODEL_CHOICE: {model}")

    return model


def _get_model_choice() -> str:
    """Get model choice from credential service using proper methods (sync version)."""
    try:
        # Import the sync helper from llm_provider_service
        from ..llm_provider_service import _get_active_provider_sync
        
        provider_config = _get_active_provider_sync()
        model = provider_config["chat_model"]
        provider = provider_config["provider"]
        
        search_logger.debug(f"Using model from provider config: {model} with provider: {provider}")
        return model
    except Exception as e:
        search_logger.warning(f"Error getting provider config: {e}, using default")
        return "gpt-4.1-nano"


def generate_contextual_embeddings_batch(full_documents: List[str], chunks: List[str], provider: str = None) -> List[Tuple[str, bool]]:
    """
    Generate contextual information for multiple chunks in a single API call to avoid rate limiting.
    
    This processes ALL chunks passed to it in a single API call.
    The caller should batch appropriately (e.g., 10 chunks at a time).
    
    Args:
        full_documents: List of complete document texts
        chunks: List of specific chunks to generate context for
        provider: Optional provider override
        
    Returns:
        List of tuples containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    # Create LLM client using the provider service
    try:
        client = get_llm_client_sync()
    except Exception as e:
        print(f"Error: Failed to create LLM client: {e}")
        return [(chunk, False) for chunk in chunks]
    
    # Get model choice from credential service (RAG setting)
    model_choice = _get_model_choice()
    
    try:
        # Build batch prompt for ALL chunks at once
        batch_prompt = "Process the following chunks and provide contextual information for each:\n\n"
        
        for i, (doc, chunk) in enumerate(zip(full_documents, chunks)):
            # Use only 2000 chars of document context to save tokens
            doc_preview = doc[:2000] if len(doc) > 2000 else doc
            batch_prompt += f"CHUNK {i+1}:\n"
            batch_prompt += f"<document_preview>\n{doc_preview}\n</document_preview>\n"
            batch_prompt += f"<chunk>\n{chunk[:500]}\n</chunk>\n\n"  # Limit chunk preview
        
        batch_prompt += "For each chunk, provide a short succinct context to situate it within the overall document for improving search retrieval. Format your response as:\nCHUNK 1: [context]\nCHUNK 2: [context]\netc."
        
        # Make single API call for ALL chunks
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates contextual information for document chunks."},
                {"role": "user", "content": batch_prompt}
            ],
            temperature=0,
            max_tokens=100 * len(chunks)  # Limit response size
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        
        # Extract contexts from response
        lines = response_text.strip().split('\n')
        chunk_contexts = {}
        
        for line in lines:
            if line.strip().startswith("CHUNK"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    chunk_num = int(parts[0].strip().split()[1]) - 1
                    context = parts[1].strip()
                    chunk_contexts[chunk_num] = context
        
        # Build results
        results = []
        for i, chunk in enumerate(chunks):
            if i in chunk_contexts:
                # Combine context with full chunk (not truncated)
                contextual_text = chunk_contexts[i] + "\n\n" + chunk
                results.append((contextual_text, True))
            else:
                results.append((chunk, False))
                
    except openai.RateLimitError as e:
        if "insufficient_quota" in str(e):
            search_logger.warning(f"⚠️ QUOTA EXHAUSTED in contextual embeddings: {e}")
            print(f"⚠️ OpenAI quota exhausted - proceeding without contextual embeddings")
        else:
            search_logger.warning(f"Rate limit hit in contextual embeddings batch: {e}")
            print(f"Rate limit hit - proceeding without contextual embeddings for this batch")
        # Return non-contextual for all chunks
        results = [(chunk, False) for chunk in chunks]
        
    except Exception as e:
        print(f"Error in contextual embedding batch: {e}")
        # Return non-contextual for all chunks
        results = [(chunk, False) for chunk in chunks]
    
    return results