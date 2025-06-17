"""Mock data factories for testing."""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import uuid


class MockDataFactory:
    """Factory for creating mock test data."""
    
    @staticmethod
    def create_project(
        id: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock project data."""
        now = datetime.utcnow()
        project_id = id or f"project-{uuid.uuid4().hex[:8]}"
        
        base_project = {
            "id": project_id,
            "title": title or f"Test Project {project_id[:8]}",
            "description": kwargs.get("description", "Test project description"),
            "status": kwargs.get("status", "active"),
            "pinned": kwargs.get("pinned", False),
            "created_at": kwargs.get("created_at", now.isoformat()),
            "updated_at": kwargs.get("updated_at", now.isoformat()),
            "metadata": kwargs.get("metadata", {"test": True}),
            "tags": kwargs.get("tags", ["test", "mock"]),
            "settings": kwargs.get("settings", {})
        }
        
        return base_project
    
    @staticmethod
    def create_task(
        id: Optional[str] = None,
        project_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock task data."""
        now = datetime.utcnow()
        task_id = id or f"task-{uuid.uuid4().hex[:8]}"
        
        base_task = {
            "id": task_id,
            "project_id": project_id or f"project-{uuid.uuid4().hex[:8]}",
            "title": kwargs.get("title", f"Test Task {task_id[:8]}"),
            "description": kwargs.get("description", "Test task description"),
            "status": kwargs.get("status", "todo"),
            "priority": kwargs.get("priority", 1),
            "assignee": kwargs.get("assignee", "Archon"),
            "parent_id": kwargs.get("parent_id", None),
            "created_at": kwargs.get("created_at", now.isoformat()),
            "updated_at": kwargs.get("updated_at", now.isoformat()),
            "due_date": kwargs.get("due_date", None),
            "metadata": kwargs.get("metadata", {"test": True}),
            "tags": kwargs.get("tags", []),
            "subtasks": kwargs.get("subtasks", [])
        }
        
        return base_task
    
    @staticmethod
    def create_document(
        id: Optional[str] = None,
        project_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock document data."""
        now = datetime.utcnow()
        doc_id = id or f"doc-{uuid.uuid4().hex[:8]}"
        
        base_document = {
            "id": doc_id,
            "project_id": project_id or f"project-{uuid.uuid4().hex[:8]}",
            "title": kwargs.get("title", f"Test Document {doc_id[:8]}"),
            "content": kwargs.get("content", "Test document content\n\nWith multiple lines."),
            "type": kwargs.get("type", "markdown"),
            "metadata": kwargs.get("metadata", {"test": True}),
            "created_at": kwargs.get("created_at", now.isoformat()),
            "updated_at": kwargs.get("updated_at", now.isoformat()),
            "version": kwargs.get("version", 1),
            "tags": kwargs.get("tags", [])
        }
        
        return base_document
    
    @staticmethod
    def create_mcp_client(
        id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock MCP client configuration."""
        client_id = id or f"client-{uuid.uuid4().hex[:8]}"
        
        base_client = {
            "id": client_id,
            "name": kwargs.get("name", f"Test MCP Client {client_id[:8]}"),
            "transport": kwargs.get("transport", "stdio"),
            "command": kwargs.get("command", "python"),
            "args": kwargs.get("args", ["-m", "test_mcp_server"]),
            "env": kwargs.get("env", {}),
            "enabled": kwargs.get("enabled", True),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
            "metadata": kwargs.get("metadata", {"test": True})
        }
        
        return base_client
    
    @staticmethod
    def create_knowledge_source(
        id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock knowledge source data."""
        source_id = id or f"source-{uuid.uuid4().hex[:8]}"
        
        base_source = {
            "id": source_id,
            "url": kwargs.get("url", f"https://example.com/{source_id}"),
            "title": kwargs.get("title", f"Test Source {source_id[:8]}"),
            "type": kwargs.get("type", "website"),
            "status": kwargs.get("status", "indexed"),
            "page_count": kwargs.get("page_count", 10),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow().isoformat()),
            "metadata": kwargs.get("metadata", {"test": True})
        }
        
        return base_source
    
    @staticmethod
    def create_knowledge_page(
        id: Optional[str] = None,
        source_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock knowledge page data."""
        page_id = id or f"page-{uuid.uuid4().hex[:8]}"
        
        base_page = {
            "id": page_id,
            "source_id": source_id or f"source-{uuid.uuid4().hex[:8]}",
            "url": kwargs.get("url", f"https://example.com/page/{page_id}"),
            "title": kwargs.get("title", f"Test Page {page_id[:8]}"),
            "content": kwargs.get("content", "Test page content with sample text."),
            "embedding": kwargs.get("embedding", [0.1] * 1536),  # Mock embedding
            "metadata": kwargs.get("metadata", {"test": True}),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat())
        }
        
        return base_page
    
    @staticmethod
    def create_chat_message(
        role: str = "user",
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock chat message."""
        return {
            "role": role,
            "content": kwargs.get("content", "Test message content"),
            "timestamp": kwargs.get("timestamp", datetime.utcnow().isoformat()),
            "metadata": kwargs.get("metadata", {})
        }
    
    @staticmethod
    def create_websocket_message(
        type: str = "message",
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock WebSocket message."""
        return {
            "type": type,
            "data": kwargs.get("data", {"test": True}),
            "timestamp": kwargs.get("timestamp", datetime.utcnow().isoformat()),
            "id": kwargs.get("id", f"msg-{uuid.uuid4().hex[:8]}")
        }
    
    @staticmethod
    def create_api_response(
        status_code: int = 200,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock API response."""
        return {
            "status_code": status_code,
            "data": kwargs.get("data", {"success": True}),
            "headers": kwargs.get("headers", {"Content-Type": "application/json"}),
            "error": kwargs.get("error", None)
        }
    
    @staticmethod
    def create_batch(factory_method: Callable[..., Dict[str, Any]], count: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Create a batch of mock data using the specified factory method."""
        return [factory_method(**kwargs) for _ in range(count)]


# Convenience instance
mock_factory = MockDataFactory()