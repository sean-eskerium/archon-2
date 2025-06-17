"""Performance tests for Archon system."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

from src.services.projects.project_service import ProjectService
from src.services.rag.search_service import SearchService
from src.services.rag.document_storage_service import DocumentStorageService
from src.services.mcp_client_service import MCPClientService


class TestDatabasePerformance:
    """Test database operation performance."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_bulk_insert_performance(self, mock_get_client):
        """Test performance of bulk insert operations."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock bulk insert response
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": f"proj_{i}"} for i in range(1000)
        ]
        
        service = ProjectService()
        
        # Create 1000 projects
        projects = [
            {
                "name": f"Project {i}",
                "description": f"Description for project {i}",
                "metadata": {"index": i}
            }
            for i in range(1000)
        ]
        
        start_time = time.time()
        
        # Should batch insert efficiently
        results = await service.bulk_create_projects(projects)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (< 2 seconds for mock)
        assert duration < 2.0
        assert len(results) == 1000
        
        # Verify batching was used (not 1000 individual calls)
        assert mock_client.table.return_value.insert.call_count < 10
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_concurrent_read_performance(self, mock_get_client):
        """Test performance of concurrent read operations."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock query response
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = {
            "id": "proj_123",
            "name": "Test Project"
        }
        
        service = ProjectService()
        
        # Perform 100 concurrent reads
        async def read_project(project_id):
            start = time.time()
            result = await service.get_project(project_id)
            return time.time() - start
        
        tasks = [read_project(f"proj_{i}") for i in range(100)]
        
        start_time = time.time()
        durations = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time
        
        # Should handle concurrent reads efficiently
        assert total_duration < 1.0  # 100 reads in < 1 second
        
        # Individual read times should be consistent
        avg_duration = statistics.mean(durations)
        std_deviation = statistics.stdev(durations)
        assert std_deviation < avg_duration * 0.5  # Low variance


class TestSearchPerformance:
    """Test search and RAG performance."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    @patch('src.utils.get_embedding')
    async def test_vector_search_performance(self, mock_embedding, mock_get_client):
        """Test vector search performance."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock embedding generation
        mock_embedding.return_value = [0.1] * 768
        
        # Mock search results
        mock_results = [
            {
                "id": f"kb_{i}",
                "content": f"Result {i}",
                "similarity": 0.9 - (i * 0.01)
            }
            for i in range(100)
        ]
        
        mock_client.rpc.return_value.execute.return_value.data = mock_results
        
        service = SearchService()
        
        # Perform searches
        queries = ["search query " + str(i) for i in range(10)]
        
        start_time = time.time()
        
        tasks = [service.search(q, "proj_123", limit=20) for q in queries]
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # Should complete 10 searches quickly
        assert duration < 2.0
        assert all(len(r) <= 20 for r in results)
        
        # Verify embedding was generated for each query
        assert mock_embedding.call_count == 10
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_document_chunking_performance(self, mock_get_client):
        """Test document chunking and storage performance."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock insert
        mock_client.table.return_value.insert.return_value.execute.return_value.data = []
        
        service = DocumentStorageService()
        
        # Large document (100KB)
        large_document = "Lorem ipsum " * 10000
        
        start_time = time.time()
        
        # Should efficiently chunk and process
        chunks = await service.chunk_document(
            document=large_document,
            chunk_size=1000,
            overlap=100
        )
        
        duration = time.time() - start_time
        
        # Should chunk quickly
        assert duration < 0.5
        assert len(chunks) > 50  # Should create many chunks
        
        # Verify chunks have proper overlap
        for i in range(1, len(chunks)):
            assert chunks[i][:100] in chunks[i-1]  # Overlap exists


class TestMCPPerformance:
    """Test MCP client performance."""
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_concurrent_tool_execution(self, mock_session):
        """Test concurrent MCP tool execution performance."""
        mock_client = AsyncMock()
        mock_session.return_value = mock_client
        
        # Mock tool responses
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "result": {"content": "Tool result"}
        }
        mock_client.post.return_value.__aenter__.return_value = mock_response
        
        service = MCPClientService()
        
        # Create mock client
        with patch.object(service, 'get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_get_client.return_value = mock_mcp_client
            
            # Execute 50 tools concurrently
            async def execute_tool(index):
                start = time.time()
                result = await service.execute_tool(
                    f"session_{index}",
                    "test_tool",
                    {"param": index}
                )
                return time.time() - start
            
            tasks = [execute_tool(i) for i in range(50)]
            
            start_time = time.time()
            durations = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
            
            # Should handle concurrent executions well
            assert total_duration < 2.0
            
            # Check for rate limiting effectiveness
            max_duration = max(durations)
            min_duration = min(durations)
            assert max_duration < min_duration * 10  # No extreme outliers
    
    @pytest.mark.asyncio
    async def test_session_lookup_performance(self):
        """Test session lookup performance with many sessions."""
        from src.services.mcp_session_manager import SimplifiedSessionManager
        
        manager = SimplifiedSessionManager()
        
        # Create 1000 sessions
        session_ids = []
        for i in range(1000):
            session_id = await manager.create_session(f"user_{i}", f"client_{i}")
            session_ids.append(session_id)
        
        # Measure lookup performance
        lookup_times = []
        
        for _ in range(100):
            # Random session lookup
            import random
            session_id = random.choice(session_ids)
            
            start = time.time()
            session = await manager.get_session(session_id)
            lookup_times.append(time.time() - start)
        
        # Lookups should be O(1) - very fast
        avg_lookup_time = statistics.mean(lookup_times)
        assert avg_lookup_time < 0.001  # Sub-millisecond lookups


class TestAPIPerformance:
    """Test API endpoint performance."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_api_response_time(self, mock_get_client):
        """Test API endpoint response times."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock database responses
        mock_client.table.return_value.select.return_value.execute.return_value.data = [
            {"id": f"proj_{i}", "name": f"Project {i}"}
            for i in range(100)
        ]
        
        with TestClient(app) as client:
            response_times = []
            
            # Make 100 API calls
            for _ in range(100):
                start = time.time()
                response = client.get("/api/projects?limit=10")
                response_times.append(time.time() - start)
                
                assert response.status_code == 200
            
            # Check response time metrics
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            # Average should be fast
            assert avg_response_time < 0.050  # 50ms average
            
            # 95th percentile should be reasonable
            assert p95_response_time < 0.100  # 100ms for 95% of requests
    
    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self):
        """Test WebSocket message throughput."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        with TestClient(app) as client:
            with client.websocket_connect("/ws/test") as websocket:
                # Send many messages quickly
                start_time = time.time()
                message_count = 1000
                
                for i in range(message_count):
                    websocket.send_json({
                        "type": "test",
                        "data": {"index": i}
                    })
                
                duration = time.time() - start_time
                throughput = message_count / duration
                
                # Should handle high message rate
                assert throughput > 1000  # > 1000 messages per second


