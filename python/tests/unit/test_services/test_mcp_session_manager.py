"""Unit tests for MCP Session Manager."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from src.services.mcp_session_manager import SimplifiedSessionManager, get_session_manager


class TestSimplifiedSessionManager:
    """Unit tests for SimplifiedSessionManager."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager instance."""
        return SimplifiedSessionManager(timeout=60)  # 60 second timeout for testing
    
    @pytest.fixture
    def fixed_datetime(self):
        """Fixed datetime for testing."""
        return datetime(2024, 1, 1, 12, 0, 0)
    
    @pytest.mark.unit
    def test_mcp_session_manager_creates_sessions(self, session_manager):
        """Test creating new sessions."""
        # Act
        session_id1 = session_manager.create_session()
        session_id2 = session_manager.create_session()
        
        # Assert
        assert session_id1 is not None
        assert session_id2 is not None
        assert session_id1 != session_id2  # Sessions should be unique
        assert len(session_manager.sessions) == 2
        
        # Verify UUIDs are valid format
        import uuid
        uuid.UUID(session_id1)  # Should not raise
        uuid.UUID(session_id2)  # Should not raise
    
    @pytest.mark.unit
    def test_mcp_session_manager_validates_sessions(self, session_manager):
        """Test session validation."""
        # Arrange
        session_id = session_manager.create_session()
        
        # Act & Assert - Valid session
        assert session_manager.validate_session(session_id) is True
        
        # Act & Assert - Invalid session
        assert session_manager.validate_session("invalid-session-id") is False
    
    @pytest.mark.unit
    @patch('src.services.mcp_session_manager.datetime')
    def test_mcp_session_manager_expires_sessions(self, mock_datetime, session_manager, fixed_datetime):
        """Test session expiration."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        session_id = session_manager.create_session()
        
        # Move time forward but within timeout
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=30)
        assert session_manager.validate_session(session_id) is True
        
        # Move time past timeout
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=61)
        assert session_manager.validate_session(session_id) is False
        
        # Session should be removed
        assert session_id not in session_manager.sessions
    
    @pytest.mark.unit
    @patch('src.services.mcp_session_manager.datetime')
    def test_mcp_session_manager_updates_last_seen(self, mock_datetime, session_manager, fixed_datetime):
        """Test that validation updates last seen time."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        session_id = session_manager.create_session()
        
        # Move time forward
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=30)
        
        # Act - Validate session
        session_manager.validate_session(session_id)
        
        # Assert - Last seen should be updated
        assert session_manager.sessions[session_id] == fixed_datetime + timedelta(seconds=30)
    
    @pytest.mark.unit
    @patch('src.services.mcp_session_manager.datetime')
    def test_mcp_session_manager_cleans_up_expired(self, mock_datetime, session_manager, fixed_datetime):
        """Test cleanup of expired sessions."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        
        # Create multiple sessions at different times
        session1 = session_manager.create_session()
        
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=30)
        session2 = session_manager.create_session()
        
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=45)
        session3 = session_manager.create_session()
        
        # Move time to expire first two sessions
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=91)
        
        # Act
        removed_count = session_manager.cleanup_expired_sessions()
        
        # Assert
        assert removed_count == 2
        assert session1 not in session_manager.sessions
        assert session2 not in session_manager.sessions
        assert session3 in session_manager.sessions  # Still valid
    
    @pytest.mark.unit
    def test_get_active_session_count(self, session_manager):
        """Test getting active session count."""
        # Create sessions
        session_manager.create_session()
        session_manager.create_session()
        session_manager.create_session()
        
        # Get count (should trigger cleanup first)
        count = session_manager.get_active_session_count()
        
        assert count == 3
    
    @pytest.mark.unit
    @patch('src.services.mcp_session_manager.datetime')
    def test_get_active_session_count_with_expired(self, mock_datetime, session_manager, fixed_datetime):
        """Test getting active session count excludes expired sessions."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        
        # Create sessions
        session1 = session_manager.create_session()
        session2 = session_manager.create_session()
        
        # Expire one session
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=61)
        
        # Act
        count = session_manager.get_active_session_count()
        
        # Assert
        assert count == 0  # Both sessions expired
    
    @pytest.mark.unit
    def test_custom_timeout(self):
        """Test session manager with custom timeout."""
        # Create manager with 5 minute timeout
        manager = SimplifiedSessionManager(timeout=300)
        
        assert manager.timeout == 300
        
        # Create a session
        session_id = manager.create_session()
        assert session_id in manager.sessions
    
    @pytest.mark.unit
    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton instance."""
        # Reset global instance
        import src.services.mcp_session_manager
        src.services.mcp_session_manager._session_manager = None
        
        # Get instance multiple times
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        # Should be same instance
        assert manager1 is manager2
        
        # Should have default timeout
        assert manager1.timeout == 3600  # Default 1 hour
    
    @pytest.mark.unit
    def test_concurrent_session_creation(self, session_manager):
        """Test that concurrent session creation works correctly."""
        # Create many sessions quickly
        sessions = []
        for _ in range(100):
            session_id = session_manager.create_session()
            sessions.append(session_id)
        
        # All should be unique
        assert len(set(sessions)) == 100
        assert len(session_manager.sessions) == 100
    
    @pytest.mark.unit
    @patch('src.services.mcp_session_manager.logger')
    def test_logging(self, mock_logger, session_manager):
        """Test that operations are properly logged."""
        # Create session
        session_id = session_manager.create_session()
        mock_logger.info.assert_called_with(f"Created new session: {session_id}")
        
        # Cleanup expired sessions
        session_manager.cleanup_expired_sessions()
        
        # Validate with expired session
        with patch('src.services.mcp_session_manager.datetime') as mock_dt:
            # Make session expired
            mock_dt.now.return_value = datetime.now() + timedelta(seconds=3700)
            session_manager.validate_session(session_id)
            
            # Should log expiration
            assert any("expired" in str(call) for call in mock_logger.info.call_args_list)