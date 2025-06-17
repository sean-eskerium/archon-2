"""Unit tests for RAG Module MCP tools."""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.modules.rag_module import register_rag_tools, get_bool_setting, smart_crawl_url_direct, delete_source_standalone
from mcp.server.fastmcp import FastMCP, Context


class TestRAGModule:
    """Unit tests for RAG module MCP tools."""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP server."""
        return MagicMock(spec=FastMCP)
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context with required services."""
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context.crawler = MagicMock()
        ctx.request_context.lifespan_context.supabase_client = MagicMock()
        ctx.request_context.lifespan_context.reranking_model = None
        return ctx
    
    @pytest.fixture
    def mock_services(self):
        """Mock all RAG service classes."""
        with patch('src.modules.rag_module.CrawlingService') as mock_crawling:
            with patch('src.modules.rag_module.DocumentStorageService') as mock_storage:
                with patch('src.modules.rag_module.SearchService') as mock_search:
                    with patch('src.modules.rag_module.SourceManagementService') as mock_source:
                        yield {
                            'crawling': mock_crawling,
                            'storage': mock_storage,
                            'search': mock_search,
                            'source': mock_source
                        }
    
    @pytest.mark.unit
    def test_register_rag_tools(self, mock_mcp):
        """Test that all RAG tools are registered with MCP."""
        register_rag_tools(mock_mcp)
        
        # Verify tools were registered
        assert mock_mcp.tool.call_count >= 5  # At least 5 RAG tools
    
    @pytest.mark.unit
    @patch('src.modules.rag_module.os.getenv')
    @patch('src.modules.rag_module.credential_service')
    def test_get_bool_setting(self, mock_cred_service, mock_getenv):
        """Test boolean setting retrieval."""
        # Test with credential service
        mock_cred_service._cache = {"USE_AGENTIC_RAG": "true"}
        mock_cred_service._cache_initialized = True
        
        result = get_bool_setting("USE_AGENTIC_RAG")
        assert result is True
        
        # Test with environment variable fallback
        mock_cred_service._cache = {}
        mock_getenv.return_value = "false"
        
        result = get_bool_setting("USE_AGENTIC_RAG")
        assert result is False
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawl_single_page_success(self, mock_context, mock_services):
        """Test successful single page crawling."""
        # Setup mocks
        mock_crawling_service = MagicMock()
        mock_crawling_service.crawl_single_page = AsyncMock(return_value={
            "success": True,
            "markdown": "# Test Page\n\nThis is test content.",
            "title": "Test Page",
            "links": {"internal": [], "external": []}
        })
        mock_services['crawling'].return_value = mock_crawling_service
        
        mock_storage_service = MagicMock()
        mock_storage_service.smart_chunk_markdown.return_value = ["# Test Page\n\nThis is test content."]
        mock_storage_service.extract_section_info.return_value = {
            "headers": ["Test Page"],
            "char_count": 35,
            "word_count": 5
        }
        mock_services['storage'].return_value = mock_storage_service
        
        mock_source_service = MagicMock()
        mock_source_service.create_source_info.return_value = (True, {"source_id": "example.com"})
        mock_services['source'].return_value = mock_source_service
        
        # Mock add_documents_to_supabase
        with patch('src.modules.rag_module.add_documents_to_supabase') as mock_add_docs:
            mock_add_docs.return_value = None
            
            # Register tools and get crawl_single_page function
            mcp = FastMCP()
            register_rag_tools(mcp)
            crawl_single_page = None
            for tool_name, tool_func in mcp._tools.items():
                if 'crawl_single_page' in tool_name:
                    crawl_single_page = tool_func
                    break
            
            # Test crawl
            result = await crawl_single_page(mock_context, "https://example.com/page")
            
            data = json.loads(result)
            assert data["success"] is True
            assert data["chunks_stored"] == 1
            assert data["total_word_count"] == 5
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_smart_crawl_url_sitemap(self, mock_context, mock_services):
        """Test smart crawl with sitemap detection."""
        # Setup progress callback
        mock_context.progress_callback = AsyncMock()
        
        # Setup mocks for sitemap crawl
        mock_crawling_service = MagicMock()
        mock_crawling_service.is_sitemap.return_value = True
        mock_crawling_service.parse_sitemap.return_value = ["https://example.com/page1", "https://example.com/page2"]
        mock_crawling_service.crawl_batch_with_progress = AsyncMock(return_value=[
            {"url": "https://example.com/page1", "markdown": "Page 1 content"},
            {"url": "https://example.com/page2", "markdown": "Page 2 content"}
        ])
        mock_services['crawling'].return_value = mock_crawling_service
        
        mock_storage_service = MagicMock()
        mock_storage_service.smart_chunk_markdown.return_value = ["Content chunk"]
        mock_storage_service.extract_section_info.return_value = {
            "headers": [], "char_count": 10, "word_count": 2
        }
        mock_services['storage'].return_value = mock_storage_service
        
        mock_source_service = MagicMock()
        mock_source_service.create_source_info.return_value = (True, {})
        mock_services['source'].return_value = mock_source_service
        
        # Mock add_documents_to_supabase
        with patch('src.modules.rag_module.add_documents_to_supabase') as mock_add_docs:
            mock_add_docs.return_value = None
            
            result = await smart_crawl_url_direct(
                mock_context,
                "https://example.com/sitemap.xml",
                max_depth=2
            )
            
            data = json.loads(result)
            assert data["success"] is True
            assert data["crawl_type"] == "sitemap"
            assert data["urls_processed"] == 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_perform_rag_query(self, mock_context, mock_services):
        """Test RAG query execution."""
        # Setup mock search service
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (True, {
            "results": [
                {
                    "content": "Test result content",
                    "similarity": 0.95,
                    "metadata": {"source": "example.com"}
                }
            ],
            "query": "test query"
        })
        mock_services['search'].return_value = mock_search_service
        
        # Register tools and get perform_rag_query function
        mcp = FastMCP()
        register_rag_tools(mcp)
        perform_rag_query = None
        for tool_name, tool_func in mcp._tools.items():
            if 'perform_rag_query' in tool_name:
                perform_rag_query = tool_func
                break
        
        # Test query
        result = await perform_rag_query(
            mock_context,
            query="test query",
            match_count=5
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert len(data["results"]) == 1
        assert data["results"][0]["similarity"] == 0.95
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_source_standalone(self, mock_context, mock_services):
        """Test source deletion functionality."""
        # Setup mock
        mock_source_service = MagicMock()
        mock_source_service.delete_source.return_value = (True, {
            "deleted_count": 10,
            "message": "Source deleted successfully"
        })
        mock_services['source'].return_value = mock_source_service
        
        result = await delete_source_standalone(mock_context, "example.com")
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["deleted_count"] == 10
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_code_examples(self, mock_context, mock_services):
        """Test code example search."""
        # Setup mock
        mock_search_service = MagicMock()
        mock_search_service.search_code_examples_service.return_value = (True, {
            "code_examples": [
                {
                    "code_block": "def test():\n    pass",
                    "summary": "Test function",
                    "similarity": 0.9
                }
            ]
        })
        mock_services['search'].return_value = mock_search_service
        
        # Register tools and get search_code_examples function
        mcp = FastMCP()
        register_rag_tools(mcp)
        search_code_examples = None
        for tool_name, tool_func in mcp._tools.items():
            if 'search_code_examples' in tool_name:
                search_code_examples = tool_func
                break
        
        # Test search
        result = await search_code_examples(
            mock_context,
            query="test function",
            match_count=3
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert len(data["code_examples"]) == 1
        assert "def test()" in data["code_examples"][0]["code_block"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_document(self, mock_context, mock_services):
        """Test document upload functionality."""
        # Setup mocks
        mock_storage_service = MagicMock()
        mock_storage_service.smart_chunk_markdown.return_value = ["Document chunk 1", "Document chunk 2"]
        mock_storage_service.extract_section_info.return_value = {
            "headers": ["Header 1"],
            "char_count": 100,
            "word_count": 20
        }
        mock_services['storage'].return_value = mock_storage_service
        
        mock_source_service = MagicMock()
        mock_source_service.create_source_info.return_value = (True, {"source_id": "uploaded_doc"})
        mock_services['source'].return_value = mock_source_service
        
        # Mock add_documents_to_supabase
        with patch('src.modules.rag_module.add_documents_to_supabase') as mock_add_docs:
            mock_add_docs.return_value = None
            
            # Register tools and get upload_document function
            mcp = FastMCP()
            register_rag_tools(mcp)
            upload_document = None
            for tool_name, tool_func in mcp._tools.items():
                if 'upload_document' in tool_name:
                    upload_document = tool_func
                    break
            
            # Test upload
            result = await upload_document(
                mock_context,
                file_content="# Test Document\n\nThis is a test document.",
                filename="test.md",
                knowledge_type="technical",
                tags=["test", "documentation"]
            )
            
            data = json.loads(result)
            assert data["success"] is True
            assert data["chunks_stored"] == 2
            assert data["filename"] == "test.md"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling(self, mock_context, mock_services):
        """Test error handling in RAG tools."""
        # Setup mock to raise exception
        mock_crawling_service = MagicMock()
        mock_crawling_service.crawl_single_page = AsyncMock(side_effect=Exception("Network error"))
        mock_services['crawling'].return_value = mock_crawling_service
        
        # Register tools and get function
        mcp = FastMCP()
        register_rag_tools(mcp)
        crawl_single_page = None
        for tool_name, tool_func in mcp._tools.items():
            if 'crawl_single_page' in tool_name:
                crawl_single_page = tool_func
                break
        
        # Test error handling
        result = await crawl_single_page(mock_context, "https://example.com")
        
        data = json.loads(result)
        assert data["success"] is False
        assert "Network error" in data["error"]