class TestMemoryPerformance:
    """Test memory usage and efficiency."""
    
    @pytest.mark.asyncio
    async def test_large_dataset_memory_usage(self):
        """Test memory efficiency with large datasets."""
        import sys
        
        # Create large dataset
        large_list = []
        
        # Get initial memory
        initial_size = sys.getsizeof(large_list)
        
        # Add many items
        for i in range(10000):
            large_list.append({
                "id": f"item_{i}",
                "data": "x" * 100,  # 100 byte string
                "metadata": {"index": i}
            })
        
        # Get final memory
        final_size = sys.getsizeof(large_list)
        
        # Calculate per-item memory
        memory_per_item = (final_size - initial_size) / 10000
        
        # Should be memory efficient
        assert memory_per_item < 500  # Less than 500 bytes per item
    
    @pytest.mark.asyncio
    @patch('src.utils.get_embedding')
    async def test_embedding_cache_performance(self, mock_embedding):
        """Test embedding cache effectiveness."""
        mock_embedding.return_value = [0.1] * 768
        
        service = DocumentStorageService()
        
        # Generate embeddings for repeated content
        contents = ["Content " + str(i % 100) for i in range(1000)]  # Only 100 unique
        
        start_time = time.time()
        
        # Should cache repeated embeddings
        for content in contents:
            await service.generate_embedding(content)
        
        duration = time.time() - start_time
        
        # Should be fast due to caching
        assert duration < 1.0
        
        # Should have called embedding function only for unique content
        assert mock_embedding.call_count <= 100


class TestScalabilityTests:
    """Test system scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(self):
        """Simulate many concurrent users."""
        from src.services.projects.project_service import ProjectService
        
        with patch('src.utils.get_supabase_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock responses
            mock_client.table.return_value.select.return_value.execute.return_value.data = []
            
            # Simulate 100 concurrent users
            async def user_session(user_id):
                service = ProjectService()
                
                # Each user performs several operations
                operations = []
                
                # List projects
                start = time.time()
                await service.list_projects()
                operations.append(time.time() - start)
                
                # Get specific project
                start = time.time()
                await service.get_project(f"proj_{user_id}")
                operations.append(time.time() - start)
                
                return operations
            
            # Run concurrent user sessions
            start_time = time.time()
            
            tasks = [user_session(i) for i in range(100)]
            all_operations = await asyncio.gather(*tasks)
            
            total_duration = time.time() - start_time
            
            # Should handle 100 concurrent users
            assert total_duration < 5.0
            
            # Flatten operation times
            all_times = [t for user_times in all_operations for t in user_times]
            
            # Check operation consistency
            avg_time = statistics.mean(all_times)
            assert avg_time < 0.050  # 50ms average per operation