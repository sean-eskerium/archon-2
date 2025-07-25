"""
Vector Search Service

Handles vector similarity search for documents and code examples.
"""
import os
from typing import List, Dict, Any, Optional
from supabase import Client

from ...config.logfire_config import safe_span, get_logger

logger = get_logger(__name__)
from ..embeddings.embedding_service import create_embedding, create_embedding_async

# Fixed similarity threshold for RAG queries
# Could make this configurable in the future, but that is unnecessary for now
SIMILARITY_THRESHOLD = 0.15




def search_documents(
    client: Client,
    query: str,
    match_count: int = 5,
    filter_metadata: Optional[dict] = None,
    use_hybrid_search: bool = False,
    cached_api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for documents in the database using semantic search.
    
    Args:
        client: Supabase client
        query: Search query string
        match_count: Number of results to return
        filter_metadata: Optional metadata filter dict
        use_hybrid_search: Whether to use hybrid keyword + semantic search
        cached_api_key: Cached OpenAI API key for embeddings (deprecated)
    
    Returns:
        List of matching documents
    """
    with safe_span("vector_search", 
                           query_length=len(query),
                           match_count=match_count,
                           has_filter=filter_metadata is not None) as span:
        try:
            logger.info(f"Document search started - query: {query[:100]}{'...' if len(query) > 100 else ''}, match_count: {match_count}, filter: {filter_metadata}")
            
            # Create embedding for the query
            with safe_span("create_embedding"):
                query_embedding = create_embedding(query)
                
                if not query_embedding:
                    logger.error("Failed to create embedding for query")
                    return []
                
                span.set_attribute("embedding_dimensions", len(query_embedding))
            
            # Build the filter for the RPC call
            with safe_span("prepare_rpc_params"):
                rpc_params = {
                    "query_embedding": query_embedding,
                    "match_count": match_count
                }
                
                # Add filter to RPC params if provided
                if filter_metadata:
                    logger.debug(f"Adding filter to RPC params: {filter_metadata}")
                    
                    # Check if we have a source filter specifically
                    if "source" in filter_metadata:
                        # Use the version with source_filter parameter
                        rpc_params["source_filter"] = filter_metadata["source"]
                        # Also add the general filter as empty jsonb to satisfy the function signature
                        rpc_params["filter"] = {}
                    else:
                        # Use the general filter parameter
                        rpc_params["filter"] = filter_metadata
                    
                    span.set_attribute("filter_applied", True)
                    span.set_attribute("filter_keys", list(filter_metadata.keys()) if filter_metadata else [])
                else:
                    # No filter provided - use empty jsonb for filter parameter
                    rpc_params["filter"] = {}
            
            # Call the RPC function
            with safe_span("supabase_rpc_call"):
                logger.debug(f"Calling Supabase RPC function: match_crawled_pages, params: {list(rpc_params.keys())}")
                
                response = client.rpc("match_crawled_pages", rpc_params).execute()
                
                # Apply threshold filtering to results
                filtered_results = []
                if response.data:
                    for result in response.data:
                        similarity = result.get("similarity", 0.0)
                        if similarity >= SIMILARITY_THRESHOLD:
                            filtered_results.append(result)
                
                span.set_attribute("rpc_success", True)
                span.set_attribute("raw_results_count", len(response.data) if response.data else 0)
                span.set_attribute("filtered_results_count", len(filtered_results))
                span.set_attribute("threshold_used", SIMILARITY_THRESHOLD)
            
            results_count = len(filtered_results)
            
            span.set_attribute("success", True)
            span.set_attribute("final_results_count", results_count)
            
            # Enhanced logging for debugging
            if results_count == 0:
                logger.warning(f"Document search returned 0 results - query: {query[:100]}{'...' if len(query) > 100 else ''}, raw_count: {len(response.data) if response.data else 0}, filter: {filter_metadata}")
            else:
                logger.info(f"Document search completed - query: {query[:100]}{'...' if len(query) > 100 else ''}, results: {results_count}, raw_count: {len(response.data) if response.data else 0}")
            
            return filtered_results
        
        except Exception as e:
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            
            logger.error(f"Document search failed - query: {query[:100]}{'...' if len(query) > 100 else ''}, error: {e} ({type(e).__name__})")
            
            # Return empty list on error
            return []


async def search_documents_async(
    client: Client,
    query: str,
    match_count: int = 5,
    filter_metadata: Optional[dict] = None,
    use_hybrid_search: bool = False,
    cached_api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Async version of search_documents that properly awaits embedding creation.
    
    Args:
        client: Supabase client
        query: Search query string
        match_count: Number of results to return
        filter_metadata: Optional metadata filter dict
        use_hybrid_search: Whether to use hybrid keyword + semantic search
        cached_api_key: Cached OpenAI API key for embeddings (deprecated)
    
    Returns:
        List of matching documents
    """
    with safe_span("vector_search_async", 
                           query_length=len(query),
                           match_count=match_count,
                           has_filter=filter_metadata is not None) as span:
        try:
            logger.info(f"Document search started (async) - query: {query[:100]}{'...' if len(query) > 100 else ''}, match_count: {match_count}, filter: {filter_metadata}")
            
            # Create embedding for the query - using async version
            with safe_span("create_embedding_async"):
                query_embedding = await create_embedding_async(query)
                
                if not query_embedding:
                    logger.error("Failed to create embedding for query")
                    return []
                
                span.set_attribute("embedding_dimensions", len(query_embedding))
            
            # Build the filter for the RPC call
            with safe_span("prepare_rpc_params"):
                rpc_params = {
                    "query_embedding": query_embedding,
                    "match_count": match_count
                }
                
                # Add filter to RPC params if provided
                if filter_metadata:
                    logger.debug(f"Adding filter to RPC params: {filter_metadata}")
                    
                    # Check if we have a source filter specifically
                    if "source" in filter_metadata:
                        # Use the version with source_filter parameter
                        rpc_params["source_filter"] = filter_metadata["source"]
                        # Also add the general filter as empty jsonb to satisfy the function signature
                        rpc_params["filter"] = {}
                    else:
                        # Use the general filter parameter
                        rpc_params["filter"] = filter_metadata
                    
                    span.set_attribute("filter_applied", True)
                    span.set_attribute("filter_keys", list(filter_metadata.keys()) if filter_metadata else [])
                else:
                    # No filter provided - use empty jsonb for filter parameter
                    rpc_params["filter"] = {}
            
            # Call the RPC function
            with safe_span("supabase_rpc_call"):
                logger.debug(f"Calling Supabase RPC function: match_crawled_pages, params: {list(rpc_params.keys())}")
                
                response = client.rpc("match_crawled_pages", rpc_params).execute()
                
                # Apply threshold filtering to results
                filtered_results = []
                if response.data:
                    for result in response.data:
                        similarity = result.get("similarity", 0.0)
                        if similarity >= SIMILARITY_THRESHOLD:
                            filtered_results.append(result)
                
                span.set_attribute("rpc_success", True)
                span.set_attribute("raw_results_count", len(response.data) if response.data else 0)
                span.set_attribute("filtered_results_count", len(filtered_results))
           
            results_count = len(filtered_results)
            
            span.set_attribute("success", True)
            span.set_attribute("final_results_count", results_count)
            
            logger.info(f"Document search completed (async) - query: {query[:100]}{'...' if len(query) > 100 else ''}, results: {results_count}")
            
            return filtered_results
        
        except Exception as e:
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            
            logger.error(f"Document search failed (async) - query: {query[:100]}{'...' if len(query) > 100 else ''}, error: {e} ({type(e).__name__})")
            
            # Return empty list on error
            return []


def search_code_examples(
    client: Client, 
    query: str, 
    match_count: int = 10, 
    filter_metadata: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for code examples in Supabase using vector similarity.
    
    Args:
        client: Supabase client
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_id: Optional source ID to filter results
        
    Returns:
        List of matching code examples
    """
    # Create a more descriptive query for better embedding match
    # Since code examples are embedded with their summaries, we should make the query more descriptive
    enhanced_query = f"Code example for {query}\n\nSummary: Example code showing {query}"
    
    # Create embedding for the enhanced query
    query_embedding = create_embedding(enhanced_query)
    
    # Execute the search using the match_code_examples function
    try:
        # Only include filter parameter if filter_metadata is provided and not empty
        params = {
            'query_embedding': query_embedding,
            'match_count': match_count
        }
        
        # Only add the filter if it's actually provided and not empty
        if filter_metadata:
            params['filter'] = filter_metadata
            
        # Add source filter if provided
        if source_id:
            params['source_filter'] = source_id
        
        result = client.rpc('match_code_examples', params).execute()
        
        return result.data
    except Exception as e:
        logger.error(f"Error searching code examples: {e}")
        return []