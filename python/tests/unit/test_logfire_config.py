"""Tests for Logfire configuration module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from contextlib import contextmanager

from src.logfire_config import (
    configure_logfire,
    get_logfire_instance,
    log_api_request,
    log_api_response,
    log_error,
    measure_performance
)


class TestLogfireConfiguration:
    """Test cases for Logfire configuration."""
    
    @patch.dict(os.environ, {'LOGFIRE_TOKEN': 'test-token'})
    @patch('logfire.configure')
    def test_configure_logfire_with_token(self, mock_configure):
        """Test configuring Logfire with token."""
        configure_logfire()
        
        mock_configure.assert_called_once()
        call_args = mock_configure.call_args[1]
        assert call_args['token'] == 'test-token'
        assert call_args['service_name'] == 'archon'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('logfire.configure')
    def test_configure_logfire_without_token(self, mock_configure):
        """Test configuring Logfire without token (development mode)."""
        configure_logfire()
        
        mock_configure.assert_called_once()
        call_args = mock_configure.call_args[1]
        assert 'token' not in call_args or call_args['token'] is None
        assert call_args['console']['verbose'] is True
    
    @patch('logfire.Logfire')
    def test_get_logfire_instance(self, mock_logfire_class):
        """Test getting Logfire instance."""
        mock_instance = Mock()
        mock_logfire_class.return_value = mock_instance
        
        instance = get_logfire_instance()
        
        assert instance == mock_instance
        # Test singleton behavior
        instance2 = get_logfire_instance()
        assert instance2 == instance


class TestLogfireLogging:
    """Test cases for Logfire logging functions."""
    
    @patch('src.logfire_config.logfire')
    def test_log_api_request(self, mock_logfire):
        """Test logging API requests."""
        log_api_request(
            method="POST",
            path="/api/projects",
            body={"name": "Test Project"}
        )
        
        mock_logfire.info.assert_called_once_with(
            "API Request",
            method="POST",
            path="/api/projects",
            body={"name": "Test Project"}
        )
    
    @patch('src.logfire_config.logfire')
    def test_log_api_response(self, mock_logfire):
        """Test logging API responses."""
        log_api_response(
            status_code=200,
            duration=0.123,
            path="/api/projects"
        )
        
        mock_logfire.info.assert_called_once_with(
            "API Response",
            status_code=200,
            duration=0.123,
            path="/api/projects"
        )
    
    @patch('src.logfire_config.logfire')
    def test_log_error(self, mock_logfire):
        """Test logging errors."""
        error = ValueError("Test error")
        log_error(
            error=error,
            context={"operation": "create_project"}
        )
        
        mock_logfire.error.assert_called_once_with(
            "Error occurred",
            error=str(error),
            error_type=type(error).__name__,
            context={"operation": "create_project"}
        )


class TestPerformanceMeasurement:
    """Test cases for performance measurement."""
    
    @patch('src.logfire_config.logfire')
    def test_measure_performance_context_manager(self, mock_logfire):
        """Test performance measurement context manager."""
        mock_span = MagicMock()
        mock_logfire.span.return_value = mock_span
        
        with measure_performance("test_operation") as span:
            assert span == mock_span.__enter__.return_value
            # Simulate some work
            pass
        
        mock_logfire.span.assert_called_once_with("test_operation")
        mock_span.__enter__.assert_called_once()
        mock_span.__exit__.assert_called_once()
    
    @patch('src.logfire_config.logfire')
    def test_measure_performance_with_attributes(self, mock_logfire):
        """Test performance measurement with custom attributes."""
        mock_span = MagicMock()
        mock_logfire.span.return_value = mock_span
        
        with measure_performance(
            "database_query",
            attributes={"query": "SELECT * FROM projects", "table": "projects"}
        ) as span:
            pass
        
        mock_logfire.span.assert_called_once_with(
            "database_query",
            query="SELECT * FROM projects",
            table="projects"
        )
    
    @patch('src.logfire_config.logfire')
    def test_measure_performance_error_handling(self, mock_logfire):
        """Test performance measurement with error handling."""
        mock_span = MagicMock()
        mock_logfire.span.return_value = mock_span
        
        with pytest.raises(ValueError):
            with measure_performance("failing_operation") as span:
                raise ValueError("Operation failed")
        
        # Ensure span context manager properly exits even on error
        mock_span.__enter__.assert_called_once()
        mock_span.__exit__.assert_called_once()


class TestLogfireIntegration:
    """Test cases for Logfire integration scenarios."""
    
    @patch('src.logfire_config.logfire')
    def test_structured_logging(self, mock_logfire):
        """Test structured logging with various data types."""
        log_api_request(
            method="GET",
            path="/api/projects/123",
            headers={"Authorization": "Bearer ***"},
            query_params={"include": "tasks,documents"}
        )
        
        call_args = mock_logfire.info.call_args
        assert call_args[0][0] == "API Request"
        kwargs = call_args[1]
        assert kwargs['method'] == "GET"
        assert kwargs['headers']['Authorization'] == "Bearer ***"
        assert kwargs['query_params']['include'] == "tasks,documents"
    
    @patch('src.logfire_config.logfire')
    def test_performance_metrics_aggregation(self, mock_logfire):
        """Test aggregating performance metrics."""
        # Simulate multiple operations
        operations = [
            ("db_query", 0.050),
            ("api_call", 0.120),
            ("cache_lookup", 0.005)
        ]
        
        for op_name, duration in operations:
            log_api_response(
                status_code=200,
                duration=duration,
                path=f"/test/{op_name}"
            )
        
        assert mock_logfire.info.call_count == 3
        
        # Verify each operation was logged
        for i, (op_name, duration) in enumerate(operations):
            call_args = mock_logfire.info.call_args_list[i]
            assert call_args[1]['duration'] == duration
            assert op_name in call_args[1]['path']