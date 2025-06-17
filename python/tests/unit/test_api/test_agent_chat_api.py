"""Unit tests for Agent Chat API endpoints with enhanced patterns."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import json
from datetime import datetime, timedelta

from src.api.agent_chat_api import router
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import assert_fields_equal, measure_time


@pytest.mark.unit
@pytest.mark.standard
class TestAgentChatAPI:
    """Unit tests for Agent Chat API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_base_agent(self):
        """Mock base agent."""
        agent = MagicMock()
        agent.chat = AsyncMock()
        agent.stream_chat = AsyncMock()
        agent.get_conversation_history = MagicMock(return_value=[])
        agent.clear_conversation = MagicMock()
        return agent
    
    @pytest.fixture
    def mock_document_agent(self):
        """Mock document agent."""
        agent = MagicMock()
        agent.chat = AsyncMock()
        agent.stream_chat = AsyncMock()
        agent.analyze_document = AsyncMock()
        agent.get_conversation_history = MagicMock(return_value=[])
        return agent
    
    @pytest.fixture
    def mock_rag_agent(self):
        """Mock RAG agent."""
        agent = MagicMock()
        agent.chat = AsyncMock()
        agent.stream_chat = AsyncMock()
        agent.search_and_answer = AsyncMock()
        agent.get_sources = AsyncMock()
        return agent
    
    @pytest.fixture
    def make_chat_message(self):
        """Factory for creating chat messages."""
        def _make_message(
            message_id: Optional[str] = None,
            role: str = "user",
            content: str = "Test message",
            timestamp: Optional[str] = None,
            metadata: Optional[Dict] = None
        ) -> Dict:
            return {
                "id": message_id or f"msg-{uuid.uuid4().hex[:8]}",
                "role": role,
                "content": content,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
        return _make_message
    
    @pytest.fixture
    def make_conversation(self):
        """Factory for creating conversation data."""
        def _make_conversation(
            conversation_id: Optional[str] = None,
            agent_type: str = "base",
            messages: Optional[List[Dict]] = None,
            created_at: Optional[str] = None
        ) -> Dict:
            return {
                "id": conversation_id or f"conv-{uuid.uuid4().hex[:8]}",
                "agent_type": agent_type,
                "messages": messages or [],
                "created_at": created_at or datetime.utcnow().isoformat(),
                "metadata": {
                    "total_messages": len(messages or []),
                    "last_activity": datetime.utcnow().isoformat()
                }
            }
        return _make_conversation
    
    # =============================================================================
    # Basic Chat Tests
    # =============================================================================
    
    @pytest.mark.parametrize("agent_type,message", [
        pytest.param("base", "Hello, how are you?", id="base-agent-greeting"),
        pytest.param("document", "Analyze this document", id="document-agent-request"),
        pytest.param("rag", "What is the capital of France?", id="rag-agent-question"),
    ])
    @patch('src.api.agent_chat_api.base_agent')
    @patch('src.api.agent_chat_api.document_agent')
    @patch('src.api.agent_chat_api.rag_agent')
    async def test_chat_with_different_agents(
        self,
        mock_rag,
        mock_doc,
        mock_base,
        test_client,
        mock_base_agent,
        mock_document_agent,
        mock_rag_agent,
        agent_type,
        message
    ):
        """Test chat functionality with different agent types."""
        # Arrange
        mock_base.return_value = mock_base_agent
        mock_doc.return_value = mock_document_agent
        mock_rag.return_value = mock_rag_agent
        
        response_content = f"Response from {agent_type} agent"
        
        if agent_type == "base":
            mock_base_agent.chat.return_value = response_content
        elif agent_type == "document":
            mock_document_agent.chat.return_value = response_content
        elif agent_type == "rag":
            mock_rag_agent.chat.return_value = response_content
        
        # Act
        response = test_client.post(f"/api/agent/{agent_type}/chat", json={
            "message": message,
            "conversation_id": "test-conv-123"
        })
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["response"] == response_content
        assert result["conversation_id"] == "test-conv-123"
        assert "timestamp" in result
    
    # =============================================================================
    # Streaming Chat Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    @pytest.mark.parametrize("agent_type", ["base", "document", "rag"])
    @patch('src.api.agent_chat_api.base_agent')
    @patch('src.api.agent_chat_api.document_agent')
    @patch('src.api.agent_chat_api.rag_agent')
    async def test_streaming_chat(
        self,
        mock_rag,
        mock_doc,
        mock_base,
        test_client,
        mock_base_agent,
        mock_document_agent,
        mock_rag_agent,
        agent_type
    ):
        """Test streaming chat responses."""
        # Arrange
        mock_base.return_value = mock_base_agent
        mock_doc.return_value = mock_document_agent
        mock_rag.return_value = mock_rag_agent
        
        # Mock streaming response
        async def stream_response():
            chunks = ["Hello", " from", " streaming", " agent!"]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.01)
        
        if agent_type == "base":
            mock_base_agent.stream_chat.return_value = stream_response()
        elif agent_type == "document":
            mock_document_agent.stream_chat.return_value = stream_response()
        elif agent_type == "rag":
            mock_rag_agent.stream_chat.return_value = stream_response()
        
        # Act & Assert
        with test_client.websocket_connect(f"/api/agent/{agent_type}/chat/stream") as websocket:
            # Send message
            websocket.send_json({
                "message": "Test streaming",
                "conversation_id": "stream-conv-123"
            })
            
            # Receive chunks
            chunks_received = []
            while True:
                try:
                    data = websocket.receive_json(timeout=1)
                    if data["type"] == "chunk":
                        chunks_received.append(data["content"])
                    elif data["type"] == "end":
                        break
                except:
                    break
            
            assert len(chunks_received) == 4
            assert "".join(chunks_received) == "Hello from streaming agent!"
    
    # =============================================================================
    # Conversation History Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_messages", [0, 5, 20])
    @patch('src.api.agent_chat_api.get_supabase_client')
    def test_get_conversation_history(
        self,
        mock_get_client,
        test_client,
        make_chat_message,
        num_messages
    ):
        """Test retrieving conversation history."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        conversation_id = "conv-123"
        messages = []
        for i in range(num_messages):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(make_chat_message(
                role=role,
                content=f"Message {i+1}"
            ))
        
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=messages
        )
        
        # Act
        response = test_client.get(f"/api/agent/conversations/{conversation_id}/history")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["messages"]) == num_messages
        assert result["conversation_id"] == conversation_id
        assert result["total_messages"] == num_messages
    
    @pytest.mark.parametrize("page,page_size,total_messages", [
        pytest.param(1, 10, 25, id="first-page"),
        pytest.param(2, 10, 25, id="second-page"),
        pytest.param(3, 10, 25, id="last-page-partial"),
        pytest.param(1, 50, 25, id="all-in-one-page"),
    ])
    @patch('src.api.agent_chat_api.get_supabase_client')
    def test_conversation_history_pagination(
        self,
        mock_get_client,
        test_client,
        make_chat_message,
        page,
        page_size,
        total_messages
    ):
        """Test conversation history with pagination."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Calculate expected messages for this page
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_messages)
        expected_count = max(0, end_idx - start_idx)
        
        messages = [
            make_chat_message(content=f"Message {i+1}")
            for i in range(start_idx, end_idx)
        ]
        
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value = MagicMock(
            data=messages
        )
        
        # Act
        response = test_client.get(
            f"/api/agent/conversations/conv-123/history?page={page}&page_size={page_size}"
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert len(result["messages"]) == expected_count
        assert result["page"] == page
        assert result["page_size"] == page_size
    
    # =============================================================================
    # Rate Limiting Tests
    # =============================================================================
    
    @pytest.mark.parametrize("requests_per_minute,should_be_limited", [
        pytest.param(10, False, id="under-limit"),
        pytest.param(60, False, id="at-limit"),
        pytest.param(61, True, id="over-limit"),
    ])
    @patch('src.api.agent_chat_api.base_agent')
    @patch('src.api.agent_chat_api.rate_limiter')
    async def test_rate_limiting(
        self,
        mock_rate_limiter,
        mock_base,
        test_client,
        mock_base_agent,
        requests_per_minute,
        should_be_limited
    ):
        """Test rate limiting on chat endpoints."""
        # Arrange
        mock_base.return_value = mock_base_agent
        mock_base_agent.chat.return_value = "Response"
        
        # Mock rate limiter
        call_count = 0
        def check_rate_limit(*args):
            nonlocal call_count
            call_count += 1
            if call_count > 60 and should_be_limited:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            return True
        
        mock_rate_limiter.check_rate_limit = check_rate_limit
        
        # Act - Make multiple requests
        responses = []
        for i in range(min(requests_per_minute, 65)):  # Cap at 65 to avoid long tests
            response = test_client.post("/api/agent/base/chat", json={
                "message": f"Message {i}",
                "conversation_id": "rate-test"
            })
            responses.append(response)
            
            if response.status_code == 429:
                break
        
        # Assert
        if should_be_limited:
            assert any(r.status_code == 429 for r in responses)
        else:
            assert all(r.status_code == 200 for r in responses)
    
    # =============================================================================
    # Document Analysis Tests
    # =============================================================================
    
    @pytest.mark.parametrize("document_type,content_length", [
        pytest.param("text", 100, id="short-text"),
        pytest.param("text", 10000, id="long-text"),
        pytest.param("markdown", 5000, id="markdown-doc"),
        pytest.param("code", 2000, id="code-snippet"),
    ])
    @patch('src.api.agent_chat_api.document_agent')
    async def test_document_analysis(
        self,
        mock_doc,
        test_client,
        mock_document_agent,
        document_type,
        content_length
    ):
        """Test document analysis with different document types."""
        # Arrange
        mock_doc.return_value = mock_document_agent
        
        # Generate document content
        if document_type == "text":
            content = "Lorem ipsum " * (content_length // 11)
        elif document_type == "markdown":
            content = "# Title\n\n## Section\n\nContent " * (content_length // 30)
        elif document_type == "code":
            content = "def function():\n    return 'code'\n" * (content_length // 35)
        else:
            content = "Generic content " * (content_length // 16)
        
        analysis_result = {
            "summary": f"Analysis of {document_type} document",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "document_type": document_type,
            "word_count": len(content.split()),
            "confidence": 0.95
        }
        
        mock_document_agent.analyze_document.return_value = analysis_result
        
        # Act
        response = test_client.post("/api/agent/document/analyze", json={
            "content": content[:content_length],
            "document_type": document_type,
            "conversation_id": "doc-analysis-123"
        })
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["summary"] == analysis_result["summary"]
        assert len(result["key_points"]) == 3
        assert result["document_type"] == document_type
    
    # =============================================================================
    # RAG Search Tests
    # =============================================================================
    
    @pytest.mark.parametrize("search_params", [
        pytest.param(
            {"query": "What is machine learning?", "num_sources": 3},
            id="basic-search"
        ),
        pytest.param(
            {"query": "Explain quantum computing", "num_sources": 5, "threshold": 0.8},
            id="high-threshold-search"
        ),
        pytest.param(
            {"query": "Python async programming", "project_id": "proj-123", "num_sources": 3},
            id="project-scoped-search"
        ),
    ])
    @patch('src.api.agent_chat_api.rag_agent')
    async def test_rag_search_and_answer(
        self,
        mock_rag,
        test_client,
        mock_rag_agent,
        search_params
    ):
        """Test RAG search and answer functionality."""
        # Arrange
        mock_rag.return_value = mock_rag_agent
        
        # Mock search results
        sources = []
        for i in range(search_params.get("num_sources", 3)):
            sources.append({
                "id": f"source-{i}",
                "content": f"Source content {i} related to {search_params['query']}",
                "score": 0.9 - (i * 0.1),
                "metadata": {"page": f"page-{i}", "section": f"section-{i}"}
            })
        
        rag_response = {
            "answer": f"Based on the sources, here's information about {search_params['query']}...",
            "sources": sources,
            "confidence": 0.85,
            "search_time": 0.234
        }
        
        mock_rag_agent.search_and_answer.return_value = rag_response
        
        # Act
        response = test_client.post("/api/agent/rag/search", json=search_params)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "answer" in result
        assert len(result["sources"]) == search_params.get("num_sources", 3)
        assert result["confidence"] == 0.85
        assert all(s["score"] >= search_params.get("threshold", 0.0) for s in result["sources"])
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_scenario", [
        pytest.param("agent_error", id="agent-processing-error"),
        pytest.param("invalid_agent_type", id="unknown-agent"),
        pytest.param("conversation_not_found", id="missing-conversation"),
        pytest.param("websocket_disconnect", id="ws-disconnect"),
    ])
    @patch('src.api.agent_chat_api.base_agent')
    @patch('src.api.agent_chat_api.get_supabase_client')
    async def test_error_handling(
        self,
        mock_get_client,
        mock_base,
        test_client,
        mock_base_agent,
        error_scenario
    ):
        """Test error handling for various scenarios."""
        # Arrange
        mock_base.return_value = mock_base_agent
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        if error_scenario == "agent_error":
            mock_base_agent.chat.side_effect = Exception("Agent processing failed")
            response = test_client.post("/api/agent/base/chat", json={
                "message": "Test message"
            })
            expected_status = 500
            
        elif error_scenario == "invalid_agent_type":
            response = test_client.post("/api/agent/invalid/chat", json={
                "message": "Test message"
            })
            expected_status = 404
            
        elif error_scenario == "conversation_not_found":
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            response = test_client.get("/api/agent/conversations/nonexistent/history")
            expected_status = 404
            
        elif error_scenario == "websocket_disconnect":
            # This would be tested differently in a real WebSocket test
            response = test_client.post("/api/agent/base/chat", json={})
            expected_status = 422  # Invalid request
        
        # Assert
        assert response.status_code == expected_status
        assert "error" in response.json() or "detail" in response.json()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("message_length", [100, 1000, 5000])
    @patch('src.api.agent_chat_api.base_agent')
    async def test_chat_response_time(
        self,
        mock_base,
        test_client,
        mock_base_agent,
        message_length
    ):
        """Test chat response time with different message lengths."""
        # Arrange
        mock_base.return_value = mock_base_agent
        message = "Test message " * (message_length // 13)
        
        # Simulate processing time based on message length
        async def delayed_response():
            await asyncio.sleep(message_length / 10000)  # Small delay
            return f"Response to {len(message)} character message"
        
        mock_base_agent.chat.side_effect = delayed_response
        
        # Act & Assert
        with measure_time(f"chat_{message_length}_chars", threshold=1.0):
            response = test_client.post("/api/agent/base/chat", json={
                "message": message[:message_length]
            })
        
        assert response.status_code == 200
        assert "Response to" in response.json()["response"]
    
    # =============================================================================
    # Conversation Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("action", ["clear", "export", "delete"])
    @patch('src.api.agent_chat_api.get_supabase_client')
    @patch('src.api.agent_chat_api.base_agent')
    def test_conversation_management(
        self,
        mock_base,
        mock_get_client,
        test_client,
        mock_base_agent,
        action
    ):
        """Test conversation management operations."""
        # Arrange
        mock_base.return_value = mock_base_agent
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        conversation_id = "conv-to-manage"
        
        if action == "clear":
            mock_base_agent.clear_conversation.return_value = True
            response = test_client.post(f"/api/agent/conversations/{conversation_id}/clear")
            
        elif action == "export":
            # Mock conversation data
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=messages
            )
            response = test_client.get(f"/api/agent/conversations/{conversation_id}/export")
            
        elif action == "delete":
            mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": conversation_id}]
            )
            response = test_client.delete(f"/api/agent/conversations/{conversation_id}")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        if action == "clear":
            assert result["success"] is True
            mock_base_agent.clear_conversation.assert_called_once()
        elif action == "export":
            assert "messages" in result
            assert "metadata" in result
        elif action == "delete":
            assert result["success"] is True
            assert result["deleted_id"] == conversation_id
    
    # =============================================================================
    # Multi-turn Conversation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_turns", [1, 3, 5])
    @patch('src.api.agent_chat_api.base_agent')
    async def test_multi_turn_conversation(
        self,
        mock_base,
        test_client,
        mock_base_agent,
        make_chat_message,
        num_turns
    ):
        """Test multi-turn conversations."""
        # Arrange
        mock_base.return_value = mock_base_agent
        conversation_id = "multi-turn-conv"
        conversation_history = []
        
        # Simulate conversation with context
        def chat_with_context(message, conv_id, **kwargs):
            conversation_history.append(make_chat_message(role="user", content=message))
            response = f"Response {len(conversation_history)}: Acknowledging '{message}'"
            conversation_history.append(make_chat_message(role="assistant", content=response))
            return response
        
        mock_base_agent.chat.side_effect = chat_with_context
        mock_base_agent.get_conversation_history.return_value = conversation_history
        
        # Act - Have multiple turns
        for i in range(num_turns):
            response = test_client.post("/api/agent/base/chat", json={
                "message": f"User message {i+1}",
                "conversation_id": conversation_id
            })
            assert response.status_code == 200
        
        # Assert - Check conversation maintained context
        assert len(conversation_history) == num_turns * 2  # User + assistant messages
        assert mock_base_agent.chat.call_count == num_turns