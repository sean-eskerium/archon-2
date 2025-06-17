"""Tests for models module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pydantic import ValidationError

from src.modules.models import (
    Project, Task, TaskStatus, TaskPriority, Document, DocumentVersion,
    KnowledgeBase, KnowledgeSource, SourceType, CrawlStatus,
    MCPServer, MCPClient, MCPTool, MCPResource,
    ChatMessage, ChatRole, AgentResponse
)


class TestProjectModel:
    """Test cases for Project model."""
    
    def test_project_creation_valid(self):
        """Test creating a valid project."""
        project = Project(
            id="proj_123",
            name="Test Project",
            description="A test project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"key": "value"}
        )
        
        assert project.id == "proj_123"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.metadata == {"key": "value"}
    
    def test_project_validation_missing_required(self):
        """Test project validation with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            Project(description="Missing name")
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('name',) for error in errors)
    
    def test_project_validation_invalid_types(self):
        """Test project validation with invalid types."""
        with pytest.raises(ValidationError):
            Project(
                name=123,  # Should be string
                description="Valid description"
            )


class TestTaskModel:
    """Test cases for Task model."""
    
    def test_task_creation_with_defaults(self):
        """Test creating task with default values."""
        task = Task(
            title="Test Task",
            project_id="proj_123"
        )
        
        assert task.title == "Test Task"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.completed is False
        assert task.subtasks == []
    
    def test_task_status_validation(self):
        """Test task status enum validation."""
        task = Task(
            title="Test Task",
            project_id="proj_123",
            status=TaskStatus.IN_PROGRESS
        )
        assert task.status == TaskStatus.IN_PROGRESS
        
        # Test invalid status
        with pytest.raises(ValidationError):
            Task(
                title="Test Task",
                project_id="proj_123",
                status="INVALID_STATUS"
            )
    
    def test_task_priority_validation(self):
        """Test task priority enum validation."""
        task = Task(
            title="Test Task",
            project_id="proj_123",
            priority=TaskPriority.HIGH
        )
        assert task.priority == TaskPriority.HIGH
    
    def test_task_with_subtasks(self):
        """Test task with nested subtasks."""
        subtask = Task(
            title="Subtask",
            project_id="proj_123"
        )
        
        parent_task = Task(
            title="Parent Task",
            project_id="proj_123",
            subtasks=[subtask]
        )
        
        assert len(parent_task.subtasks) == 1
        assert parent_task.subtasks[0].title == "Subtask"


