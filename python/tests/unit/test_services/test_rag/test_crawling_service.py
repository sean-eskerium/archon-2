"""Unit tests for CrawlingService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import xml.etree.ElementTree as ET
from src.services.rag.crawling_service import CrawlingService


class TestCrawlingService:
    """Unit tests for CrawlingService."""
    
    @pytest.fixture
    def mock_crawler(self):
        """Mock AsyncWebCrawler."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def crawling_service(self, mock_crawler, mock_supabase_client):
        """Create CrawlingService instance with mocked dependencies."""
        return CrawlingService(crawler=mock_crawler, supabase_client=mock_supabase_client)
    
    @pytest.fixture
    def mock_crawl_result(self):
        """Mock successful crawl result."""
        result = MagicMock()
        result.success = True
        result.markdown = "# Test Page\n\nThis is test content."
        result.title = "Test Page"
        result.url = "https://example.com/test"
        result.links = {
            "internal": [
                {"href": "https://example.com/page1"},
                {"href": "https://example.com/page2"}
            ],
            "external": [
                {"href": "https://external.com/page"}
            ]
        }
        result.error_message = None
        return result
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_crawls_single_page(self, crawling_service, mock_crawler, mock_crawl_result):
        """Test crawling a single web page."""
        # Arrange
        url = "https://example.com/test"
        mock_crawler.arun = AsyncMock(return_value=mock_crawl_result)
        
        # Act
        result = await crawling_service.crawl_single_page(url)
        
        # Assert
        assert result["success"] is True
        assert result["url"] == url
        assert result["markdown"] == mock_crawl_result.markdown
        assert result["title"] == "Test Page"
        assert result["content_length"] == len(mock_crawl_result.markdown)
        mock_crawler.arun.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_extracts_content(self, crawling_service, mock_crawler, mock_crawl_result):
        """Test content extraction from crawled page."""
        # Arrange
        mock_crawler.arun = AsyncMock(return_value=mock_crawl_result)
        
        # Act
        result = await crawling_service.crawl_single_page("https://example.com")
        
        # Assert
        assert "markdown" in result
        assert result["markdown"] == "# Test Page\n\nThis is test content."
        assert "links" in result
        assert len(result["links"]["internal"]) == 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_handles_invalid_urls(self, crawling_service, mock_crawler):
        """Test handling of invalid URLs."""
        # Arrange
        mock_crawler.arun = AsyncMock(side_effect=Exception("Invalid URL"))
        
        # Act
        result = await crawling_service.crawl_single_page("invalid-url")
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "Invalid URL" in result["error"]
    
    @pytest.mark.unit
    @patch('requests.get')
    def test_crawling_service_respects_robots_txt(self, mock_get, crawling_service):
        """Test that sitemap parsing respects robots.txt (via requests headers)."""
        # Arrange
        sitemap_url = "https://example.com/sitemap.xml"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>"""
        mock_get.return_value = mock_response
        
        # Act
        urls = crawling_service.parse_sitemap(sitemap_url)
        
        # Assert
        assert len(urls) == 1
        assert urls[0] == "https://example.com/page1"
        mock_get.assert_called_once_with(sitemap_url, timeout=30)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_limits_crawl_depth(self, crawling_service, mock_crawler):
        """Test recursive crawling respects depth limits."""
        # Arrange
        start_urls = ["https://example.com"]
        max_depth = 2
        
        # Mock crawl results for different depths
        depth1_result = MagicMock()
        depth1_result.success = True
        depth1_result.markdown = "Depth 1 content"
        depth1_result.url = "https://example.com"
        depth1_result.links = {"internal": [{"href": "https://example.com/level1"}], "external": []}
        
        depth2_result = MagicMock()
        depth2_result.success = True
        depth2_result.markdown = "Depth 2 content"
        depth2_result.url = "https://example.com/level1"
        depth2_result.links = {"internal": [{"href": "https://example.com/level2"}], "external": []}
        
        # Set up mock to return different results based on depth
        mock_crawler.arun_many = AsyncMock()
        mock_crawler.arun_many.side_effect = [
            [depth1_result],  # First depth
            [depth2_result],  # Second depth
        ]
        
        # Act
        results = await crawling_service.crawl_recursive_with_progress(
            start_urls=start_urls,
            max_depth=max_depth,
            max_concurrent=5
        )
        
        # Assert
        assert len(results) == 2  # Should only crawl 2 levels deep
        assert mock_crawler.arun_many.call_count == 2
    
    @pytest.mark.unit
    def test_crawling_service_detects_content_type(self, crawling_service):
        """Test content type detection for URLs."""
        # Test sitemap detection
        assert crawling_service.is_sitemap("https://example.com/sitemap.xml") is True
        assert crawling_service.is_sitemap("https://example.com/sitemap/index.xml") is True
        assert crawling_service.is_sitemap("https://example.com/page.html") is False
        
        # Test text file detection
        assert crawling_service.is_txt("https://example.com/robots.txt") is True
        assert crawling_service.is_txt("https://example.com/readme.txt") is True
        assert crawling_service.is_txt("https://example.com/page.html") is False
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_handles_redirects(self, crawling_service, mock_crawler):
        """Test handling of URL redirects."""
        # Arrange
        original_url = "https://example.com/old"
        redirected_url = "https://example.com/new"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.url = redirected_url  # Crawler returns final URL
        mock_result.markdown = "Redirected content"
        mock_result.title = "New Page"
        mock_result.links = {"internal": [], "external": []}
        
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        
        # Act
        result = await crawling_service.crawl_single_page(original_url)
        
        # Assert
        assert result["success"] is True
        assert result["url"] == original_url  # Service preserves original URL
        assert result["markdown"] == "Redirected content"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawling_service_manages_concurrent_crawls(self, crawling_service, mock_crawler):
        """Test concurrent crawling with batch processing."""
        # Arrange
        urls = [f"https://example.com/page{i}" for i in range(50)]
        max_concurrent = 10
        
        # Create mock results for each URL
        mock_results = []
        for url in urls:
            result = MagicMock()
            result.success = True
            result.url = url
            result.markdown = f"Content for {url}"
            mock_results.append(result)
        
        # Mock arun_many to return results in batches
        mock_crawler.arun_many = AsyncMock(side_effect=lambda urls, **kwargs: 
            [r for r in mock_results if r.url in urls]
        )
        
        # Act
        results = await crawling_service.crawl_batch_with_progress(
            urls=urls,
            max_concurrent=max_concurrent
        )
        
        # Assert
        assert len(results) == 50
        assert all(r["markdown"] == f"Content for {r['url']}" for r in results)
        # Should be called multiple times due to batching
        assert mock_crawler.arun_many.call_count > 1
    
    @pytest.mark.unit
    @patch('requests.get')
    def test_parse_sitemap_handles_errors(self, mock_get, crawling_service):
        """Test sitemap parsing error handling."""
        # Test network error
        mock_get.side_effect = Exception("Network error")
        urls = crawling_service.parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []
        
        # Test invalid XML
        mock_get.side_effect = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"Invalid XML content"
        mock_get.return_value = mock_response
        
        urls = crawling_service.parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []
        
        # Test HTTP error
        mock_response.status_code = 404
        urls = crawling_service.parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_crawl_with_progress_callback(self, crawling_service, mock_crawler):
        """Test crawling with progress reporting."""
        # Arrange
        urls = ["https://example.com/page1", "https://example.com/page2"]
        progress_updates = []
        
        async def progress_callback(phase, percentage, message, **kwargs):
            progress_updates.append({
                "phase": phase,
                "percentage": percentage,
                "message": message
            })
        
        # Mock crawl results
        mock_results = []
        for url in urls:
            result = MagicMock()
            result.success = True
            result.url = url
            result.markdown = f"Content for {url}"
            mock_results.append(result)
        
        mock_crawler.arun_many = AsyncMock(return_value=mock_results)
        
        # Act
        results = await crawling_service.crawl_batch_with_progress(
            urls=urls,
            progress_callback=progress_callback
        )
        
        # Assert
        assert len(results) == 2
        assert len(progress_updates) > 0
        assert progress_updates[0]["phase"] == "crawling"
        assert progress_updates[-1]["percentage"] == 60  # End progress
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_crawler_instance_error(self, mock_supabase_client):
        """Test error when no crawler instance is available."""
        # Arrange
        service = CrawlingService(crawler=None, supabase_client=mock_supabase_client)
        
        # Act
        result = await service.crawl_single_page("https://example.com")
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "No crawler instance available"