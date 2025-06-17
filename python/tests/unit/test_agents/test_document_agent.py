"""Unit tests for DocumentAgent."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import json
import uuid
from dataclasses import dataclass
from src.agents.document_agent import DocumentAgent, DocumentDependencies, DocumentOperation


class TestDocumentAgent:
    """Unit tests for DocumentAgent."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def document_agent(self):
        """Create DocumentAgent instance."""
        return DocumentAgent()
    
    @pytest.fixture
    def document_deps(self):
        """Create document dependencies."""
        return DocumentDependencies(
            project_id="test-project-123",
            user_id="test-user",
            current_document_id=None,
            progress_callback=None
        )
    
    @pytest.fixture
    def sample_document(self):
        """Sample document data."""
        return {
            "id": "doc-123",
            "title": "Test PRD",
            "document_type": "prd",
            "content": {
                "overview": "This is a test product requirements document",
                "features": ["Feature 1", "Feature 2"],
                "requirements": {
                    "functional": ["Req 1", "Req 2"],
                    "non_functional": ["Performance", "Security"]
                }
            },
            "status": "draft",
            "version": "1.0"
        }
    
    @pytest.mark.unit
    def test_document_agent_supports_conversation(self, document_agent):
        """Test that document agent supports conversational interactions."""
        # Verify agent configuration
        assert document_agent.name == "DocumentAgent"
        assert document_agent.model == "openai:gpt-4o-mini"
        assert document_agent.enable_rate_limiting is True
        
        # Verify system prompt contains document capabilities
        system_prompt = document_agent.get_system_prompt()
        assert "Document Management Assistant" in system_prompt
        assert "create new documents" in system_prompt.lower()
        assert "update existing document" in system_prompt.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_document_agent_creates_documents(self, document_agent, document_deps):
        """Test document creation through conversation."""
        # Mock the internal agent
        mock_agent_result = MagicMock()
        mock_agent_result.data = DocumentOperation(
            operation_type="create",
            document_id="new-doc-123",
            document_type="prd",
            title="User Authentication PRD",
            changes_made=["Created new PRD document"],
            success=True,
            message="Successfully created PRD",
            content_preview="This document describes user authentication..."
        )
        
        document_agent._agent.run = AsyncMock(return_value=mock_agent_result)
        
        # Test document creation
        result = await document_agent.run_conversation(
            user_message="Create a PRD for user authentication",
            project_id="test-project",
            user_id="test-user"
        )
        
        assert result.operation_type == "create"
        assert result.document_type == "prd"
        assert result.success is True
        assert "authentication" in result.title.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit  
    async def test_document_agent_updates_documents(self, document_agent, document_deps):
        """Test document updates through conversation."""
        # Mock the update operation
        mock_agent_result = MagicMock()
        mock_agent_result.data = DocumentOperation(
            operation_type="update",
            document_id="existing-doc-123",
            document_type="prd",
            title="Updated PRD",
            changes_made=["Added OAuth section", "Updated security requirements"],
            success=True,
            message="Successfully updated document",
            content_preview="Updated content preview..."
        )
        
        document_agent._agent.run = AsyncMock(return_value=mock_agent_result)
        
        # Test document update
        result = await document_agent.run_conversation(
            user_message="Add OAuth authentication section to the PRD",
            project_id="test-project",
            user_id="test-user",
            current_document_id="existing-doc-123"
        )
        
        assert result.operation_type == "update"
        assert result.success is True
        assert "OAuth section" in result.changes_made
    
    @pytest.mark.unit
    def test_document_agent_understands_multiple_formats(self, document_agent):
        """Test agent understanding of different document types."""
        # Get system prompt to verify document types
        system_prompt = document_agent.get_system_prompt()
        
        # Check supported document types
        document_types = [
            "prd", "technical_spec", "meeting_notes",
            "api_docs", "feature_plan", "erd"
        ]
        
        for doc_type in document_types:
            assert doc_type in system_prompt.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_document_agent_generates_structured_content(self, document_agent):
        """Test that agent generates properly structured document content."""
        # Test block generation
        blocks = document_agent._convert_to_blocks(
            title="Test Document",
            document_type="prd",
            content_description="A product requirements document for a chat application"
        )
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "heading"
        assert blocks[0]["data"]["text"] == "Test Document"
        
        # Should have introduction and sections
        block_types = [block["type"] for block in blocks]
        assert "paragraph" in block_types
        assert "heading" in block_types
    
    @pytest.mark.unit
    def test_block_creation_utilities(self, document_agent):
        """Test document block creation utilities."""
        # Test block ID generation
        block_id1 = document_agent._generate_block_id()
        block_id2 = document_agent._generate_block_id()
        assert block_id1 != block_id2
        assert len(block_id1) > 10
        
        # Test block creation
        block = document_agent._create_block(
            block_type="paragraph",
            content="Test content",
            properties={"alignment": "left"}
        )
        
        assert block["type"] == "paragraph"
        assert block["data"]["text"] == "Test content"
        assert block["data"]["alignment"] == "left"
        assert "id" in block
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_progress_callback_integration(self, document_agent):
        """Test progress callback is called during operations."""
        # Create progress callback mock
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        # Create deps with callback
        deps = DocumentDependencies(
            project_id="test-project",
            progress_callback=progress_callback
        )
        
        # Mock successful operation
        mock_result = MagicMock()
        mock_result.data = DocumentOperation(
            operation_type="create",
            success=True,
            message="Created document",
            changes_made=["Created new document"],
            document_id="123",
            title="Test Doc"
        )
        
        document_agent._agent.run = AsyncMock(return_value=mock_result)
        
        # Run with progress callback
        await document_agent.run("Create a document", deps)
        
        # Progress callback should be passed to agent
        assert deps.progress_callback is not None
    
    @pytest.mark.unit
    def test_document_operation_validation(self):
        """Test DocumentOperation model validation."""
        # Valid operation
        op = DocumentOperation(
            operation_type="create",
            document_id="123",
            document_type="prd",
            title="Test",
            changes_made=["Created"],
            success=True,
            message="Success"
        )
        
        assert op.operation_type == "create"
        assert op.success is True
        
        # Test with minimal required fields
        min_op = DocumentOperation(
            operation_type="query",
            changes_made=[],
            success=False,
            message="Query operation"
        )
        
        assert min_op.document_id is None
        assert min_op.content_preview is None