class TestDocumentModel:
    """Test cases for Document model."""
    
    def test_document_creation(self):
        """Test creating a document with all fields."""
        doc = Document(
            id="doc_123",
            project_id="proj_123",
            title="Test Document",
            content="Document content",
            doc_type="requirements",
            metadata={"author": "test"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert doc.id == "doc_123"
        assert doc.title == "Test Document"
        assert doc.content == "Document content"
        assert doc.metadata["author"] == "test"
    
    def test_document_version(self):
        """Test DocumentVersion model."""
        version = DocumentVersion(
            id="ver_123",
            document_id="doc_123",
            version_number=1,
            content="Version 1 content",
            metadata={"changes": "Initial version"},
            created_at=datetime.now()
        )
        
        assert version.version_number == 1
        assert version.content == "Version 1 content"


class TestKnowledgeBaseModels:
    """Test cases for Knowledge Base related models."""
    
    def test_knowledge_base_creation(self):
        """Test creating a knowledge base entry."""
        kb = KnowledgeBase(
            id="kb_123",
            project_id="proj_123",
            source_id="src_123",
            content="Knowledge content",
            embeddings=[0.1, 0.2, 0.3],
            metadata={"page": 1},
            created_at=datetime.now()
        )
        
        assert kb.id == "kb_123"
        assert kb.embeddings == [0.1, 0.2, 0.3]
        assert kb.metadata["page"] == 1
    
    def test_knowledge_source_types(self):
        """Test KnowledgeSource with different source types."""
        # URL source
        url_source = KnowledgeSource(
            id="src_123",
            project_id="proj_123",
            name="Web Source",
            source_type=SourceType.URL,
            url="https://example.com",
            crawl_status=CrawlStatus.COMPLETED
        )
        assert url_source.source_type == SourceType.URL
        assert url_source.url == "https://example.com"
        
        # File source
        file_source = KnowledgeSource(
            id="src_456",
            project_id="proj_123",
            name="File Source",
            source_type=SourceType.FILE,
            file_path="/path/to/file.pdf"
        )
        assert file_source.source_type == SourceType.FILE
        assert file_source.file_path == "/path/to/file.pdf"
    
    def test_crawl_status_validation(self):
        """Test crawl status enum validation."""
        source = KnowledgeSource(
            id="src_123",
            project_id="proj_123",
            name="Test Source",
            source_type=SourceType.URL,
            crawl_status=CrawlStatus.IN_PROGRESS
        )
        assert source.crawl_status == CrawlStatus.IN_PROGRESS


class TestMCPModels:
    """Test cases for MCP related models."""
    
    def test_mcp_server_creation(self):
        """Test creating an MCP server."""
        server = MCPServer(
            id="srv_123",
            name="Test Server",
            command="python",
            args=["-m", "test_server"],
            env={"API_KEY": "test"},
            created_at=datetime.now()
        )
        
        assert server.name == "Test Server"
        assert server.command == "python"
        assert server.args == ["-m", "test_server"]
        assert server.env["API_KEY"] == "test"
    
    def test_mcp_client_with_tools(self):
        """Test MCP client with tools and resources."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"}
        )
        
        resource = MCPResource(
            uri="resource://test",
            name="Test Resource",
            description="A test resource"
        )
        
        client = MCPClient(
            id="client_123",
            server_id="srv_123",
            tools=[tool],
            resources=[resource],
            is_connected=True
        )
        
        assert len(client.tools) == 1
        assert client.tools[0].name == "test_tool"
        assert len(client.resources) == 1
        assert client.resources[0].uri == "resource://test"
        assert client.is_connected is True


class TestChatModels:
    """Test cases for Chat related models."""
    
    def test_chat_message_creation(self):
        """Test creating chat messages with different roles."""
        user_msg = ChatMessage(
            role=ChatRole.USER,
            content="Hello, assistant!"
        )
        assert user_msg.role == ChatRole.USER
        assert user_msg.content == "Hello, assistant!"
        
        assistant_msg = ChatMessage(
            role=ChatRole.ASSISTANT,
            content="Hello! How can I help?"
        )
        assert assistant_msg.role == ChatRole.ASSISTANT
        
        system_msg = ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant."
        )
        assert system_msg.role == ChatRole.SYSTEM
    
    def test_agent_response(self):
        """Test AgentResponse model."""
        response = AgentResponse(
            content="Here is my response",
            metadata={
                "model": "gpt-4",
                "tokens": 150,
                "sources": ["doc1", "doc2"]
            },
            error=None
        )
        
        assert response.content == "Here is my response"
        assert response.metadata["model"] == "gpt-4"
        assert response.metadata["tokens"] == 150
        assert response.error is None
        
        # Test error response
        error_response = AgentResponse(
            content="",
            error="API rate limit exceeded"
        )
        assert error_response.error == "API rate limit exceeded"


class TestModelRelationships:
    """Test cases for model relationships and constraints."""
    
    def test_task_project_relationship(self):
        """Test task must belong to a project."""
        with pytest.raises(ValidationError):
            Task(title="Orphan Task")  # Missing project_id
    
    def test_document_project_relationship(self):
        """Test document must belong to a project."""
        with pytest.raises(ValidationError):
            Document(
                title="Orphan Document",
                content="Content"
            )  # Missing project_id
    
    def test_knowledge_source_validation(self):
        """Test knowledge source URL/file validation."""
        # URL source must have URL
        with pytest.raises(ValidationError):
            KnowledgeSource(
                id="src_123",
                project_id="proj_123",
                name="Invalid URL Source",
                source_type=SourceType.URL
                # Missing URL
            )
        
        # File source must have file path
        with pytest.raises(ValidationError):
            KnowledgeSource(
                id="src_456",
                project_id="proj_123",
                name="Invalid File Source",
                source_type=SourceType.FILE
                # Missing file_path
            )


class TestModelSerialization:
    """Test cases for model serialization."""
    
    def test_project_json_serialization(self):
        """Test project model JSON serialization."""
        project = Project(
            name="Test Project",
            description="Description",
            metadata={"key": "value"}
        )
        
        json_data = project.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test Project" in json_data
        
        # Test deserialization
        project_copy = Project.model_validate_json(json_data)
        assert project_copy.name == project.name
        assert project_copy.description == project.description
    
    def test_datetime_serialization(self):
        """Test datetime field serialization."""
        now = datetime.now()
        task = Task(
            title="Test Task",
            project_id="proj_123",
            created_at=now
        )
        
        json_data = task.model_dump()
        assert "created_at" in json_data
        
        # Ensure datetime is serializable
        import json
        json_str = json.dumps(json_data, default=str)
        assert isinstance(json_str, str)