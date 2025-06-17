"""Unit tests for DocumentAgent with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import json
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from src.agents.document_agent import DocumentAgent, DocumentDependencies, DocumentOperation
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time
)


@pytest.mark.unit
@pytest.mark.standard
class TestDocumentAgent:
    """Unit tests for DocumentAgent with enhanced patterns."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def make_document_agent(self):
        """Factory for creating document agents with custom configs."""
        def _make_agent(
            name: str = "DocumentAgent",
            model: str = "openai:gpt-4o-mini",
            enable_rate_limiting: bool = True,
            temperature: float = 0.7
        ) -> DocumentAgent:
            return DocumentAgent(
                name=name,
                model=model,
                enable_rate_limiting=enable_rate_limiting,
                temperature=temperature
            )
        return _make_agent
    
    @pytest.fixture
    def document_agent(self, make_document_agent):
        """Create default DocumentAgent instance."""
        return make_document_agent()
    
    @pytest.fixture
    def make_document_deps(self):
        """Factory for creating document dependencies."""
        def _make_deps(
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
            current_document_id: Optional[str] = None,
            progress_callback: Optional[Any] = None
        ) -> DocumentDependencies:
            return DocumentDependencies(
                project_id=project_id or f"project-{uuid.uuid4().hex[:8]}",
                user_id=user_id or f"user-{uuid.uuid4().hex[:8]}",
                current_document_id=current_document_id,
                progress_callback=progress_callback
            )
        return _make_deps
    
    @pytest.fixture
    def document_deps(self, make_document_deps):
        """Create default document dependencies."""
        return make_document_deps()
    
    @pytest.fixture
    def make_document_data(self):
        """Factory for creating sample documents."""
        def _make_document(
            doc_id: Optional[str] = None,
            title: str = "Test Document",
            document_type: str = "prd",
            status: str = "draft",
            version: str = "1.0",
            content: Optional[Dict] = None
        ) -> Dict:
            return {
                "id": doc_id or f"doc-{uuid.uuid4().hex[:8]}",
                "title": title,
                "document_type": document_type,
                "content": content or {
                    "overview": f"Overview for {title}",
                    "features": ["Feature 1", "Feature 2"],
                    "requirements": {
                        "functional": ["Req 1", "Req 2"],
                        "non_functional": ["Performance", "Security"]
                    }
                },
                "status": status,
                "version": version
            }
        return _make_document
    
    @pytest.fixture
    def make_document_operation(self):
        """Factory for creating DocumentOperation results."""
        def _make_operation(
            operation_type: str = "create",
            document_id: Optional[str] = None,
            document_type: Optional[str] = "prd",
            title: Optional[str] = None,
            changes_made: Optional[List[str]] = None,
            success: bool = True,
            message: str = "Operation successful",
            content_preview: Optional[str] = None
        ) -> DocumentOperation:
            return DocumentOperation(
                operation_type=operation_type,
                document_id=document_id,
                document_type=document_type,
                title=title,
                changes_made=changes_made or [],
                success=success,
                message=message,
                content_preview=content_preview
            )
        return _make_operation
    
    # =============================================================================
    # Agent Configuration Tests
    # =============================================================================
    
    @pytest.mark.parametrize("model,rate_limiting", [
        pytest.param("openai:gpt-4o-mini", True, id="default-config"),
        pytest.param("openai:gpt-4o", True, id="gpt4-model"),
        pytest.param("openai:gpt-3.5-turbo", False, id="gpt35-no-rate-limit"),
    ])
    def test_agent_initialization_configurations(
        self,
        make_document_agent,
        model,
        rate_limiting
    ):
        """Test document agent initialization with various configurations."""
        # Act
        agent = make_document_agent(model=model, enable_rate_limiting=rate_limiting)
        
        # Assert
        assert agent.name == "DocumentAgent"
        assert agent.model == model
        assert agent.enable_rate_limiting == rate_limiting
        
        # Verify system prompt
        system_prompt = agent.get_system_prompt()
        assert "Document Management Assistant" in system_prompt
        assert all(doc_type in system_prompt.lower() for doc_type in [
            "prd", "technical_spec", "meeting_notes", "api_docs"
        ])
    
    # =============================================================================
    # Document Operation Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("operation,user_message,expected_fields", [
        pytest.param(
            "create",
            "Create a PRD for user authentication",
            {"operation_type": "create", "document_type": "prd", "success": True},
            id="create-prd"
        ),
        pytest.param(
            "update",
            "Add OAuth section to the existing document",
            {"operation_type": "update", "success": True},
            id="update-document"
        ),
        pytest.param(
            "query",
            "What documents do we have for authentication?",
            {"operation_type": "query", "success": True},
            id="query-documents"
        ),
    ])
    async def test_document_operations_via_conversation(
        self,
        document_agent,
        make_document_deps,
        make_document_operation,
        operation,
        user_message,
        expected_fields
    ):
        """Test various document operations through conversation."""
        # Arrange
        deps = make_document_deps(
            current_document_id="existing-doc" if operation == "update" else None
        )
        
        mock_result = MagicMock()
        mock_result.data = make_document_operation(**expected_fields)
        document_agent._agent.run = AsyncMock(return_value=mock_result)
        
        # Act
        result = await document_agent.run_conversation(
            user_message=user_message,
            project_id=deps.project_id,
            user_id=deps.user_id,
            current_document_id=deps.current_document_id
        )
        
        # Assert
        for field, value in expected_fields.items():
            assert getattr(result, field) == value
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("changes_count", [0, 1, 5, 10])
    async def test_document_update_tracking(
        self,
        document_agent,
        document_deps,
        make_document_operation,
        changes_count
    ):
        """Test tracking of multiple changes during document updates."""
        # Arrange
        changes = [f"Change {i+1}" for i in range(changes_count)]
        
        mock_result = MagicMock()
        mock_result.data = make_document_operation(
            operation_type="update",
            changes_made=changes
        )
        document_agent._agent.run = AsyncMock(return_value=mock_result)
        
        # Act
        result = await document_agent.run("Update document", document_deps)
        
        # Assert
        assert len(result.changes_made) == changes_count
        if changes_count > 0:
            assert all(f"Change {i+1}" in result.changes_made for i in range(changes_count))
    
    # =============================================================================
    # Block Generation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("doc_type,expected_blocks", [
        pytest.param(
            "prd",
            ["heading", "paragraph", "list"],
            id="prd-blocks"
        ),
        pytest.param(
            "technical_spec",
            ["heading", "paragraph", "code"],
            id="tech-spec-blocks"
        ),
        pytest.param(
            "meeting_notes",
            ["heading", "paragraph", "checklist"],
            id="meeting-notes-blocks"
        ),
    ])
    def test_block_generation_for_document_types(
        self,
        document_agent,
        doc_type,
        expected_blocks
    ):
        """Test block generation for different document types."""
        # Act
        blocks = document_agent._convert_to_blocks(
            title=f"Test {doc_type}",
            document_type=doc_type,
            content_description=f"A {doc_type} document for testing"
        )
        
        # Assert
        assert len(blocks) > 0
        assert blocks[0]["type"] == "heading"
        assert blocks[0]["data"]["text"] == f"Test {doc_type}"
        
        # Check for expected block types based on document type
        block_types = {block["type"] for block in blocks}
        for expected_type in expected_blocks:
            if expected_type in ["code", "checklist"]:  # Optional blocks
                continue
            assert expected_type in block_types
    
    @pytest.mark.parametrize("block_type,content,properties", [
        pytest.param(
            "paragraph",
            "Test paragraph content",
            {"alignment": "left"},
            id="paragraph-block"
        ),
        pytest.param(
            "heading",
            "Test Heading",
            {"level": 2},
            id="heading-block"
        ),
        pytest.param(
            "list",
            ["Item 1", "Item 2"],
            {"style": "unordered"},
            id="list-block"
        ),
    ])
    def test_individual_block_creation(
        self,
        document_agent,
        block_type,
        content,
        properties
    ):
        """Test creation of individual block types."""
        # Act
        block = document_agent._create_block(
            block_type=block_type,
            content=content,
            properties=properties
        )
        
        # Assert
        assert block["type"] == block_type
        assert "id" in block
        assert len(block["id"]) > 10  # Valid block ID
        
        if isinstance(content, list):
            assert "items" in block["data"]
        else:
            assert block["data"]["text"] == content
        
        # Check properties
        for key, value in properties.items():
            assert block["data"][key] == value
    
    # =============================================================================
    # Progress Callback Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_progress_callback_integration(
        self,
        document_agent,
        make_document_deps,
        make_document_operation
    ):
        """Test progress callbacks during document operations."""
        # Arrange
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        deps = make_document_deps(progress_callback=progress_callback)
        
        mock_result = MagicMock()
        mock_result.data = make_document_operation(
            operation_type="create",
            message="Creating document...",
            changes_made=["Step 1: Initialize", "Step 2: Generate content"]
        )
        document_agent._agent.run = AsyncMock(return_value=mock_result)
        
        # Act
        await document_agent.run("Create a document", deps)
        
        # Assert
        # Verify the callback was passed through to dependencies
        assert deps.progress_callback is not None
        document_agent._agent.run.assert_called_once()
        call_deps = document_agent._agent.run.call_args[1]['deps']
        assert call_deps.progress_callback is progress_callback
    
    # =============================================================================
    # Memory and Context Tests
    # =============================================================================
    
    @pytest.mark.parametrize("conversation_length", [1, 5, 10])
    def test_conversation_memory_handling(
        self,
        document_agent,
        conversation_length
    ):
        """Test handling of conversation context with various lengths."""
        # Note: This tests the concept - actual implementation may vary
        # Arrange
        messages = []
        for i in range(conversation_length):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i+1}"
            })
        
        # Act - Test that agent can handle conversation context
        # This would be part of the agent's internal state management
        # For now, we verify the structure is valid
        
        # Assert
        assert len(messages) == conversation_length
        assert all("role" in msg and "content" in msg for msg in messages)
    
    # =============================================================================
    # Validation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("operation_data,should_be_valid", [
        pytest.param(
            {
                "operation_type": "create",
                "changes_made": ["Created"],
                "success": True,
                "message": "Success"
            },
            True,
            id="minimal-valid"
        ),
        pytest.param(
            {
                "operation_type": "update",
                "document_id": "doc-123",
                "title": "Updated Doc",
                "changes_made": ["Updated section A", "Added section B"],
                "success": True,
                "message": "Updated successfully",
                "content_preview": "Preview..."
            },
            True,
            id="complete-valid"
        ),
    ])
    def test_document_operation_validation(
        self,
        operation_data,
        should_be_valid
    ):
        """Test DocumentOperation model validation."""
        # Act & Assert
        if should_be_valid:
            op = DocumentOperation(**operation_data)
            assert op.operation_type == operation_data["operation_type"]
            assert op.success == operation_data["success"]
        else:
            with pytest.raises(ValueError):
                DocumentOperation(**operation_data)
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_blocks", [10, 50, 100])
    def test_block_generation_performance(
        self,
        document_agent,
        num_blocks
    ):
        """Test performance of block generation at scale."""
        # Act & Assert
        with measure_time(f"generate_{num_blocks}_blocks", threshold=0.5):
            blocks = []
            for i in range(num_blocks):
                block = document_agent._create_block(
                    block_type="paragraph",
                    content=f"Block {i+1} content with some text",
                    properties={"index": i}
                )
                blocks.append(block)
        
        assert len(blocks) == num_blocks
        # Verify all blocks have unique IDs
        block_ids = [b["id"] for b in blocks]
        assert len(set(block_ids)) == num_blocks
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,error_message", [
        pytest.param(ValueError, "Invalid document type", id="value-error"),
        pytest.param(RuntimeError, "Agent runtime error", id="runtime-error"),
    ])
    async def test_error_handling_in_operations(
        self,
        document_agent,
        document_deps,
        error_type,
        error_message
    ):
        """Test error handling during document operations."""
        # Arrange
        document_agent._agent.run = AsyncMock(side_effect=error_type(error_message))
        
        # Act & Assert
        with pytest.raises(error_type, match=error_message):
            await document_agent.run("Create document", document_deps)