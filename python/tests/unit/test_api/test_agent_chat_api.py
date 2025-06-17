"""Unit tests for Agent Chat API endpoints."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import uuid
from fastapi import WebSocket
from fastapi.testclient import TestClient
from src.api.agent_chat_api import (
    router, ChatMessage, ChatRequest, CreateSessionRequest,
    ChatSession, ChatSessionManager
)


class TestChatSessionManager:
    """Unit tests for ChatSessionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create ChatSessionManager instance."""
        return ChatSessionManager()
    
    @pytest.fixture
    def sample_message(self):
        """Create sample chat message."""
        return ChatMessage(
            id=str(uuid.uuid4()),
            content="Test message",
            sender="user",
            timestamp=datetime.now(),
            agent_type="docs"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_session_docs_agent(self, manager):
        """Test creating a session with docs agent."""
        session_id = await manager.create_session(project_id="test-project", agent_type="docs")
        
        assert session_id in manager.sessions
        session = manager.sessions[session_id]
        assert session.project_id == "test-project"
        assert session.agent_type == "docs"
        assert len(session.messages) == 1
        assert "Documentation Assistant" in session.messages[0].content
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_session_rag_agent(self, manager):
        """Test creating a session with RAG agent."""
        session_id = await manager.create_session(project_id="test-project", agent_type="rag")
        
        session = manager.sessions[session_id]
        assert session.agent_type == "rag"
        assert "RAG Search Assistant" in session.messages[0].content
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_management(self, manager):
        """Test WebSocket connection management."""
        # Create session
        session_id = await manager.create_session()
        
        # Mock WebSocket
        ws = MagicMock()
        ws.send_json = AsyncMock()
        
        # Add WebSocket
        await manager.add_websocket(session_id, ws)
        assert session_id in manager.websockets
        assert ws in manager.websockets[session_id]
        
        # Remove WebSocket
        manager.remove_websocket(session_id, ws)
        assert session_id not in manager.websockets
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_broadcast_message(self, manager, sample_message):
        """Test broadcasting messages to WebSockets."""
        session_id = "test-session"
        
        # Mock WebSockets
        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Disconnected"))
        
        manager.websockets[session_id] = [ws1, ws2]
        
        # Broadcast message
        await manager.broadcast_message(session_id, sample_message)
        
        # Check ws1 received message
        ws1.send_json.assert_called_once()
        call_args = ws1.send_json.call_args[0][0]
        assert call_args["type"] == "message"
        assert call_args["data"]["content"] == "Test message"
        
        # Check ws2 was removed due to error
        assert ws2 not in manager.websockets.get(session_id, [])
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_broadcast_typing_indicator(self, manager):
        """Test broadcasting typing indicator."""
        session_id = "test-session"
        
        # Mock WebSocket
        ws = MagicMock()
        ws.send_json = AsyncMock()
        manager.websockets[session_id] = [ws]
        
        # Broadcast typing
        await manager.broadcast_typing(session_id, True)
        
        ws.send_json.assert_called_once_with({
            "type": "typing",
            "data": {"is_typing": True}
        })
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.agent_chat_api.DocumentAgent')
    async def test_process_user_message_docs(self, mock_doc_agent_class, manager):
        """Test processing user message with document agent."""
        # Setup mock
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Document created successfully"
        mock_result.changes_made = ["Created new PRD"]
        mock_result.content_preview = None
        
        mock_agent.run_conversation = AsyncMock(return_value=mock_result)
        mock_doc_agent_class.return_value = mock_agent
        
        # Create session
        session_id = await manager.create_session(agent_type="docs")
        
        # Process message
        await manager.process_user_message(session_id, "Create a PRD for authentication")
        
        # Check messages added
        session = manager.sessions[session_id]
        assert len(session.messages) == 3  # Welcome + user + agent response
        assert session.messages[-1].sender == "agent"
        assert "Document created successfully" in session.messages[-1].content
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limiting(self, manager):
        """Test request rate limiting."""
        # Set up rate limiting
        manager._max_concurrent_requests = 1
        manager._processing_requests = 1  # Already at capacity
        
        session_id = await manager.create_session()
        
        # Mock broadcast methods
        manager.broadcast_typing = AsyncMock()
        manager.broadcast_message = AsyncMock()
        
        # Try to process message when at capacity
        await manager.process_user_message(session_id, "Test message")
        
        # Should have been queued
        assert not manager._request_queue.empty()
        manager.broadcast_typing.assert_called_with(session_id, True)
    
    @pytest.mark.unit
    def test_response_caching(self, manager):
        """Test response caching mechanism."""
        cache_key = "test_key"
        response = "Cached response"
        
        # Cache response
        manager._cache_response(cache_key, response)
        
        # Retrieve cached response
        cached = manager._get_cached_response(cache_key)
        assert cached == response
        
        # Test cache size limit
        for i in range(manager._max_cache_size + 10):
            manager._cache_response(f"key_{i}", f"response_{i}")
        
        # Cache should not exceed max size
        assert len(manager._response_cache) <= manager._max_cache_size
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_queued_request_processing(self, manager):
        """Test processing of queued requests."""
        # Setup
        manager._max_concurrent_requests = 1
        session_id = await manager.create_session()
        
        # Mock the single request processor
        manager._process_single_request = AsyncMock()
        
        # Queue a request
        await manager._request_queue.put((session_id, "Test message", None))
        
        # Process queued requests
        await manager._process_queued_requests()
        
        # Should have processed the queued request
        manager._process_single_request.assert_called_once()
        assert manager._request_queue.empty()


class TestAgentChatAPIEndpoints:
    """Unit tests for Agent Chat API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager."""
        with patch('src.api.agent_chat_api.session_manager') as mock:
            yield mock
    
    @pytest.mark.unit
    def test_create_session_endpoint(self, test_client, mock_session_manager):
        """Test POST /sessions endpoint."""
        mock_session_manager.create_session = AsyncMock(return_value="session-123")
        
        request_data = {
            "project_id": "project-456",
            "agent_type": "docs"
        }
        
        response = test_client.post("/api/chat/sessions", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-123"
        assert data["success"] is True
    
    @pytest.mark.unit
    def test_get_session_endpoint(self, test_client, mock_session_manager):
        """Test GET /sessions/{session_id} endpoint."""
        # Mock session
        mock_session = MagicMock()
        mock_session.model_dump.return_value = {
            "session_id": "session-123",
            "project_id": "project-456",
            "messages": [],
            "agent_type": "docs",
            "created_at": datetime.now().isoformat()
        }
        
        mock_session_manager.sessions = {"session-123": mock_session}
        
        response = test_client.get("/api/chat/sessions/session-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["session_id"] == "session-123"
    
    @pytest.mark.unit
    def test_send_message_endpoint(self, test_client, mock_session_manager):
        """Test POST /sessions/{session_id}/messages endpoint."""
        mock_session_manager.process_user_message = AsyncMock()
        
        request_data = {
            "message": "Create a new document",
            "context": {"additional": "info"}
        }
        
        response = test_client.post("/api/chat/sessions/session-123/messages", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify process_user_message was called
        mock_session_manager.process_user_message.assert_called_once_with(
            "session-123",
            "Create a new document",
            {"additional": "info"}
        )
    
    @pytest.mark.unit
    def test_get_status_endpoint(self, test_client, mock_session_manager):
        """Test GET /status endpoint."""
        # Mock sessions
        mock_session1 = MagicMock()
        mock_session1.agent_type = "docs"
        mock_session1.messages = [MagicMock(), MagicMock()]
        
        mock_session2 = MagicMock()
        mock_session2.agent_type = "rag"
        mock_session2.messages = [MagicMock()]
        
        mock_session_manager.sessions = {
            "session1": mock_session1,
            "session2": mock_session2
        }
        mock_session_manager.websockets = {"session1": [MagicMock()]}
        
        response = test_client.get("/api/chat/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["stats"]["total_sessions"] == 2
        assert data["stats"]["active_connections"] == 1
        assert data["stats"]["sessions_by_agent"]["docs"] == 1
        assert data["stats"]["sessions_by_agent"]["rag"] == 1
    
    @pytest.mark.unit
    def test_chat_message_validation(self):
        """Test ChatMessage model validation."""
        # Valid message
        msg = ChatMessage(
            id="msg-123",
            content="Hello",
            sender="user",
            timestamp=datetime.now(),
            agent_type="docs"
        )
        
        assert msg.sender == "user"
        assert msg.agent_type == "docs"
        
        # Message without agent_type (optional)
        msg2 = ChatMessage(
            id="msg-456",
            content="Hi",
            sender="agent",
            timestamp=datetime.now()
        )
        
        assert msg2.agent_type is None
    
    @pytest.mark.unit
    def test_session_not_found(self, test_client, mock_session_manager):
        """Test handling of non-existent session."""
        mock_session_manager.sessions = {}
        
        response = test_client.get("/api/chat/sessions/non-existent")
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_lazy_agent_initialization(self, manager):
        """Test lazy initialization of agents."""
        # Agents should not be initialized until accessed
        assert manager._document_agent is None
        assert manager._rag_agent is None
        
        # Mock agent classes
        with patch('src.api.agent_chat_api.DocumentAgent') as mock_doc:
            with patch('src.api.agent_chat_api.RagAgent') as mock_rag:
                # Access document agent
                _ = manager.document_agent
                mock_doc.assert_called_once()
                
                # Access RAG agent
                _ = manager.rag_agent
                mock_rag.assert_called_once()
    
    @pytest.mark.unit
    def test_create_session_request_validation(self):
        """Test CreateSessionRequest model validation."""
        # With defaults
        req = CreateSessionRequest()
        assert req.project_id is None
        assert req.agent_type == "docs"
        
        # With custom values
        req2 = CreateSessionRequest(project_id="proj-123", agent_type="rag")
        assert req2.project_id == "proj-123"
        assert req2.agent_type == "rag"