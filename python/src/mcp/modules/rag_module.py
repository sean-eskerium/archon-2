"""
RAG Module for Archon MCP Server (HTTP-based version)

This module provides tools for:
- RAG query and search
- Source management
- Code example extraction and search

This version uses HTTP calls to the server service instead of importing
service modules directly, enabling true microservices architecture.
"""

from mcp.server.fastmcp import FastMCP, Context
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import json
import logging
import os
from datetime import datetime
import httpx

# Import service discovery for HTTP communication
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)


def get_setting(key: str, default: str = "false") -> str:
    """Get a setting from environment variable."""
    return os.getenv(key, default)


def get_bool_setting(key: str, default: bool = False) -> bool:
    """Get a boolean setting from environment variable."""
    value = get_setting(key, "false" if not default else "true")
    return value.lower() in ("true", "1", "yes", "on")


def register_rag_tools(mcp: FastMCP):
    """Register all RAG tools with the MCP server."""
    
    @mcp.tool()
    async def get_available_sources(ctx: Context) -> str:
        """
        Get list of available sources in the knowledge base.
        
        This tool uses HTTP call to the API service.
        
        Returns:
            JSON string with list of sources
        """
        try:
            api_url = get_api_url()
            timeout = httpx.Timeout(30.0, connect=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(urljoin(api_url, "/api/rag/sources"))
                
                if response.status_code == 200:
                    result = response.json()
                    sources = result.get("sources", [])
                    
                    return json.dumps({
                        "success": True,
                        "sources": sources,
                        "count": len(sources)
                    }, indent=2)
                else:
                    error_detail = response.text
                    return json.dumps({
                        "success": False,
                        "error": f"HTTP {response.status_code}: {error_detail}"
                    }, indent=2)
                    
        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
    
    @mcp.tool()
    async def perform_rag_query(ctx: Context, query: str, source: str = None, match_count: int = 5) -> str:
        """
        Perform a RAG (Retrieval Augmented Generation) query on stored content.
        
        This tool searches the vector database for content relevant to the query and returns
        the matching documents. Optionally filter by source domain.
        Get the source by using the get_available_sources tool before calling this search!
        
        Args:
            query: The search query
            source: Optional source domain to filter results (e.g., 'example.com')
            match_count: Maximum number of results to return (default: 5)
        
        Returns:
            JSON string with search results
        """
        try:
            api_url = get_api_url()
            timeout = httpx.Timeout(30.0, connect=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                request_data = {
                    "query": query,
                    "match_count": match_count
                }
                if source:
                    request_data["source"] = source
                
                response = await client.post(
                    urljoin(api_url, "/api/rag/query"),
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return json.dumps({
                        "success": True,
                        "results": result.get("results", []),
                        "reranked": result.get("reranked", False),
                        "error": None
                    }, indent=2)
                else:
                    error_detail = response.text
                    return json.dumps({
                        "success": False,
                        "results": [],
                        "error": f"HTTP {response.status_code}: {error_detail}"
                    }, indent=2)
                    
        except Exception as e:
            logger.error(f"Error performing RAG query: {e}")
            return json.dumps({
                "success": False,
                "results": [],
                "error": str(e)
            }, indent=2)
    
    @mcp.tool()
    async def search_code_examples(ctx: Context, query: str, source_id: str = None, match_count: int = 5) -> str:
        """
        Search for code examples relevant to the query.
        
        This tool searches the vector database for code examples relevant to the query and returns
        the matching examples with their summaries. Optionally filter by source_id.
        Get the source_id by using the get_available_sources tool before calling this search!

        Use the get_available_sources tool first to see what sources are available for filtering.
        
        Args:
            query: The search query
            source_id: Optional source ID to filter results (e.g., 'example.com')
            match_count: Maximum number of results to return (default: 5)
        
        Returns:
            JSON string with search results
        """
        try:
            api_url = get_api_url()
            timeout = httpx.Timeout(30.0, connect=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                request_data = {
                    "query": query,
                    "match_count": match_count
                }
                if source_id:
                    request_data["source"] = source_id
                
                # Call the dedicated code examples endpoint
                response = await client.post(
                    urljoin(api_url, "/api/rag/code-examples"),
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return json.dumps({
                        "success": True,
                        "results": result.get("results", []),
                        "reranked": result.get("reranked", False),
                        "error": None
                    }, indent=2)
                else:
                    error_detail = response.text
                    return json.dumps({
                        "success": False,
                        "results": [],
                        "error": f"HTTP {response.status_code}: {error_detail}"
                    }, indent=2)
                    
        except Exception as e:
            logger.error(f"Error searching code examples: {e}")
            return json.dumps({
                "success": False,
                "results": [],
                "error": str(e)
            }, indent=2)
    

    # Log successful registration
    logger.info("✓ RAG tools registered (HTTP-based version)")