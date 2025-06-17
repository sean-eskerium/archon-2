"""Unit tests for CrawlingService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import asyncio

from src.services.rag.crawling_service import CrawlingService
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_called_with_subset,
    async_timeout,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestCrawlingService:
    """Unit tests for CrawlingService with enhanced patterns."""
    
    @pytest.fixture
    def mock_crawler(self):
        """Mock AsyncWebCrawler with common methods."""
        crawler = AsyncMock()
        crawler.arun = AsyncMock()
        crawler.arun_many = AsyncMock()
        return crawler
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def crawling_service(self, mock_crawler, mock_supabase_client):
        """Create CrawlingService instance with mocked dependencies."""
        return CrawlingService(crawler=mock_crawler, supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def make_crawl_result(self):
        """Factory for creating mock crawl results."""
        def _make_result(
            url: str,
            success: bool = True,
            markdown: Optional[str] = None,
            title: Optional[str] = None,
            internal_links: Optional[List[str]] = None,
            external_links: Optional[List[str]] = None,
            error_message: Optional[str] = None
        ):
            result = MagicMock()
            result.success = success
            result.url = url
            result.markdown = markdown or f"# Page Content\n\nContent for {url}"
            result.title = title or f"Page Title - {url}"
            result.error_message = error_message
            
            # Setup links structure
            result.links = {
                "internal": [{"href": link} for link in (internal_links or [])],
                "external": [{"href": link} for link in (external_links or [])]
            }
            
            return result
        return _make_result
    
    # =============================================================================
    # Single Page Crawling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("url,expected_success", [
        pytest.param("https://example.com", True, id="valid-https"),
        pytest.param("http://example.com", True, id="valid-http"),
        pytest.param("https://example.com/page/deep/path", True, id="deep-path"),
        pytest.param("", False, id="empty-url"),
    ])
    async def test_crawl_single_page_various_urls(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        url,
        expected_success
    ):
        """Test crawling single pages with various URL patterns."""
        # Arrange
        if expected_success and url:
            mock_result = make_crawl_result(url=url)
            mock_crawler.arun.return_value = mock_result
        else:
            mock_crawler.arun.side_effect = Exception("Invalid URL")
        
        # Act
        result = await crawling_service.crawl_single_page(url)
        
        # Assert
        assert result["success"] == expected_success
        assert result["url"] == url
        
        if expected_success:
            assert "markdown" in result
            assert "title" in result
            assert result["content_length"] > 0
        else:
            assert "error" in result
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("content_size", [
        pytest.param(100, id="small-content"),
        pytest.param(10000, id="medium-content"),
        pytest.param(100000, id="large-content"),
    ])
    async def test_crawl_various_content_sizes(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        content_size
    ):
        """Test crawling pages with various content sizes."""
        # Arrange
        url = "https://example.com/page"
        content = "# Test Content\n\n" + "Lorem ipsum " * (content_size // 11)
        mock_result = make_crawl_result(url=url, markdown=content)
        mock_crawler.arun.return_value = mock_result
        
        # Act
        result = await crawling_service.crawl_single_page(url)
        
        # Assert
        assert result["success"] is True
        assert result["content_length"] >= content_size
        assert len(result["markdown"]) >= content_size
    
    # =============================================================================
    # Link Extraction Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("internal_count,external_count", [
        pytest.param(0, 0, id="no-links"),
        pytest.param(5, 0, id="internal-only"),
        pytest.param(0, 5, id="external-only"),
        pytest.param(10, 10, id="mixed-links"),
        pytest.param(100, 50, id="many-links"),
    ])
    async def test_link_extraction_patterns(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        internal_count,
        external_count
    ):
        """Test extraction of various link patterns."""
        # Arrange
        url = "https://example.com"
        internal_links = [f"https://example.com/page{i}" for i in range(internal_count)]
        external_links = [f"https://external{i}.com" for i in range(external_count)]
        
        mock_result = make_crawl_result(
            url=url,
            internal_links=internal_links,
            external_links=external_links
        )
        mock_crawler.arun.return_value = mock_result
        
        # Act
        result = await crawling_service.crawl_single_page(url)
        
        # Assert
        assert result["success"] is True
        assert len(result["links"]["internal"]) == internal_count
        assert len(result["links"]["external"]) == external_count
    
    # =============================================================================
    # Batch Crawling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("url_count,max_concurrent,expected_batches", [
        pytest.param(10, 5, 2, id="small-batch"),
        pytest.param(50, 10, 5, id="medium-batch"),
        pytest.param(100, 20, 5, id="large-batch"),
        pytest.param(7, 10, 1, id="single-batch"),
    ])
    async def test_batch_crawling_with_concurrency(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        url_count,
        max_concurrent,
        expected_batches
    ):
        """Test batch crawling with various concurrency limits."""
        # Arrange
        urls = [f"https://example.com/page{i}" for i in range(url_count)]
        
        # Create mock results for all URLs
        def mock_arun_many(batch_urls, **kwargs):
            return [make_crawl_result(url=url) for url in batch_urls]
        
        mock_crawler.arun_many.side_effect = mock_arun_many
        
        # Act
        results = await crawling_service.crawl_batch_with_progress(
            urls=urls,
            max_concurrent=max_concurrent
        )
        
        # Assert
        assert len(results) == url_count
        assert all(r["success"] for r in results)
        assert mock_crawler.arun_many.call_count == expected_batches
    
    # =============================================================================
    # Recursive Crawling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("max_depth,expected_crawled", [
        pytest.param(1, 1, id="depth-1"),
        pytest.param(2, 3, id="depth-2"),  # 1 + 2 children
        pytest.param(3, 7, id="depth-3"),  # 1 + 2 + 4 grandchildren
    ])
    async def test_recursive_crawling_depth_limits(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        max_depth,
        expected_crawled
    ):
        """Test recursive crawling respects depth limits."""
        # Arrange
        start_url = "https://example.com"
        
        # Setup mock to simulate tree structure
        def create_crawl_results(urls):
            results = []
            for url in urls:
                depth = url.count('/') - 2  # Simple depth calculation
                if depth < max_depth:
                    # Each page has 2 child links
                    internal_links = [
                        f"{url}/child1",
                        f"{url}/child2"
                    ]
                else:
                    internal_links = []
                
                results.append(make_crawl_result(
                    url=url,
                    internal_links=internal_links
                ))
            return results
        
        mock_crawler.arun_many.side_effect = create_crawl_results
        
        # Act
        results = await crawling_service.crawl_recursive_with_progress(
            start_urls=[start_url],
            max_depth=max_depth,
            max_concurrent=5
        )
        
        # Assert
        assert len(results) == expected_crawled
    
    # =============================================================================
    # Sitemap Parsing Tests
    # =============================================================================
    
    @pytest.mark.parametrize("sitemap_content,expected_urls", [
        pytest.param(
            b"""<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://example.com/page1</loc></url>
                <url><loc>https://example.com/page2</loc></url>
            </urlset>""",
            ["https://example.com/page1", "https://example.com/page2"],
            id="standard-sitemap"
        ),
        pytest.param(
            b"""<?xml version="1.0" encoding="UTF-8"?>
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
            </sitemapindex>""",
            [],  # Sitemap index not supported in basic implementation
            id="sitemap-index"
        ),
        pytest.param(
            b"Invalid XML content",
            [],
            id="invalid-xml"
        ),
    ])
    @patch('requests.get')
    def test_parse_sitemap_various_formats(
        self,
        mock_get,
        crawling_service,
        sitemap_content,
        expected_urls
    ):
        """Test parsing various sitemap formats."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_content
        mock_get.return_value = mock_response
        
        # Act
        urls = crawling_service.parse_sitemap("https://example.com/sitemap.xml")
        
        # Assert
        assert urls == expected_urls
    
    # =============================================================================
    # Content Type Detection Tests
    # =============================================================================
    
    @pytest.mark.parametrize("url,is_sitemap,is_txt", [
        pytest.param("https://example.com/sitemap.xml", True, False, id="sitemap-xml"),
        pytest.param("https://example.com/sitemap/index.xml", True, False, id="sitemap-index"),
        pytest.param("https://example.com/robots.txt", False, True, id="robots-txt"),
        pytest.param("https://example.com/readme.txt", False, True, id="readme-txt"),
        pytest.param("https://example.com/page.html", False, False, id="html-page"),
        pytest.param("https://example.com/data.json", False, False, id="json-file"),
    ])
    def test_content_type_detection(
        self,
        crawling_service,
        url,
        is_sitemap,
        is_txt
    ):
        """Test detection of various content types from URLs."""
        # Assert
        assert crawling_service.is_sitemap(url) == is_sitemap
        assert crawling_service.is_txt(url) == is_txt
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,error_message", [
        pytest.param(ConnectionError("Network error"), "Network error", id="network-error"),
        pytest.param(TimeoutError("Timeout"), "Timeout", id="timeout-error"),
        pytest.param(ValueError("Invalid URL"), "Invalid URL", id="invalid-url"),
        pytest.param(Exception("Unknown error"), "Unknown error", id="generic-error"),
    ])
    async def test_error_handling_single_page(
        self,
        crawling_service,
        mock_crawler,
        error_type,
        error_message
    ):
        """Test error handling for various crawling failures."""
        # Arrange
        mock_crawler.arun.side_effect = error_type
        
        # Act
        result = await crawling_service.crawl_single_page("https://example.com")
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert error_message in result["error"]
    
    @pytest.mark.asyncio
    async def test_no_crawler_instance_handling(self, mock_supabase_client):
        """Test graceful handling when crawler is not available."""
        # Arrange
        service = CrawlingService(crawler=None, supabase_client=mock_supabase_client)
        
        # Act
        result = await service.crawl_single_page("https://example.com")
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "No crawler instance available"
    
    # =============================================================================
    # Progress Tracking Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_progress_callback_reporting(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result
    ):
        """Test progress callback reporting during crawling."""
        # Arrange
        urls = [f"https://example.com/page{i}" for i in range(5)]
        progress_updates = []
        
        async def progress_callback(phase, percentage, message, **kwargs):
            progress_updates.append({
                "phase": phase,
                "percentage": percentage,
                "message": message,
                "details": kwargs
            })
        
        # Mock crawl results
        mock_crawler.arun_many.return_value = [
            make_crawl_result(url=url) for url in urls
        ]
        
        # Act
        results = await crawling_service.crawl_batch_with_progress(
            urls=urls,
            progress_callback=progress_callback
        )
        
        # Assert
        assert len(results) == 5
        assert len(progress_updates) > 0
        
        # Check progress phases
        phases = [update["phase"] for update in progress_updates]
        assert "crawling" in phases
        
        # Check progress percentages
        percentages = [update["percentage"] for update in progress_updates]
        assert percentages[0] < percentages[-1]  # Progress increases
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.parametrize("url_count", [100, 500, 1000])
    async def test_large_scale_crawling_performance(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        url_count
    ):
        """Test performance with large numbers of URLs."""
        # Arrange
        urls = [f"https://example.com/page{i}" for i in range(url_count)]
        
        # Mock fast responses
        def mock_batch_crawl(batch_urls, **kwargs):
            return [make_crawl_result(url=url) for url in batch_urls]
        
        mock_crawler.arun_many.side_effect = mock_batch_crawl
        
        # Act & Assert
        with measure_time(f"crawl_{url_count}_urls", threshold=5.0):
            results = await crawling_service.crawl_batch_with_progress(
                urls=urls,
                max_concurrent=50
            )
        
        assert len(results) == url_count
        assert all(r["success"] for r in results)
    
    # =============================================================================
    # Redirect Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("redirect_chain", [
        pytest.param(
            ["https://example.com/old", "https://example.com/new"],
            id="single-redirect"
        ),
        pytest.param(
            ["https://example.com/v1", "https://example.com/v2", "https://example.com/current"],
            id="multiple-redirects"
        ),
    ])
    async def test_redirect_handling(
        self,
        crawling_service,
        mock_crawler,
        make_crawl_result,
        redirect_chain
    ):
        """Test handling of URL redirects."""
        # Arrange
        original_url = redirect_chain[0]
        final_url = redirect_chain[-1]
        
        mock_result = make_crawl_result(url=final_url)
        mock_crawler.arun.return_value = mock_result
        
        # Act
        result = await crawling_service.crawl_single_page(original_url)
        
        # Assert
        assert result["success"] is True
        assert result["url"] == original_url  # Preserves original URL
        assert result["markdown"] is not None