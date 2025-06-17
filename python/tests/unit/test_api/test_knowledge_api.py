"""Unit tests for Knowledge API endpoints with enhanced patterns."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

from src.api.knowledge_api import router
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import assert_fields_equal, measure_time


@pytest.mark.unit
@pytest.mark.standard
class TestKnowledgeAPI:
    """Unit tests for Knowledge API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        client = MagicMock()
        # Setup default chain behavior
        client.table.return_value.select.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return client
    
    @pytest.fixture
    def make_crawled_page(self):
        """Factory for creating crawled page data."""
        def _make_page(
            page_id: Optional[str] = None,
            url: str = "https://example.com",
            title: str = "Example Page",
            content: str = "Page content here",
            project_id: Optional[str] = None,
            status: str = "completed",
            metadata: Optional[Dict] = None
        ) -> Dict:
            return {
                "id": page_id or f"page-{uuid.uuid4().hex[:8]}",
                "url": url,
                "title": title,
                "content": content,
                "project_id": project_id,
                "status": status,
                "metadata": metadata or {
                    "crawl_depth": 1,
                    "word_count": len(content.split()),
                    "links_found": 5
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        return _make_page
    
    @pytest.fixture
    def make_document_chunk(self):
        """Factory for creating document chunks."""
        def _make_chunk(
            chunk_id: Optional[str] = None,
            page_id: str = "page-123",
            content: str = "Chunk content",
            chunk_index: int = 0,
            embedding: Optional[List[float]] = None
        ) -> Dict:
            return {
                "id": chunk_id or f"chunk-{uuid.uuid4().hex[:8]}",
                "page_id": page_id,
                "content": content,
                "chunk_index": chunk_index,
                "embedding": embedding or [0.1] * 1536,  # Mock embedding
                "metadata": {
                    "start_char": chunk_index * 1000,
                    "end_char": (chunk_index + 1) * 1000
                },
                "created_at": datetime.utcnow().isoformat()
            }
        return _make_chunk
    
    # =============================================================================
    # Crawled Pages Tests
    # =============================================================================
    
    @pytest.mark.parametrize("page_count,page_size,expected_pages", [
        pytest.param(0, 10, 0, id="no-pages"),
        pytest.param(5, 10, 5, id="less-than-page"),
        pytest.param(10, 10, 10, id="full-page"),
        pytest.param(25, 10, 10, id="more-than-page"),
    ])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_list_crawled_pages_pagination(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_crawled_page,
        page_count,
        page_size,
        expected_pages
    ):
        """Test listing crawled pages with pagination."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        pages = [make_crawled_page(title=f"Page {i+1}") for i in range(page_count)]
        limited_pages = pages[:expected_pages]
        
        mock_supabase_client.table.return_value.select.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value = MagicMock(
            data=limited_pages
        )
        
        # Act
        response = test_client.get(f"/api/knowledge/pages?page=1&page_size={page_size}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["pages"]) == expected_pages
        assert result["total"] == page_count
        assert result["page"] == 1
        assert result["page_size"] == page_size
    
    @pytest.mark.parametrize("filter_params", [
        pytest.param({"project_id": "proj-123"}, id="by-project"),
        pytest.param({"status": "completed"}, id="by-status"),
        pytest.param({"search": "example"}, id="by-search"),
        pytest.param(
            {"project_id": "proj-123", "status": "completed"},
            id="multiple-filters"
        ),
    ])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_list_crawled_pages_filtering(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_crawled_page,
        filter_params
    ):
        """Test filtering crawled pages."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        # Create pages matching filters
        filtered_pages = []
        for i in range(3):
            page = make_crawled_page(
                title=f"Page {i+1}",
                project_id=filter_params.get("project_id"),
                status=filter_params.get("status", "completed")
            )
            if "search" in filter_params:
                page["title"] = f"Example Page {i+1}"
            filtered_pages.append(page)
        
        # Setup mock to return filtered results
        mock_query = mock_supabase_client.table.return_value.select.return_value
        
        if "project_id" in filter_params:
            mock_query = mock_query.eq.return_value
        if "status" in filter_params:
            mock_query = mock_query.eq.return_value
        if "search" in filter_params:
            mock_query = mock_query.ilike.return_value
        
        mock_query.order.return_value.limit.return_value.offset.return_value.execute.return_value = MagicMock(
            data=filtered_pages
        )
        
        # Act
        query_string = "&".join(f"{k}={v}" for k, v in filter_params.items())
        response = test_client.get(f"/api/knowledge/pages?{query_string}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["pages"]) == 3
    
    # =============================================================================
    # Crawling Operations Tests
    # =============================================================================
    
    @pytest.mark.parametrize("crawl_request,expected_status", [
        pytest.param(
            {"url": "https://example.com", "project_id": "proj-123"},
            202,
            id="valid-single-url"
        ),
        pytest.param(
            {
                "urls": ["https://example.com", "https://test.com"],
                "project_id": "proj-123"
            },
            202,
            id="valid-multiple-urls"
        ),
        pytest.param(
            {"url": "invalid-url", "project_id": "proj-123"},
            422,
            id="invalid-url"
        ),
        pytest.param(
            {"url": "https://example.com"},  # Missing project_id
            422,
            id="missing-project-id"
        ),
    ])
    @patch('src.api.knowledge_api.crawling_service')
    def test_start_crawling(
        self,
        mock_crawling_service,
        test_client,
        crawl_request,
        expected_status
    ):
        """Test starting crawl operations."""
        # Arrange
        if expected_status == 202:
            mock_crawling_service.crawl_url = AsyncMock(return_value={"id": "crawl-123"})
            mock_crawling_service.crawl_urls_batch = AsyncMock(
                return_value=[{"id": f"crawl-{i}"} for i in range(len(crawl_request.get("urls", [])))]
            )
        
        # Act
        response = test_client.post("/api/knowledge/crawl", json=crawl_request)
        
        # Assert
        assert response.status_code == expected_status
        
        if expected_status == 202:
            result = response.json()
            assert "crawl_id" in result or "crawl_ids" in result
            assert result["status"] == "started"
    
    @pytest.mark.parametrize("crawl_status", [
        pytest.param("pending", id="pending-crawl"),
        pytest.param("running", id="running-crawl"),
        pytest.param("completed", id="completed-crawl"),
        pytest.param("failed", id="failed-crawl"),
    ])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_get_crawl_status(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_crawled_page,
        crawl_status
    ):
        """Test getting crawl status."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        crawl_id = "crawl-123"
        
        page = make_crawled_page(page_id=crawl_id, status=crawl_status)
        if crawl_status == "failed":
            page["metadata"]["error"] = "Connection timeout"
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[page]
        )
        
        # Act
        response = test_client.get(f"/api/knowledge/crawl/{crawl_id}/status")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == crawl_status
        assert result["crawl_id"] == crawl_id
        
        if crawl_status == "failed":
            assert "error" in result
    
    # =============================================================================
    # Document Chunks Tests
    # =============================================================================
    
    @pytest.mark.parametrize("chunk_count", [0, 5, 20])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_get_page_chunks(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_document_chunk,
        chunk_count
    ):
        """Test getting chunks for a specific page."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        page_id = "page-123"
        
        chunks = [
            make_document_chunk(page_id=page_id, chunk_index=i)
            for i in range(chunk_count)
        ]
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=chunks
        )
        
        # Act
        response = test_client.get(f"/api/knowledge/pages/{page_id}/chunks")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["chunks"]) == chunk_count
        
        # Verify chunks are ordered by index
        for i, chunk in enumerate(result["chunks"]):
            assert chunk["chunk_index"] == i
    
    # =============================================================================
    # Search Tests
    # =============================================================================
    
    @pytest.mark.parametrize("search_params", [
        pytest.param(
            {"query": "test query", "limit": 10},
            id="basic-search"
        ),
        pytest.param(
            {"query": "test", "project_id": "proj-123", "limit": 5},
            id="project-scoped-search"
        ),
        pytest.param(
            {"query": "test", "threshold": 0.8, "limit": 20},
            id="high-threshold-search"
        ),
    ])
    @patch('src.api.knowledge_api.search_service')
    def test_semantic_search(
        self,
        mock_search_service,
        test_client,
        search_params
    ):
        """Test semantic search functionality."""
        # Arrange
        mock_results = [
            {
                "id": f"result-{i}",
                "content": f"Result content {i}",
                "score": 0.9 - (i * 0.1),
                "metadata": {"page_id": f"page-{i}"}
            }
            for i in range(min(search_params.get("limit", 10), 5))
        ]
        
        mock_search_service.search = AsyncMock(return_value=mock_results)
        
        # Act
        response = test_client.post("/api/knowledge/search", json=search_params)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert len(result["results"]) <= search_params.get("limit", 10)
        
        # Verify results are ordered by score
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)
    
    # =============================================================================
    # Reindexing Tests
    # =============================================================================
    
    @patch('src.api.knowledge_api.document_storage_service')
    def test_reindex_page(
        self,
        mock_storage_service,
        test_client
    ):
        """Test reindexing a specific page."""
        # Arrange
        page_id = "page-to-reindex"
        mock_storage_service.reindex_page = AsyncMock(return_value={"chunks_created": 10})
        
        # Act
        response = test_client.post(f"/api/knowledge/pages/{page_id}/reindex")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["chunks_created"] == 10
        mock_storage_service.reindex_page.assert_called_once_with(page_id)
    
    @patch('src.api.knowledge_api.document_storage_service')
    def test_reindex_project(
        self,
        mock_storage_service,
        test_client
    ):
        """Test reindexing all pages in a project."""
        # Arrange
        project_id = "proj-123"
        mock_storage_service.reindex_project = AsyncMock(
            return_value={"pages_reindexed": 15, "total_chunks": 150}
        )
        
        # Act
        response = test_client.post(f"/api/knowledge/projects/{project_id}/reindex")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["pages_reindexed"] == 15
        assert result["total_chunks"] == 150
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario", [
        pytest.param("page_not_found", id="404-page"),
        pytest.param("crawl_service_error", id="crawl-error"),
        pytest.param("search_service_error", id="search-error"),
        pytest.param("database_error", id="db-error"),
    ])
    @patch('src.api.knowledge_api.get_supabase_client')
    @patch('src.api.knowledge_api.crawling_service')
    @patch('src.api.knowledge_api.search_service')
    def test_error_handling(
        self,
        mock_search_service,
        mock_crawling_service,
        mock_get_client,
        test_client,
        mock_supabase_client,
        error_scenario
    ):
        """Test error handling for various scenarios."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        if error_scenario == "page_not_found":
            mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            response = test_client.get("/api/knowledge/pages/nonexistent")
            expected_status = 404
            
        elif error_scenario == "crawl_service_error":
            mock_crawling_service.crawl_url = AsyncMock(
                side_effect=Exception("Crawling service unavailable")
            )
            response = test_client.post("/api/knowledge/crawl", json={
                "url": "https://example.com",
                "project_id": "proj-123"
            })
            expected_status = 500
            
        elif error_scenario == "search_service_error":
            mock_search_service.search = AsyncMock(
                side_effect=Exception("Search index corrupted")
            )
            response = test_client.post("/api/knowledge/search", json={
                "query": "test"
            })
            expected_status = 500
            
        elif error_scenario == "database_error":
            mock_supabase_client.table.side_effect = Exception("Database connection failed")
            response = test_client.get("/api/knowledge/pages")
            expected_status = 500
        
        # Assert
        assert response.status_code == expected_status
        assert "error" in response.json() or "detail" in response.json()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_pages", [100, 500, 1000])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_list_pages_performance(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        make_crawled_page,
        num_pages
    ):
        """Test performance of listing large numbers of pages."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        # Create pages but return only first 100 (pagination)
        pages = [make_crawled_page(title=f"Page {i}") for i in range(min(num_pages, 100))]
        
        mock_supabase_client.table.return_value.select.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value = MagicMock(
            data=pages
        )
        
        # Act & Assert
        with measure_time(f"list_{num_pages}_pages", threshold=0.5):
            response = test_client.get("/api/knowledge/pages?page_size=100")
        
        assert response.status_code == 200
        assert len(response.json()["pages"]) == min(num_pages, 100)
    
    # =============================================================================
    # Batch Operations Tests
    # =============================================================================
    
    @pytest.mark.parametrize("batch_size", [1, 5, 10, 20])
    @patch('src.api.knowledge_api.crawling_service')
    def test_batch_crawl_urls(
        self,
        mock_crawling_service,
        test_client,
        batch_size
    ):
        """Test batch crawling multiple URLs."""
        # Arrange
        urls = [f"https://example{i}.com" for i in range(batch_size)]
        crawl_results = [
            {"id": f"crawl-{i}", "url": url, "status": "started"}
            for i, url in enumerate(urls)
        ]
        
        mock_crawling_service.crawl_urls_batch = AsyncMock(return_value=crawl_results)
        
        # Act
        response = test_client.post("/api/knowledge/crawl/batch", json={
            "urls": urls,
            "project_id": "proj-123"
        })
        
        # Assert
        assert response.status_code == 202
        result = response.json()
        assert len(result["crawl_jobs"]) == batch_size
        assert all(job["status"] == "started" for job in result["crawl_jobs"])
    
    @pytest.mark.parametrize("page_ids", [
        ["page-1"],
        ["page-1", "page-2", "page-3"],
        [f"page-{i}" for i in range(10)],
    ])
    @patch('src.api.knowledge_api.get_supabase_client')
    def test_batch_delete_pages(
        self,
        mock_get_client,
        test_client,
        mock_supabase_client,
        page_ids
    ):
        """Test batch deletion of pages."""
        # Arrange
        mock_get_client.return_value = mock_supabase_client
        
        # Mock successful deletion
        mock_supabase_client.table.return_value.delete.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[{"id": pid} for pid in page_ids]
        )
        
        # Act
        response = test_client.delete("/api/knowledge/pages/batch", json={"page_ids": page_ids})
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["deleted_count"] == len(page_ids)
        assert result["success"] is True