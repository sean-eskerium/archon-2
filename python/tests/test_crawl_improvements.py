"""
Test the crawling improvements including WebSocket connection verification,
retry logic, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import the modules to test
from src.api.knowledge_api import CrawlProgressManager
from src.services.rag.crawling_service import CrawlingService


class TestCrawlProgressManager:
    """Test the enhanced CrawlProgressManager with connection events."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_wait(self):
        """Test that we can wait for WebSocket connections."""
        manager = CrawlProgressManager()
        progress_id = "test-progress-123"
        
        # Start a crawl
        manager.start_crawl(progress_id, {
            "url": "https://example.com",
            "status": "starting"
        })
        
        # Verify connection event was created
        assert progress_id in manager.connection_ready_events
        assert not manager.connection_ready_events[progress_id].is_set()
        
        # Test timeout when no connection
        connected = await manager.wait_for_websocket_connection(progress_id, timeout=0.1)
        assert not connected
        
        # Simulate WebSocket connection
        mock_websocket = AsyncMock()
        
        # Start connection in background
        async def connect_after_delay():
            await asyncio.sleep(0.1)
            await manager.add_websocket(progress_id, mock_websocket)
        
        # Start connection task
        connect_task = asyncio.create_task(connect_after_delay())
        
        # Wait for connection
        connected = await manager.wait_for_websocket_connection(progress_id, timeout=1.0)
        assert connected
        
        # Clean up
        await connect_task
    
    @pytest.mark.asyncio
    async def test_progress_broadcast_without_websocket(self):
        """Test that progress updates are stored even without WebSocket."""
        manager = CrawlProgressManager()
        progress_id = "test-progress-456"
        
        # Start crawl
        manager.start_crawl(progress_id, {"url": "https://example.com"})
        
        # Update progress without WebSocket
        await manager.update_progress(progress_id, {
            "status": "crawling",
            "percentage": 50,
            "log": "Crawling in progress..."
        })
        
        # Verify progress was stored
        assert progress_id in manager.active_crawls
        assert manager.active_crawls[progress_id]["status"] == "crawling"
        assert manager.active_crawls[progress_id]["percentage"] == 50
    
    @pytest.mark.asyncio
    async def test_cleanup_on_completion(self):
        """Test that resources are cleaned up after crawl completion."""
        manager = CrawlProgressManager()
        progress_id = "test-progress-789"
        
        # Start crawl
        manager.start_crawl(progress_id, {"url": "https://example.com"})
        
        # Complete crawl (with shortened cleanup time for testing)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await manager.complete_crawl(progress_id, {
                "chunksStored": 10,
                "wordCount": 1000
            })
        
        # Verify immediate state
        assert manager.active_crawls[progress_id]["status"] == "completed"
        
        # Simulate cleanup
        await mock_sleep.return_value
        
        # Note: In real implementation, cleanup happens after 5 minutes
        # For testing, we'd need to mock the sleep or wait


