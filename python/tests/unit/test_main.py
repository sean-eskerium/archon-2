"""Tests for main entry point module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import asyncio

from src.main import (
    app,
    lifespan,
    startup_event,
    shutdown_event,
    health_check,
    root_redirect
)


class TestMainApp:
    """Test cases for main FastAPI application."""
    
    def test_app_instance(self):
        """Test FastAPI app instance creation."""
        assert isinstance(app, FastAPI)
        assert app.title == "Archon API"
        assert app.version == "1.0.0"
    
    def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        # Check if CORS middleware is in the middleware stack
        middleware_classes = [m.__class__.__name__ for m in app.middleware]
        assert any('CORS' in name for name in middleware_classes)
    
    def test_routers_included(self):
        """Test all routers are included in the app."""
        route_paths = [route.path for route in app.routes]
        
        # Check major API endpoints are registered
        assert any('/api/projects' in path for path in route_paths)
        assert any('/api/mcp' in path for path in route_paths)
        assert any('/api/knowledge' in path for path in route_paths)
        assert any('/api/settings' in path for path in route_paths)
        assert any('/api/chat' in path for path in route_paths)


class TestLifecycleEvents:
    """Test cases for application lifecycle events."""
    
    @pytest.mark.asyncio
    @patch('src.main.configure_logfire')
    @patch('src.main.init_supabase')
    @patch('src.main.websocket_manager')
    async def test_startup_event(self, mock_ws_manager, mock_init_supabase, mock_configure_logfire):
        """Test application startup event."""
        await startup_event()
        
        mock_configure_logfire.assert_called_once()
        mock_init_supabase.assert_called_once()
        mock_ws_manager.connect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.main.websocket_manager')
    @patch('src.main.mcp_session_manager')
    async def test_shutdown_event(self, mock_mcp_manager, mock_ws_manager):
        """Test application shutdown event."""
        await shutdown_event()
        
        mock_ws_manager.disconnect.assert_called_once()
        mock_mcp_manager.cleanup_all.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.main.startup_event')
    @patch('src.main.shutdown_event')
    async def test_lifespan_context_manager(self, mock_shutdown, mock_startup):
        """Test lifespan context manager."""
        mock_startup.return_value = None
        mock_shutdown.return_value = None
        
        app_mock = Mock()
        
        async with lifespan(app_mock):
            mock_startup.assert_called_once()
            mock_shutdown.assert_not_called()
        
        mock_shutdown.assert_called_once()


class TestEndpoints:
    """Test cases for basic endpoints."""
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert data["version"] == "1.0.0"
    
    def test_root_redirect(self):
        """Test root path redirects to docs."""
        with TestClient(app) as client:
            response = client.get("/", follow_redirects=False)
            
            assert response.status_code == 307  # Temporary redirect
            assert response.headers["location"] == "/docs"
    
    def test_openapi_schema_available(self):
        """Test OpenAPI schema is available."""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            
            assert response.status_code == 200
            schema = response.json()
            assert "openapi" in schema
            assert schema["info"]["title"] == "Archon API"


class TestErrorHandling:
    """Test cases for error handling."""
    
    @pytest.mark.asyncio
    @patch('src.main.configure_logfire', side_effect=Exception("Config failed"))
    async def test_startup_error_handling(self, mock_configure):
        """Test error handling during startup."""
        with pytest.raises(Exception) as exc_info:
            await startup_event()
        
        assert "Config failed" in str(exc_info.value)
    
    def test_404_error_handling(self):
        """Test 404 error handling."""
        with TestClient(app) as client:
            response = client.get("/nonexistent-endpoint")
            
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
    
    def test_method_not_allowed(self):
        """Test 405 method not allowed."""
        with TestClient(app) as client:
            # Try POST on a GET-only endpoint
            response = client.post("/health")
            
            assert response.status_code == 405
            data = response.json()
            assert "detail" in data


class TestMiddleware:
    """Test cases for middleware configuration."""
    
    def test_request_id_middleware(self):
        """Test request ID middleware adds headers."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            # Check if request ID header is present
            assert "x-request-id" in response.headers
    
    def test_cors_headers(self):
        """Test CORS headers in response."""
        with TestClient(app) as client:
            response = client.options(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )
            
            assert "access-control-allow-origin" in response.headers
            assert "access-control-allow-methods" in response.headers
    
    @patch('src.main.log_api_request')
    @patch('src.main.log_api_response')
    def test_logging_middleware(self, mock_log_response, mock_log_request):
        """Test logging middleware logs requests and responses."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            # Verify logging was called
            assert mock_log_request.called or mock_log_response.called


class TestConfiguration:
    """Test cases for application configuration."""
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_production_configuration(self):
        """Test production environment configuration."""
        # Re-import to get fresh configuration
        from src.main import app as prod_app
        
        # In production, docs might be disabled
        assert prod_app.docs_url is None or prod_app.docs_url == "/docs"
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'development'})
    def test_development_configuration(self):
        """Test development environment configuration."""
        from src.main import app as dev_app
        
        # In development, docs should be available
        assert dev_app.docs_url == "/docs"
        assert dev_app.redoc_url == "/redoc"
    
    def test_api_versioning(self):
        """Test API versioning in routes."""
        route_paths = [route.path for route in app.routes]
        
        # Check that API routes include version prefix
        api_routes = [path for path in route_paths if path.startswith('/api/')]
        assert len(api_routes) > 0
        
        # Could check for /api/v1/ prefix if versioning is implemented
        # assert any(path.startswith('/api/v1/') for path in api_routes)