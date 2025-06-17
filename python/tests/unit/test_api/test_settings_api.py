"""Unit tests for Settings API endpoints with enhanced patterns."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
import os

from src.api.settings_api import router
from tests.fixtures.test_helpers import assert_fields_equal


@pytest.mark.unit
@pytest.mark.standard
class TestSettingsAPI:
    """Unit tests for Settings API endpoints."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def mock_credential_service(self):
        """Mock credential service."""
        with patch('src.api.settings_api.credential_service') as mock:
            mock.get_openai_api_key = MagicMock(return_value="test-key-123")
            mock.set_openai_api_key = MagicMock()
            mock.get_all_credentials = MagicMock(return_value={})
            mock.set_credential = MagicMock()
            mock.delete_credential = MagicMock()
            yield mock
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def sample_credentials(self):
        """Sample credentials data."""
        return {
            "OPENAI_API_KEY": "sk-test123",
            "ANTHROPIC_API_KEY": "ak-test456",
            "GITHUB_TOKEN": "ghp_test789",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "eyJtest123"
        }
    
    # =============================================================================
    # OpenAI Key Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("existing_key,expected_masked", [
        pytest.param(None, None, id="no-key"),
        pytest.param("sk-test123", "sk-...123", id="short-key"),
        pytest.param("sk-proj-verylongkeyhere123456789", "sk-...789", id="long-key"),
    ])
    def test_get_openai_api_key(
        self,
        test_client,
        mock_credential_service,
        existing_key,
        expected_masked
    ):
        """Test getting OpenAI API key with masking."""
        # Arrange
        mock_credential_service.get_openai_api_key.return_value = existing_key
        
        # Act
        response = test_client.get("/api/settings/openai-key")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        if existing_key:
            assert result["exists"] is True
            assert result["masked_key"] == expected_masked
        else:
            assert result["exists"] is False
            assert result["masked_key"] is None
    
    @pytest.mark.parametrize("api_key,should_succeed", [
        pytest.param("sk-valid123", True, id="valid-key"),
        pytest.param("", False, id="empty-key"),
        pytest.param(None, False, id="null-key"),
    ])
    def test_set_openai_api_key(
        self,
        test_client,
        mock_credential_service,
        api_key,
        should_succeed
    ):
        """Test setting OpenAI API key."""
        # Arrange
        request_data = {"api_key": api_key} if api_key is not None else {}
        
        # Act
        response = test_client.post("/api/settings/openai-key", json=request_data)
        
        # Assert
        if should_succeed:
            assert response.status_code == 200
            assert response.json()["success"] is True
            mock_credential_service.set_openai_api_key.assert_called_once_with(api_key)
        else:
            assert response.status_code in [400, 422]
    
    def test_delete_openai_api_key(self, test_client, mock_credential_service):
        """Test deleting OpenAI API key."""
        # Act
        response = test_client.delete("/api/settings/openai-key")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_credential_service.set_openai_api_key.assert_called_once_with(None)
    
    # =============================================================================
    # General Credentials Management Tests
    # =============================================================================
    
    @pytest.mark.parametrize("credentials", [
        pytest.param({}, id="no-credentials"),
        pytest.param({"KEY1": "value1"}, id="single-credential"),
        pytest.param({
            "OPENAI_API_KEY": "sk-test",
            "GITHUB_TOKEN": "ghp-test",
            "CUSTOM_KEY": "custom-value"
        }, id="multiple-credentials"),
    ])
    def test_get_all_credentials(
        self,
        test_client,
        mock_credential_service,
        credentials
    ):
        """Test getting all credentials with masking."""
        # Arrange
        mock_credential_service.get_all_credentials.return_value = credentials
        
        # Act
        response = test_client.get("/api/settings/credentials")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "credentials" in result
        
        # Verify all keys are masked
        for key, masked_value in result["credentials"].items():
            assert key in credentials
            if credentials[key]:
                assert masked_value.endswith("..." + credentials[key][-3:])
                assert not masked_value == credentials[key]  # Ensure it's actually masked
    
    @pytest.mark.parametrize("credential_data,expected_status", [
        pytest.param(
            {"key": "API_KEY", "value": "test123"},
            200,
            id="valid-credential"
        ),
        pytest.param(
            {"key": "", "value": "test"},
            422,
            id="empty-key"
        ),
        pytest.param(
            {"key": "KEY", "value": ""},
            200,  # Empty value allowed (for deletion)
            id="empty-value"
        ),
        pytest.param(
            {"key": "VERY_LONG_KEY_NAME_THAT_EXCEEDS_LIMITS" * 10, "value": "test"},
            422,
            id="key-too-long"
        ),
    ])
    def test_set_credential(
        self,
        test_client,
        mock_credential_service,
        credential_data,
        expected_status
    ):
        """Test setting individual credentials."""
        # Act
        response = test_client.post("/api/settings/credentials", json=credential_data)
        
        # Assert
        assert response.status_code == expected_status
        
        if expected_status == 200:
            assert response.json()["success"] is True
            mock_credential_service.set_credential.assert_called_once_with(
                credential_data["key"],
                credential_data["value"]
            )
    
    @pytest.mark.parametrize("key_to_delete", [
        "OPENAI_API_KEY",
        "CUSTOM_CREDENTIAL",
        "GITHUB_TOKEN",
    ])
    def test_delete_credential(
        self,
        test_client,
        mock_credential_service,
        key_to_delete
    ):
        """Test deleting individual credentials."""
        # Act
        response = test_client.delete(f"/api/settings/credentials/{key_to_delete}")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_credential_service.delete_credential.assert_called_once_with(key_to_delete)
    
    # =============================================================================
    # Environment Variable Tests
    # =============================================================================
    
    @pytest.mark.parametrize("env_vars", [
        pytest.param({}, id="no-env-vars"),
        pytest.param({
            "OPENAI_API_KEY": "from-env",
            "DATABASE_URL": "postgres://..."
        }, id="with-env-vars"),
    ])
    def test_credentials_include_env_vars(
        self,
        test_client,
        mock_credential_service,
        env_vars,
        monkeypatch
    ):
        """Test that environment variables are included in credentials."""
        # Arrange
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Simulate credential service returning env vars
        mock_credential_service.get_all_credentials.return_value = env_vars
        
        # Act
        response = test_client.get("/api/settings/credentials")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        for key in env_vars:
            assert key in result["credentials"]
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("error_type,endpoint,method", [
        pytest.param(
            Exception("Database error"),
            "/api/settings/openai-key",
            "GET",
            id="get-key-error"
        ),
        pytest.param(
            Exception("Write failed"),
            "/api/settings/openai-key",
            "POST",
            id="set-key-error"
        ),
        pytest.param(
            Exception("Service unavailable"),
            "/api/settings/credentials",
            "GET",
            id="get-credentials-error"
        ),
    ])
    def test_error_handling(
        self,
        test_client,
        mock_credential_service,
        error_type,
        endpoint,
        method
    ):
        """Test error handling for various failure scenarios."""
        # Arrange
        if method == "GET" and "openai-key" in endpoint:
            mock_credential_service.get_openai_api_key.side_effect = error_type
        elif method == "POST" and "openai-key" in endpoint:
            mock_credential_service.set_openai_api_key.side_effect = error_type
        elif method == "GET" and "credentials" in endpoint:
            mock_credential_service.get_all_credentials.side_effect = error_type
        
        # Act
        if method == "GET":
            response = test_client.get(endpoint)
        elif method == "POST":
            response = test_client.post(endpoint, json={"api_key": "test"})
        
        # Assert
        assert response.status_code == 500
        assert "error" in response.json() or "detail" in response.json()
    
    # =============================================================================
    # Security Tests
    # =============================================================================
    
    def test_credentials_always_masked_in_responses(
        self,
        test_client,
        mock_credential_service,
        sample_credentials
    ):
        """Test that credentials are never returned in plain text."""
        # Arrange
        mock_credential_service.get_all_credentials.return_value = sample_credentials
        
        # Act
        response = test_client.get("/api/settings/credentials")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        # Ensure no actual credential values are in the response
        response_text = response.text
        for key, value in sample_credentials.items():
            assert value not in response_text  # Full value should never appear
            
            # But masked version should be there
            masked = result["credentials"].get(key)
            assert masked is not None
            assert masked != value
            assert "..." in masked
    
    @pytest.mark.parametrize("sensitive_key", [
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "KEY",
        "PRIVATE",
    ])
    def test_sensitive_credential_names_handled(
        self,
        test_client,
        mock_credential_service,
        sensitive_key
    ):
        """Test that credentials with sensitive names are properly masked."""
        # Arrange
        credentials = {
            f"MY_{sensitive_key}": "sensitive-value-12345",
            f"{sensitive_key}_API": "another-sensitive-67890"
        }
        mock_credential_service.get_all_credentials.return_value = credentials
        
        # Act
        response = test_client.get("/api/settings/credentials")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        
        for key, masked in result["credentials"].items():
            # Should be masked regardless of key name
            assert "..." in masked
            assert not masked.startswith("sensitive")
    
    # =============================================================================
    # Validation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("invalid_request", [
        pytest.param(
            {"wrong_field": "value"},
            id="wrong-field-name"
        ),
        pytest.param(
            {"api_key": 12345},  # Wrong type
            id="non-string-key"
        ),
        pytest.param(
            {"api_key": "x" * 1000},  # Too long
            id="key-too-long"
        ),
    ])
    def test_request_validation(
        self,
        test_client,
        mock_credential_service,
        invalid_request
    ):
        """Test request validation for invalid inputs."""
        # Act
        response = test_client.post("/api/settings/openai-key", json=invalid_request)
        
        # Assert
        assert response.status_code in [400, 422]
        assert "detail" in response.json() or "error" in response.json()