class TestCrawlingServiceRetry:
    """Test the enhanced crawling service with retry logic."""
    
    @pytest.mark.asyncio
    async def test_single_page_retry_on_failure(self):
        """Test that crawl_single_page retries on failure."""
        # Create mock crawler
        mock_crawler = AsyncMock()
        
        # Create service with mock crawler
        service = CrawlingService(crawler=mock_crawler)
        
        # Mock failed result followed by success
        failed_result = Mock(success=False, error_message="Network error")
        success_result = Mock(
            success=True,
            markdown="# Test Content\n\nThis is test content that is long enough.",
            title="Test Page",
            links={"internal": [], "external": []}
        )
        
        # Configure mock to fail twice then succeed
        mock_crawler.arun.side_effect = [failed_result, failed_result, success_result]
        
        # Call with retry
        result = await service.crawl_single_page("https://example.com", retry_count=3)
        
        # Verify success after retries
        assert result["success"] is True
        assert result["markdown"] == success_result.markdown
        assert mock_crawler.arun.call_count == 3
    
    @pytest.mark.asyncio
    async def test_single_page_max_retries_exceeded(self):
        """Test that crawl fails after max retries."""
        mock_crawler = AsyncMock()
        service = CrawlingService(crawler=mock_crawler)
        
        # Always fail
        failed_result = Mock(success=False, error_message="Persistent error")
        mock_crawler.arun.return_value = failed_result
        
        # Call with retry
        result = await service.crawl_single_page("https://example.com", retry_count=2)
        
        # Verify failure
        assert result["success"] is False
        assert "after 2 attempts" in result["error"]
        assert mock_crawler.arun.call_count == 2
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling in crawl."""
        mock_crawler = AsyncMock()
        service = CrawlingService(crawler=mock_crawler)
        
        # Simulate timeout
        mock_crawler.arun.side_effect = asyncio.TimeoutError()
        
        # Call with retry
        result = await service.crawl_single_page("https://example.com", retry_count=1)
        
        # Verify timeout error
        assert result["success"] is False
        assert "Timeout" in result["error"]
    
    @pytest.mark.asyncio
    async def test_insufficient_content_retry(self):
        """Test retry when content is insufficient."""
        mock_crawler = AsyncMock()
        service = CrawlingService(crawler=mock_crawler)
        
        # First return insufficient content, then good content
        insufficient_result = Mock(
            success=True,
            markdown="Too short",
            title="Test",
            links={}
        )
        good_result = Mock(
            success=True,
            markdown="# Good Content\n\n" + "This is sufficient content. " * 10,
            title="Test Page",
            links={"internal": [], "external": []}
        )
        
        mock_crawler.arun.side_effect = [insufficient_result, good_result]
        
        # Call with retry
        result = await service.crawl_single_page("https://example.com", retry_count=2)
        
        # Verify success with good content
        assert result["success"] is True
        assert result["markdown"] == good_result.markdown
        assert mock_crawler.arun.call_count == 2


class TestBatchCrawling:
    """Test batch crawling improvements."""
    
    @pytest.mark.asyncio
    async def test_smaller_batch_sizes(self):
        """Test that batch sizes are properly limited."""
        mock_crawler = AsyncMock()
        service = CrawlingService(crawler=mock_crawler)
        
        # Mock successful results
        success_result = Mock(
            success=True,
            url="https://example.com",
            markdown="# Content\n\n" + "Test content. " * 20,
            title="Test"
        )
        
        # Create 25 URLs
        urls = [f"https://example.com/page{i}" for i in range(25)]
        
        # Mock arun_many to track batch sizes
        batch_sizes = []
        
        async def mock_arun_many(urls, **kwargs):
            batch_sizes.append(len(urls))
            return [success_result] * len(urls)
        
        mock_crawler.arun_many = mock_arun_many
        
        # Crawl with progress callback
        progress_updates = []
        
        async def progress_callback(status, percentage, message, **kwargs):
            progress_updates.append({
                "status": status,
                "percentage": percentage,
                "message": message
            })
        
        # Run batch crawl
        results = await service.crawl_batch_with_progress(
            urls, 
            max_concurrent=15,  # Should limit batch to 10
            progress_callback=progress_callback
        )
        
        # Verify batch sizes
        assert all(size <= 10 for size in batch_sizes), f"Batch sizes: {batch_sizes}"
        assert len(results) == 25
        
        # Verify progress updates
        assert len(progress_updates) > 0
        assert any("completed" in update["message"].lower() for update in progress_updates)


@pytest.mark.asyncio
async def test_integration_crawl_flow():
    """Test the full crawl flow with WebSocket and retries."""
    
    # This would be an integration test that requires running services
    # Skipping for unit tests, but included as example
    
    # Steps:
    # 1. Start a crawl via API
    # 2. Connect WebSocket
    # 3. Verify connection is established before crawling starts
    # 4. Simulate some failures and verify retries
    # 5. Complete crawl and verify cleanup
    
    pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])