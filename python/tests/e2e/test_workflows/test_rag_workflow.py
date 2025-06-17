"""End-to-end tests for RAG workflows."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime
import json

from src.services.rag.crawling_service import CrawlingService
from src.services.rag.document_storage_service import DocumentStorageService
from src.services.rag.search_service import SearchService
from src.services.rag.source_management_service import SourceManagementService


class TestRAGIngestionWorkflow:
    """Test complete RAG ingestion workflow."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    @patch('crawl4ai.AsyncWebCrawler')
    @patch('src.utils.get_embedding')
    async def test_url_crawl_and_index(self, mock_embedding, mock_crawler, mock_get_client):
        """Test crawling URL and indexing content."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler.return_value = mock_crawler_instance
        
        # Mock crawl result
        mock_result = Mock()
        mock_result.markdown = """
        # Documentation Title
        
        ## Section 1
        This is the first section with important information.
        
        ## Section 2
        This section contains technical details about the API.
        """
        mock_result.metadata = {"url": "https://example.com/docs"}
        mock_crawler_instance.arun.return_value = mock_result
        
        # Mock embedding generation
        mock_embedding.return_value = [0.1] * 768
        
        # Services
        source_service = SourceManagementService()
        crawl_service = CrawlingService()
        storage_service = DocumentStorageService()
        
        project_id = "proj_123"
        
        # Step 1: Create knowledge source
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "source_123",
            "project_id": project_id,
            "name": "API Documentation",
            "source_type": "url",
            "url": "https://example.com/docs",
            "crawl_status": "pending"
        }]
        
        source = await source_service.create_source({
            "project_id": project_id,
            "name": "API Documentation",
            "source_type": "url",
            "url": "https://example.com/docs"
        })
        
        # Step 2: Crawl the URL
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
            "crawl_status": "in_progress"
        }]
        
        content = await crawl_service.crawl_url(
            "https://example.com/docs",
            wait_for="css:article"
        )
        
        assert "Documentation Title" in content
        
        # Step 3: Chunk and store content
        chunks = await storage_service.chunk_and_store(
            content=content,
            project_id=project_id,
            source_id=source["id"],
            chunk_size=500,
            overlap=50
        )
        
        # Verify chunks were created
        assert len(chunks) > 0
        
        # Step 4: Update source status
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
            "crawl_status": "completed",
            "last_crawled_at": datetime.now().isoformat()
        }]
        
        await source_service.update_crawl_status(
            source["id"],
            "completed",
            metadata={"chunks_created": len(chunks)}
        )
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_document_upload_and_index(self, mock_get_client):
        """Test document upload and indexing workflow."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        storage_service = DocumentStorageService()
        source_service = SourceManagementService()
        
        project_id = "proj_456"
        
        # Step 1: Create file source
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "source_file_123",
            "project_id": project_id,
            "name": "Technical Spec.pdf",
            "source_type": "file",
            "file_path": "/uploads/spec.pdf"
        }]
        
        source = await source_service.create_source({
            "project_id": project_id,
            "name": "Technical Spec.pdf",
            "source_type": "file",
            "file_path": "/uploads/spec.pdf"
        })
        
        # Step 2: Extract text from PDF
        with patch('src.utils.extract_text_from_file') as mock_extract:
            mock_extract.return_value = """
            Technical Specification
            
            1. Overview
            This document describes the system architecture.
            
            2. Components
            The system consists of multiple microservices.
            """
            
            text_content = await storage_service.process_file(
                file_path="/uploads/spec.pdf",
                file_type="pdf"
            )
        
        # Step 3: Store and index
        with patch('src.utils.get_embedding') as mock_embedding:
            mock_embedding.return_value = [0.2] * 768
            
            mock_client.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": f"kb_{i}"} for i in range(5)
            ]
            
            await storage_service.store_document(
                content=text_content,
                project_id=project_id,
                source_id=source["id"],
                metadata={"file_type": "pdf", "file_name": "spec.pdf"}
            )


