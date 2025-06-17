"""End-to-end tests for project workflows."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from src.main import app
from src.services.projects.project_service import ProjectService
from src.services.projects.task_service import TaskService
from src.services.projects.document_service import DocumentService


class TestProjectCreationWorkflow:
    """Test complete project creation workflow."""
    
    @pytest.mark.asyncio
    @patch('src.utils.get_supabase_client')
    async def test_create_project_with_tasks_and_docs(self, mock_get_client):
        """Test creating a project with tasks and documents."""
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        with TestClient(app) as client:
            # Step 1: Create project
            project_data = {
                "name": "AI Assistant Project",
                "description": "Build an AI-powered assistant",
                "metadata": {"category": "AI", "priority": "high"}
            }
            
            # Mock project creation
            mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "proj_123",
                **project_data,
                "created_at": datetime.now().isoformat()
            }]
            
            response = client.post("/api/projects", json=project_data)
            assert response.status_code == 201
            project = response.json()
            project_id = project["id"]
            
            # Step 2: Add tasks
            tasks = [
                {
                    "title": "Design system architecture",
                    "description": "Create high-level design",
                    "priority": "high"
                },
                {
                    "title": "Implement core features",
                    "description": "Build main functionality",
                    "priority": "medium"
                }
            ]
            
            for i, task_data in enumerate(tasks):
                mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                    "id": f"task_{i}",
                    "project_id": project_id,
                    **task_data,
                    "status": "todo"
                }]
                
                response = client.post(
                    f"/api/projects/{project_id}/tasks",
                    json=task_data
                )
                assert response.status_code == 201
            
            # Step 3: Add documents
            doc_data = {
                "title": "Requirements Document",
                "content": "# Project Requirements\n\n## Functional Requirements...",
                "doc_type": "requirements"
            }
            
            mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "doc_123",
                "project_id": project_id,
                **doc_data
            }]
            
            response = client.post(
                f"/api/projects/{project_id}/documents",
                json=doc_data
            )
            assert response.status_code == 201
            
            # Step 4: Verify complete project structure
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": project_id,
                "name": "AI Assistant Project",
                "tasks": [
                    {"id": "task_0", "title": "Design system architecture"},
                    {"id": "task_1", "title": "Implement core features"}
                ],
                "documents": [
                    {"id": "doc_123", "title": "Requirements Document"}
                ]
            }
            
            response = client.get(f"/api/projects/{project_id}?include=tasks,documents")
            assert response.status_code == 200
            
            project_details = response.json()
            assert len(project_details["tasks"]) == 2
            assert len(project_details["documents"]) == 1


class TestTaskManagementWorkflow:
    """Test task management workflow."""
    
    @pytest.mark.asyncio
    async def test_task_lifecycle(self):
        """Test complete task lifecycle from creation to completion."""
        with TestClient(app) as client:
            project_id = "proj_123"
            
            # Mock responses
            with patch('src.utils.get_supabase_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value = mock_client
                
                # Step 1: Create task
                task_data = {
                    "title": "Implement authentication",
                    "description": "Add user login functionality",
                    "priority": "high"
                }
                
                mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                    "id": "task_456",
                    "project_id": project_id,
                    **task_data,
                    "status": "todo"
                }]
                
                response = client.post(
                    f"/api/projects/{project_id}/tasks",
                    json=task_data
                )
                assert response.status_code == 201
                task = response.json()
                task_id = task["id"]
                
                # Step 2: Update task status - In Progress
                mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                    "id": task_id,
                    "status": "in_progress"
                }]
                
                response = client.patch(
                    f"/api/tasks/{task_id}",
                    json={"status": "in_progress"}
                )
                assert response.status_code == 200
                
                # Step 3: Add subtasks
                subtasks = [
                    {"title": "Design login UI"},
                    {"title": "Implement JWT tokens"},
                    {"title": "Add password hashing"}
                ]
                
                for subtask in subtasks:
                    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                        "id": f"subtask_{subtask['title'][:5]}",
                        "parent_task_id": task_id,
                        **subtask
                    }]
                    
                    response = client.post(
                        f"/api/tasks/{task_id}/subtasks",
                        json=subtask
                    )
                    assert response.status_code == 201
                
                # Step 4: Complete subtasks
                for i in range(3):
                    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                        "status": "done"
                    }]
                    
                    response = client.patch(
                        f"/api/tasks/subtask_{i}",
                        json={"status": "done"}
                    )
                    assert response.status_code == 200
                
                # Step 5: Complete main task
                mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                    "id": task_id,
                    "status": "done",
                    "completed_at": datetime.now().isoformat()
                }]
                
                response = client.patch(
                    f"/api/tasks/{task_id}",
                    json={"status": "done"}
                )
                assert response.status_code == 200
                
                completed_task = response.json()
                assert completed_task["status"] == "done"
                assert "completed_at" in completed_task


class TestDocumentVersioningWorkflow:
    """Test document versioning workflow."""
    
    @pytest.mark.asyncio
    async def test_document_versioning(self):
        """Test document creation and versioning."""
        with TestClient(app) as client:
            project_id = "proj_123"
            
            with patch('src.utils.get_supabase_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value = mock_client
                
                # Step 1: Create initial document
                doc_data = {
                    "title": "API Specification",
                    "content": "# API v1.0\n\n## Endpoints\n\n### GET /users",
                    "doc_type": "specification"
                }
                
                mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                    "id": "doc_789",
                    "project_id": project_id,
                    **doc_data,
                    "version": 1
                }]
                
                response = client.post(
                    f"/api/projects/{project_id}/documents",
                    json=doc_data
                )
                assert response.status_code == 201
                doc = response.json()
                doc_id = doc["id"]
                
                # Step 2: Update document (creates new version)
                updated_content = "# API v1.1\n\n## Endpoints\n\n### GET /users\n### POST /users"
                
                # Mock version creation
                mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                    "id": "ver_001",
                    "document_id": doc_id,
                    "version_number": 1,
                    "content": doc_data["content"]
                }]
                
                # Mock document update
                mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                    "id": doc_id,
                    "content": updated_content,
                    "version": 2
                }]
                
                response = client.put(
                    f"/api/documents/{doc_id}",
                    json={"content": updated_content}
                )
                assert response.status_code == 200
                
                # Step 3: Get version history
                mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    {
                        "id": "ver_001",
                        "version_number": 1,
                        "created_at": "2024-01-01T10:00:00"
                    },
                    {
                        "id": "ver_002",
                        "version_number": 2,
                        "created_at": "2024-01-01T11:00:00"
                    }
                ]
                
                response = client.get(f"/api/documents/{doc_id}/versions")
                assert response.status_code == 200
                versions = response.json()
                assert len(versions) == 2
                
                # Step 4: Restore previous version
                mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                    "content": doc_data["content"]
                }
                
                mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                    "id": doc_id,
                    "content": doc_data["content"],
                    "version": 3
                }]
                
                response = client.post(f"/api/documents/{doc_id}/versions/ver_001/restore")
                assert response.status_code == 200


class TestWebSocketNotifications:
    """Test WebSocket notifications during workflows."""
    
    @pytest.mark.asyncio
    async def test_realtime_updates(self):
        """Test real-time updates via WebSocket."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/projects/proj_123") as websocket:
                # Mock task creation
                with patch('src.utils.get_supabase_client') as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value = mock_client
                    
                    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                        "id": "task_999",
                        "title": "New Task",
                        "project_id": "proj_123"
                    }]
                    
                    # Create task via API
                    response = client.post(
                        "/api/projects/proj_123/tasks",
                        json={"title": "New Task"}
                    )
                    assert response.status_code == 201
                    
                    # Should receive WebSocket notification
                    notification = websocket.receive_json()
                    assert notification["type"] == "task_created"
                    assert notification["data"]["id"] == "task_999"


class TestErrorRecoveryWorkflow:
    """Test error recovery in workflows."""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback when errors occur."""
        with TestClient(app) as client:
            with patch('src.utils.get_supabase_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value = mock_client
                
                # Mock successful project creation
                mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
                    "id": "proj_temp",
                    "name": "Temporary Project"
                }]
                
                # But fail on related resource creation
                mock_client.table.return_value.insert.side_effect = [
                    Mock(execute=Mock(return_value=Mock(data=[{"id": "proj_temp"}]))),
                    Exception("Database constraint violation")
                ]
                
                # Attempt to create project with initial resources
                response = client.post(
                    "/api/projects",
                    json={
                        "name": "Temporary Project",
                        "initial_tasks": [
                            {"title": "Task 1"},
                            {"title": "Task 2"}
                        ]
                    }
                )
                
                # Should fail and rollback
                assert response.status_code == 500
                
                # Verify project was not created
                mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
                
                response = client.get("/api/projects/proj_temp")
                assert response.status_code == 404