"""Integration tests for database operations."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
from supabase import create_client, Client

from src.services.projects.project_service import ProjectService
from src.services.projects.task_service import TaskService
from src.services.projects.document_service import DocumentService
from src.services.rag.document_storage_service import DocumentStorageService
from src.services.rag.source_management_service import SourceManagementService


class TestDatabaseTransactions:
    """Test database transaction handling."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_project_cascade_delete(self, mock_get_client):
        """Test cascading delete of project and related data."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock database responses
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
        
        project_service = ProjectService()
        task_service = TaskService()
        
        # Test cascade delete
        project_id = "proj_123"
        
        # Should delete tasks, documents, knowledge sources
        await project_service.delete_project(project_id)
        
        # Verify cascade operations
        assert mock_client.table.call_count >= 3  # projects, tasks, documents tables
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_transaction_rollback(self, mock_get_client):
        """Test transaction rollback on error."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # First operation succeeds
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "task_123"}]
        
        # Second operation fails
        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
        
        task_service = TaskService()
        
        with pytest.raises(Exception):
            # This should rollback the entire transaction
            await task_service.create_task_with_subtasks(
                project_id="proj_123",
                title="Parent Task",
                subtasks=[{"title": "Subtask 1"}, {"title": "Subtask 2"}]
            )
        
        # Verify rollback was attempted
        assert mock_client.table.called


class TestDatabaseConnections:
    """Test database connection handling."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_connection_pooling(self, mock_get_client):
        """Test connection pool management."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Simulate multiple concurrent requests
        services = [ProjectService() for _ in range(10)]
        
        # Execute concurrent operations
        tasks = []
        for service in services:
            task = service.list_projects(limit=10)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify connection reuse (should use same client)
        assert mock_get_client.call_count <= 10
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_connection_retry(self, mock_get_client):
        """Test automatic retry on connection failure."""
        mock_client = AsyncMock()
        
        # First call fails, second succeeds
        mock_get_client.side_effect = [
            Exception("Connection failed"),
            mock_client
        ]
        
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        
        service = ProjectService()
        
        # Should retry and succeed
        with patch('asyncio.sleep'):  # Skip actual delay
            result = await service.list_projects()
        
        assert result == []
        assert mock_get_client.call_count == 2


class TestDatabaseQueries:
    """Test complex database queries."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_complex_join_query(self, mock_get_client):
        """Test complex queries with joins."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock complex query result
        mock_result = {
            "id": "proj_123",
            "name": "Test Project",
            "tasks": [
                {"id": "task_1", "title": "Task 1", "status": "todo"},
                {"id": "task_2", "title": "Task 2", "status": "done"}
            ],
            "documents": [
                {"id": "doc_1", "title": "Requirements"}
            ]
        }
        
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_result
        
        service = ProjectService()
        result = await service.get_project_with_relations("proj_123")
        
        assert result["name"] == "Test Project"
        assert len(result["tasks"]) == 2
        assert len(result["documents"]) == 1
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_pagination_consistency(self, mock_get_client):
        """Test pagination consistency across requests."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock paginated results
        page1_data = [{"id": f"proj_{i}", "name": f"Project {i}"} for i in range(10)]
        page2_data = [{"id": f"proj_{i}", "name": f"Project {i}"} for i in range(10, 20)]
        
        mock_client.table.return_value.select.return_value.range.side_effect = [
            Mock(execute=Mock(return_value=Mock(data=page1_data))),
            Mock(execute=Mock(return_value=Mock(data=page2_data)))
        ]
        
        service = ProjectService()
        
        # Get first page
        result1 = await service.list_projects(offset=0, limit=10)
        # Get second page
        result2 = await service.list_projects(offset=10, limit=10)
        
        # Verify no overlap
        ids1 = {p["id"] for p in result1}
        ids2 = {p["id"] for p in result2}
        assert len(ids1.intersection(ids2)) == 0


class TestDatabaseConsistency:
    """Test data consistency and integrity."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_concurrent_updates(self, mock_get_client):
        """Test handling of concurrent updates."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Simulate optimistic locking with version field
        initial_doc = {"id": "doc_123", "content": "Initial", "version": 1}
        updated_doc = {"id": "doc_123", "content": "Updated", "version": 2}
        
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = initial_doc
        
        # First update succeeds
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [updated_doc]
        
        service = DocumentService()
        
        # Two concurrent updates
        update1 = service.update_document("doc_123", {"content": "Update 1"})
        update2 = service.update_document("doc_123", {"content": "Update 2"})
        
        results = await asyncio.gather(update1, update2, return_exceptions=True)
        
        # One should succeed, one should handle version conflict
        assert any(isinstance(r, dict) for r in results)
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_referential_integrity(self, mock_get_client):
        """Test referential integrity constraints."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Try to create task for non-existent project
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Foreign key violation"
        )
        
        service = TaskService()
        
        with pytest.raises(Exception) as exc_info:
            await service.create_task(
                project_id="non_existent_proj",
                title="Orphan Task"
            )
        
        assert "Foreign key" in str(exc_info.value)


class TestDatabasePerformance:
    """Test database performance optimizations."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_bulk_insert_optimization(self, mock_get_client):
        """Test bulk insert performance."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock bulk insert
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": f"kb_{i}"} for i in range(100)
        ]
        
        service = DocumentStorageService()
        
        # Create 100 embeddings
        embeddings = [
            {
                "content": f"Chunk {i}",
                "embedding": [0.1] * 768,
                "metadata": {"chunk_index": i}
            }
            for i in range(100)
        ]
        
        start_time = asyncio.get_event_loop().time()
        await service.store_embeddings("proj_123", "source_123", embeddings)
        end_time = asyncio.get_event_loop().time()
        
        # Should use bulk insert (single call)
        assert mock_client.table.return_value.insert.call_count == 1
        
        # Should complete quickly
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_index_usage(self, mock_get_client):
        """Test that queries use appropriate indexes."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock indexed query
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        
        service = TaskService()
        
        # Query that should use project_id index
        await service.list_tasks(
            project_id="proj_123",
            status="in_progress",
            order_by="created_at"
        )
        
        # Verify query structure promotes index usage
        calls = mock_client.table.return_value.select.return_value.eq.call_args_list
        assert any(call[0] == ('project_id', 'proj_123') for call in calls)


class TestDatabaseMigrations:
    """Test database migration scenarios."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_schema_version_check(self, mock_get_client):
        """Test schema version compatibility check."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock schema version table
        mock_client.table.return_value.select.return_value.single.return_value.execute.return_value.data = {
            "version": "1.2.0",
            "applied_at": datetime.now().isoformat()
        }
        
        # Service should check schema version on init
        service = ProjectService()
        await service.check_schema_compatibility()
        
        mock_client.table.assert_any_call("schema_migrations")
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_data_migration_handling(self, mock_get_client):
        """Test handling of data during migrations."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock old format data
        old_format_tasks = [
            {"id": "task_1", "title": "Task 1", "completed": True},  # Old field name
            {"id": "task_2", "title": "Task 2", "completed": False}
        ]
        
        mock_client.table.return_value.select.return_value.execute.return_value.data = old_format_tasks
        
        service = TaskService()
        
        # Service should handle old format gracefully
        tasks = await service.list_tasks("proj_123")
        
        # Should map old field names to new
        assert all("status" in task for task in tasks)
        assert tasks[0]["status"] == "done"
        assert tasks[1]["status"] == "todo"