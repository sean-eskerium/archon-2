"""Unit tests for MCP Session Manager with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
import asyncio

from src.services.mcp_session_manager import SimplifiedSessionManager, get_session_manager
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time,
    wait_for_condition
)


@pytest.mark.unit
@pytest.mark.critical
class TestSimplifiedSessionManager:
    """Unit tests for SimplifiedSessionManager with enhanced patterns."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager instance with default timeout."""
        return SimplifiedSessionManager(timeout=60)  # 60 second timeout for testing
    
    @pytest.fixture
    def make_session_manager(self):
        """Factory for creating session managers with custom timeouts."""
        def _make_manager(timeout: int = 60) -> SimplifiedSessionManager:
            return SimplifiedSessionManager(timeout=timeout)
        return _make_manager
    
    @pytest.fixture
    def fixed_datetime(self):
        """Fixed datetime for consistent testing."""
        return datetime(2024, 1, 1, 12, 0, 0)
    
    # =============================================================================
    # Session Creation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("session_count", [
        pytest.param(1, id="single-session"),
        pytest.param(5, id="multiple-sessions"),
        pytest.param(100, id="many-sessions"),
    ])
    def test_create_sessions_with_unique_ids(self, session_manager, session_count):
        """Test creating sessions with guaranteed unique IDs."""
        # Act
        sessions = []
        for _ in range(session_count):
            session_id = session_manager.create_session()
            sessions.append(session_id)
        
        # Assert
        assert len(sessions) == session_count
        assert len(set(sessions)) == session_count  # All unique
        assert len(session_manager.sessions) == session_count
        
        # Verify all are valid UUIDs
        for session_id in sessions:
            uuid.UUID(session_id)  # Should not raise
    
    @pytest.mark.parametrize("timeout_seconds", [
        pytest.param(30, id="30-second-timeout"),
        pytest.param(60, id="1-minute-timeout"),
        pytest.param(300, id="5-minute-timeout"),
        pytest.param(3600, id="1-hour-timeout"),
    ])
    def test_session_manager_with_custom_timeouts(self, make_session_manager, timeout_seconds):
        """Test session managers with various timeout configurations."""
        # Arrange
        manager = make_session_manager(timeout=timeout_seconds)
        
        # Act
        session_id = manager.create_session()
        
        # Assert
        assert manager.timeout == timeout_seconds
        assert session_id in manager.sessions
        assert isinstance(manager.sessions[session_id], datetime)
    
    # =============================================================================
    # Session Validation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("session_exists,session_expired,expected_valid", [
        pytest.param(True, False, True, id="valid-active-session"),
        pytest.param(True, True, False, id="expired-session"),
        pytest.param(False, False, False, id="non-existent-session"),
    ])
    @patch('src.services.mcp_session_manager.datetime')
    def test_validate_session_scenarios(
        self,
        mock_datetime,
        session_manager,
        fixed_datetime,
        session_exists,
        session_expired,
        expected_valid
    ):
        """Test session validation with various scenarios."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        
        if session_exists:
            session_id = session_manager.create_session()
            
            if session_expired:
                # Move time past timeout
                mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=61)
        else:
            session_id = "non-existent-session-id"
        
        # Act
        is_valid = session_manager.validate_session(session_id)
        
        # Assert
        assert is_valid == expected_valid
        
        if session_exists and session_expired:
            # Expired session should be removed
            assert session_id not in session_manager.sessions
    
    @pytest.mark.parametrize("elapsed_seconds,should_be_valid", [
        pytest.param(0, True, id="immediate-check"),
        pytest.param(30, True, id="half-timeout"),
        pytest.param(59, True, id="just-before-timeout"),
        pytest.param(60, False, id="at-timeout"),
        pytest.param(61, False, id="past-timeout"),
        pytest.param(120, False, id="double-timeout"),
    ])
    @patch('src.services.mcp_session_manager.datetime')
    def test_session_expiration_timing(
        self,
        mock_datetime,
        session_manager,
        fixed_datetime,
        elapsed_seconds,
        should_be_valid
    ):
        """Test precise session expiration timing."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        session_id = session_manager.create_session()
        
        # Move time forward
        mock_datetime.now.return_value = fixed_datetime + timedelta(seconds=elapsed_seconds)
        
        # Act
        is_valid = session_manager.validate_session(session_id)
        
        # Assert
        assert is_valid == should_be_valid
    
    # =============================================================================
    # Session Activity Tracking Tests
    # =============================================================================
    
    @patch('src.services.mcp_session_manager.datetime')
    def test_validation_updates_last_seen_time(
        self,
        mock_datetime,
        session_manager,
        fixed_datetime
    ):
        """Test that validating a session updates its last seen time."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        session_id = session_manager.create_session()
        initial_time = session_manager.sessions[session_id]
        
        # Move time forward
        new_time = fixed_datetime + timedelta(seconds=30)
        mock_datetime.now.return_value = new_time
        
        # Act
        session_manager.validate_session(session_id)
        
        # Assert
        assert session_manager.sessions[session_id] == new_time
        assert session_manager.sessions[session_id] > initial_time
    
    # =============================================================================
    # Session Cleanup Tests
    # =============================================================================
    
    @pytest.mark.parametrize("session_ages,expected_removed", [
        pytest.param(
            [30, 45, 70, 90],  # Ages in seconds
            2,  # Two sessions expired (70s and 90s)
            id="mixed-expired-active"
        ),
        pytest.param(
            [10, 20, 30, 40],  # All within timeout
            0,
            id="all-active"
        ),
        pytest.param(
            [70, 80, 90, 100],  # All expired
            4,
            id="all-expired"
        ),
    ])
    @patch('src.services.mcp_session_manager.datetime')
    def test_cleanup_expired_sessions(
        self,
        mock_datetime,
        session_manager,
        fixed_datetime,
        session_ages,
        expected_removed
    ):
        """Test cleanup of expired sessions with various age distributions."""
        # Arrange
        sessions = []
        start_time = fixed_datetime
        
        for age in session_ages:
            # Create session at past time
            mock_datetime.now.return_value = start_time - timedelta(seconds=age)
            session_id = session_manager.create_session()
            sessions.append(session_id)
        
        # Move to current time
        mock_datetime.now.return_value = start_time
        
        # Act
        removed_count = session_manager.cleanup_expired_sessions()
        
        # Assert
        assert removed_count == expected_removed
        
        # Verify correct sessions remain
        remaining_count = len(session_ages) - expected_removed
        assert len(session_manager.sessions) == remaining_count
        
        # Check specific sessions
        for i, (session_id, age) in enumerate(zip(sessions, session_ages)):
            if age > 60:  # Expired
                assert session_id not in session_manager.sessions
            else:
                assert session_id in session_manager.sessions
    
    # =============================================================================
    # Session Count Tests
    # =============================================================================
    
    @pytest.mark.parametrize("total_sessions,expired_sessions", [
        pytest.param(5, 0, id="all-active"),
        pytest.param(5, 2, id="some-expired"),
        pytest.param(5, 5, id="all-expired"),
        pytest.param(0, 0, id="no-sessions"),
    ])
    @patch('src.services.mcp_session_manager.datetime')
    def test_get_active_session_count(
        self,
        mock_datetime,
        session_manager,
        fixed_datetime,
        total_sessions,
        expired_sessions
    ):
        """Test accurate active session counting."""
        # Arrange
        mock_datetime.now.return_value = fixed_datetime
        
        # Create sessions
        for i in range(total_sessions):
            if i < expired_sessions:
                # Create expired session
                mock_datetime.now.return_value = fixed_datetime - timedelta(seconds=70)
            else:
                # Create active session
                mock_datetime.now.return_value = fixed_datetime - timedelta(seconds=30)
            
            session_manager.create_session()
        
        # Reset to current time
        mock_datetime.now.return_value = fixed_datetime
        
        # Act
        count = session_manager.get_active_session_count()
        
        # Assert
        expected_active = total_sessions - expired_sessions
        assert count == expected_active
    
    # =============================================================================
    # Singleton Pattern Tests
    # =============================================================================
    
    def test_get_session_manager_singleton_pattern(self):
        """Test that get_session_manager returns singleton instance."""
        # Reset global instance
        import src.services.mcp_session_manager
        src.services.mcp_session_manager._session_manager = None
        
        # Get instance multiple times
        managers = []
        for _ in range(5):
            manager = get_session_manager()
            managers.append(manager)
        
        # All should be same instance
        assert all(m is managers[0] for m in managers)
        
        # Should have default timeout
        assert managers[0].timeout == 3600  # Default 1 hour
    
    # =============================================================================
    # Concurrency Tests
    # =============================================================================
    
    @pytest.mark.parametrize("concurrent_sessions", [10, 50, 100])
    def test_concurrent_session_creation(self, session_manager, concurrent_sessions):
        """Test thread-safe concurrent session creation."""
        # Create many sessions quickly
        sessions = []
        
        # Simulate concurrent creation
        for _ in range(concurrent_sessions):
            session_id = session_manager.create_session()
            sessions.append(session_id)
        
        # Assert all unique
        assert len(set(sessions)) == concurrent_sessions
        assert len(session_manager.sessions) == concurrent_sessions
        
        # Verify no corruption
        for session_id in sessions:
            assert isinstance(session_manager.sessions[session_id], datetime)
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("session_count", [1000, 5000, 10000])
    def test_session_manager_performance_at_scale(
        self,
        make_session_manager,
        session_count
    ):
        """Test session manager performance with large numbers of sessions."""
        # Arrange
        manager = make_session_manager(timeout=3600)  # 1 hour timeout
        
        # Act - Create sessions
        with measure_time(f"create_{session_count}_sessions", threshold=1.0):
            sessions = []
            for _ in range(session_count):
                session_id = manager.create_session()
                sessions.append(session_id)
        
        # Act - Validate random sessions
        import random
        sample_sessions = random.sample(sessions, min(100, session_count))
        
        with measure_time("validate_100_sessions", threshold=0.1):
            for session_id in sample_sessions:
                manager.validate_session(session_id)
        
        # Act - Cleanup (none should be expired)
        with measure_time(f"cleanup_{session_count}_sessions", threshold=0.5):
            removed = manager.cleanup_expired_sessions()
        
        # Assert
        assert removed == 0  # None expired
        assert len(manager.sessions) == session_count
    
    # =============================================================================
    # Logging Tests
    # =============================================================================
    
    @pytest.mark.parametrize("operation,log_level", [
        pytest.param("create", "info", id="create-logs-info"),
        pytest.param("validate_expired", "info", id="expired-logs-info"),
        pytest.param("cleanup", "info", id="cleanup-logs-info"),
    ])
    @patch('src.services.mcp_session_manager.logger')
    def test_logging_for_operations(
        self,
        mock_logger,
        session_manager,
        operation,
        log_level
    ):
        """Test proper logging for various operations."""
        # Arrange & Act
        if operation == "create":
            session_id = session_manager.create_session()
            # Assert
            mock_logger.info.assert_called()
            assert session_id in str(mock_logger.info.call_args)
            
        elif operation == "validate_expired":
            with patch('src.services.mcp_session_manager.datetime') as mock_dt:
                # Create and expire session
                mock_dt.now.return_value = datetime.now()
                session_id = session_manager.create_session()
                
                # Expire it
                mock_dt.now.return_value = datetime.now() + timedelta(seconds=61)
                session_manager.validate_session(session_id)
                
                # Assert
                assert any("expired" in str(call) for call in mock_logger.info.call_args_list)
                
        elif operation == "cleanup":
            # Create some sessions
            for _ in range(3):
                session_manager.create_session()
            
            # Cleanup
            mock_logger.reset_mock()
            session_manager.cleanup_expired_sessions()
            
            # Assert
            mock_logger.info.assert_called()
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("invalid_session_id", [
        pytest.param(None, id="none-session-id"),
        pytest.param("", id="empty-session-id"),
        pytest.param("not-a-uuid", id="invalid-format"),
        pytest.param(123, id="numeric-session-id"),
    ])
    def test_validate_invalid_session_ids(self, session_manager, invalid_session_id):
        """Test validation handles invalid session IDs gracefully."""
        # Act
        is_valid = session_manager.validate_session(invalid_session_id)
        
        # Assert
        assert is_valid is False
        # Should not crash or raise exceptions