class TestRAGSearchWorkflow:
    """Test RAG search workflow."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    @patch('src.utils.get_embedding')
    async def test_semantic_search_workflow(self, mock_embedding, mock_get_client):
        """Test complete semantic search workflow."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        search_service = SearchService()
        
        # Mock embedding for query
        mock_embedding.return_value = [0.3] * 768
        
        # Mock search results from vector database
        mock_search_results = [
            {
                "id": "kb_001",
                "content": "The authentication system uses JWT tokens for security.",
                "metadata": {"source": "auth_docs", "page": 5},
                "similarity": 0.95
            },
            {
                "id": "kb_002",
                "content": "JWT tokens expire after 24 hours by default.",
                "metadata": {"source": "auth_docs", "page": 6},
                "similarity": 0.89
            },
            {
                "id": "kb_003",
                "content": "Refresh tokens can be used to obtain new access tokens.",
                "metadata": {"source": "auth_docs", "page": 7},
                "similarity": 0.85
            }
        ]
        
        mock_client.rpc.return_value.execute.return_value.data = mock_search_results
        
        # Perform search
        query = "How does authentication work?"
        results = await search_service.search_with_rerank(
            query=query,
            project_id="proj_123",
            limit=10,
            similarity_threshold=0.7
        )
        
        # Verify results
        assert len(results) > 0
        assert results[0]["similarity"] >= results[1]["similarity"]  # Ordered by relevance
        assert "JWT" in results[0]["content"]
        
        # Verify embedding was generated for query
        mock_embedding.assert_called_with(query)
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_hybrid_search_workflow(self, mock_get_client):
        """Test hybrid search combining vector and keyword search."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        search_service = SearchService()
        
        # Mock vector search results
        vector_results = [
            {"id": "kb_001", "content": "OAuth2 authentication flow", "score": 0.9},
            {"id": "kb_002", "content": "JWT token validation", "score": 0.85}
        ]
        
        # Mock keyword search results
        keyword_results = [
            {"id": "kb_002", "content": "JWT token validation", "score": 0.95},
            {"id": "kb_003", "content": "API authentication methods", "score": 0.8}
        ]
        
        with patch.object(search_service, 'vector_search', return_value=vector_results):
            with patch.object(search_service, 'keyword_search', return_value=keyword_results):
                # Perform hybrid search
                results = await search_service.hybrid_search(
                    query="authentication JWT",
                    project_id="proj_123",
                    vector_weight=0.7,
                    keyword_weight=0.3
                )
        
        # Should combine and rerank results
        assert len(results) == 3  # Union of results
        assert results[0]["id"] == "kb_002"  # High score in both


class TestRAGAgentWorkflow:
    """Test RAG agent interaction workflow."""
    
    @pytest.mark.asyncio
    @patch('src.agents.rag_agent.openai.ChatCompletion.acreate')
    @patch('src.utils.get_supabase_client')
    async def test_rag_agent_conversation(self, mock_get_client, mock_openai):
        """Test RAG agent conversational workflow."""
        from src.agents.rag_agent import RagAgent
        
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock search results
        mock_client.rpc.return_value.execute.return_value.data = [
            {
                "content": "The system supports PostgreSQL and MySQL databases.",
                "metadata": {"source": "tech_docs"}
            },
            {
                "content": "PostgreSQL is recommended for production use.",
                "metadata": {"source": "best_practices"}
            }
        ]
        
        # Mock OpenAI response
        mock_openai.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    content="Based on the documentation, the system supports both PostgreSQL and MySQL databases. PostgreSQL is specifically recommended for production use due to its advanced features and better performance characteristics."
                )
            )]
        )
        
        # Create agent
        agent = RagAgent(
            project_id="proj_123",
            model="gpt-4",
            temperature=0.7
        )
        
        # Ask question
        response = await agent.chat(
            message="What databases are supported?",
            chat_history=[],
            search_kwargs={"limit": 5}
        )
        
        # Verify response
        assert "PostgreSQL" in response.content
        assert "MySQL" in response.content
        assert response.sources is not None
        assert len(response.sources) > 0


class TestRAGBatchProcessing:
    """Test batch processing workflows."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    @patch('crawl4ai.AsyncWebCrawler')
    async def test_batch_url_crawling(self, mock_crawler, mock_get_client):
        """Test batch crawling multiple URLs."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        crawl_service = CrawlingService()
        
        # Mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler.return_value = mock_crawler_instance
        
        # URLs to crawl
        urls = [
            "https://docs.example.com/intro",
            "https://docs.example.com/api",
            "https://docs.example.com/guides"
        ]
        
        # Mock different content for each URL
        mock_results = []
        for i, url in enumerate(urls):
            result = Mock()
            result.markdown = f"# Page {i}\nContent for {url}"
            result.metadata = {"url": url, "title": f"Page {i}"}
            mock_results.append(result)
        
        mock_crawler_instance.arun.side_effect = mock_results
        
        # Batch crawl
        results = await crawl_service.batch_crawl(
            urls=urls,
            project_id="proj_123",
            source_id="source_batch",
            max_concurrent=3
        )
        
        # Verify all URLs were crawled
        assert len(results) == 3
        assert all("success" in r["status"] for r in results)
        
        # Verify concurrent execution
        assert mock_crawler_instance.arun.call_count == 3
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    @patch('src.utils.get_embedding')
    async def test_incremental_indexing(self, mock_embedding, mock_get_client):
        """Test incremental indexing of new content."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        storage_service = DocumentStorageService()
        
        # Mock embedding
        mock_embedding.return_value = [0.4] * 768
        
        # Mock existing content check
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content_hash": "existing_hash_1"},
            {"content_hash": "existing_hash_2"}
        ]
        
        # New content to index
        new_chunks = [
            {"content": "Existing content 1", "hash": "existing_hash_1"},
            {"content": "Existing content 2", "hash": "existing_hash_2"},
            {"content": "New content 1", "hash": "new_hash_1"},
            {"content": "New content 2", "hash": "new_hash_2"}
        ]
        
        # Mock insert for new content only
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "kb_new_1"},
            {"id": "kb_new_2"}
        ]
        
        # Perform incremental indexing
        indexed = await storage_service.incremental_index(
            chunks=new_chunks,
            project_id="proj_123",
            source_id="source_123"
        )
        
        # Should only index new content
        assert indexed == 2
        assert mock_client.table.return_value.insert.call_count == 1
        
        # Verify only new content was processed
        insert_call = mock_client.table.return_value.insert.call_args[0][0]
        assert len(insert_call) == 2
        assert all("new" in chunk["content"] for chunk in insert_call)