"""Unit tests for CredentialService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import os
from typing import Dict, Any, List, Optional
import base64

from src.credential_service import CredentialService, CredentialItem
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_called_with_subset,
    assert_async_raises,
    DatabaseTestHelper,
    EnvironmentHelper,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestCredentialService:
    """Unit tests for CredentialService with enhanced patterns."""
    
    @pytest.fixture(scope="class")
    def db_helper(self):
        """Database test helper for creating mock results."""
        return DatabaseTestHelper()
    
    @pytest.fixture(scope="class")
    def env_helper(self):
        """Environment helper for managing test environment variables."""
        return EnvironmentHelper()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client with chained method support."""
        mock = MagicMock()
        
        # Setup chainable methods
        methods = ["table", "select", "insert", "upsert", "delete", 
                  "eq", "execute"]
        
        for method in methods:
            setattr(mock, method, MagicMock(return_value=mock))
        
        return mock
    
    @pytest.fixture
    def credential_service(self):
        """Create CredentialService instance with clean state."""
        service = CredentialService()
        service._cache_initialized = False
        service._cache = {}
        return service
    
    @pytest.fixture
    def mock_environment(self, monkeypatch):
        """Mock environment variables for tests."""
        env_vars = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key",
            "ENCRYPTION_KEY": base64.urlsafe_b64encode(b"test-encryption-key-32-bytes---").decode()
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        yield
        for key in env_vars:
            monkeypatch.delenv(key, raising=False)
    
    @pytest.fixture
    def make_credential_data(self):
        """Factory for creating credential test data."""
        def _make_credential(
            key: str = None,
            value: str = None,
            is_encrypted: bool = False,
            category: str = "general",
            description: str = None
        ) -> Dict[str, Any]:
            key = key or f"TEST_KEY_{IDGenerator.generate('key')}"
            return {
                "key": key,
                "value": value if not is_encrypted else None,
                "is_encrypted": is_encrypted,
                "encrypted_value": "encrypted-data" if is_encrypted else None,
                "category": category,
                "description": description or f"Test credential for {key}"
            }
        return _make_credential
    
    # =============================================================================
    # Credential Loading Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("credential_count,has_encrypted", [
        pytest.param(0, False, id="no-credentials"),
        pytest.param(3, False, id="plain-credentials"),
        pytest.param(5, True, id="mixed-credentials"),
    ])
    async def test_load_all_credentials(
        self,
        credential_service,
        mock_supabase_client,
        make_credential_data,
        db_helper,
        credential_count,
        has_encrypted
    ):
        """Test loading credentials from database with various configurations."""
        # Arrange
        credentials = []
        for i in range(credential_count):
            is_encrypted = has_encrypted and i % 2 == 0
            cred = make_credential_data(
                key=f"CRED_{i}",
                value=f"value_{i}" if not is_encrypted else None,
                is_encrypted=is_encrypted,
                category=["api_keys", "secrets", "general"][i % 3]
            )
            credentials.append(cred)
        
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            result = await credential_service.load_all_credentials()
            
            # Assert
            assert len(result) == credential_count
            assert credential_service._cache_initialized is True
            
            for cred in credentials:
                key = cred["key"]
                assert key in result
                
                if cred["is_encrypted"]:
                    assert isinstance(result[key], dict)
                    assert result[key]["is_encrypted"] is True
                    assert result[key]["encrypted_value"] == cred["encrypted_value"]
                else:
                    assert result[key] == cred["value"]
    
    # =============================================================================
    # Environment Variable Tests
    # =============================================================================
    
    @pytest.mark.parametrize("env_vars,should_succeed", [
        pytest.param(
            {"SUPABASE_URL": "https://test.co", "SUPABASE_SERVICE_KEY": "key"},
            True,
            id="valid-env"
        ),
        pytest.param(
            {"SUPABASE_URL": "https://test.co"},
            False,
            id="missing-service-key"
        ),
        pytest.param(
            {"SUPABASE_SERVICE_KEY": "key"},
            False,
            id="missing-url"
        ),
        pytest.param(
            {},
            False,
            id="no-env-vars"
        ),
    ])
    def test_validate_required_environment_variables(
        self,
        credential_service,
        monkeypatch,
        env_vars,
        should_succeed
    ):
        """Test validation of required Supabase environment variables."""
        # Arrange
        # Clear existing env vars
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]:
            monkeypatch.delenv(key, raising=False)
        
        # Set test env vars
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Act & Assert
        if should_succeed:
            # Should not raise
            client = credential_service._get_supabase_client()
            assert client is not None
        else:
            # Should raise ValueError
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                credential_service._get_supabase_client()
    
    # =============================================================================
    # Credential CRUD Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("key,value,category,is_encrypted", [
        pytest.param("API_KEY", "test-key-123", "api_keys", False, id="plain-api-key"),
        pytest.param("SECRET", "sensitive-data", "secrets", True, id="encrypted-secret"),
        pytest.param("CONFIG", "app-config", "general", False, id="general-config"),
        pytest.param("TOKEN", "auth-token", "auth", True, id="encrypted-token"),
    ])
    async def test_set_credential_with_various_types(
        self,
        credential_service,
        mock_supabase_client,
        db_helper,
        key,
        value,
        category,
        is_encrypted
    ):
        """Test setting credentials with different configurations."""
        # Arrange
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result([{
            "key": key,
            "value": value if not is_encrypted else None,
            "is_encrypted": is_encrypted,
            "encrypted_value": "encrypted-data" if is_encrypted else None,
            "category": category
        }])
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            if is_encrypted:
                with patch.object(credential_service, '_encrypt_value', return_value='encrypted-data'):
                    # Act
                    success = await credential_service.set_credential(
                        key=key,
                        value=value,
                        category=category,
                        is_encrypted=is_encrypted
                    )
            else:
                # Act
                success = await credential_service.set_credential(
                    key=key,
                    value=value,
                    category=category,
                    is_encrypted=is_encrypted
                )
            
            # Assert
            assert success is True
            mock_supabase_client.upsert.assert_called_once()
            
            upsert_data = mock_supabase_client.upsert.call_args[0][0]
            assert upsert_data["key"] == key
            assert upsert_data["category"] == category
            assert upsert_data["is_encrypted"] == is_encrypted
            
            if is_encrypted:
                assert upsert_data["value"] is None
                assert upsert_data["encrypted_value"] == "encrypted-data"
                assert credential_service._cache[key]["is_encrypted"] is True
            else:
                assert upsert_data["value"] == value
                assert upsert_data["encrypted_value"] is None
                assert credential_service._cache[key] == value
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("exists,default_value", [
        pytest.param(True, None, id="existing-no-default"),
        pytest.param(True, "default", id="existing-with-default"),
        pytest.param(False, "default", id="missing-with-default"),
        pytest.param(False, None, id="missing-no-default"),
    ])
    async def test_get_credential_with_defaults(
        self,
        credential_service,
        exists,
        default_value
    ):
        """Test getting credentials with various default value scenarios."""
        # Arrange
        credential_service._cache_initialized = True
        if exists:
            credential_service._cache["TEST_KEY"] = "actual-value"
        
        # Act
        result = await credential_service.get_credential("TEST_KEY", default=default_value)
        
        # Assert
        if exists:
            assert result == "actual-value"
        else:
            assert result == default_value
    
    @pytest.mark.asyncio
    async def test_delete_credential(
        self,
        credential_service,
        mock_supabase_client,
        db_helper
    ):
        """Test deleting credentials from database and cache."""
        # Arrange
        credential_service._cache = {"TO_DELETE": "value", "TO_KEEP": "other-value"}
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result([])
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            success = await credential_service.delete_credential("TO_DELETE")
            
            # Assert
            assert success is True
            assert "TO_DELETE" not in credential_service._cache
            assert "TO_KEEP" in credential_service._cache
            mock_supabase_client.delete.assert_called_once()
            mock_supabase_client.eq.assert_called_with("key", "TO_DELETE")
    
    # =============================================================================
    # Encryption/Decryption Tests
    # =============================================================================
    
    @pytest.mark.parametrize("original_value", [
        pytest.param("simple-secret", id="simple-text"),
        pytest.param("complex!@#$%^&*()_+-=[]{}|;:,.<>?", id="special-chars"),
        pytest.param("multi\nline\nvalue", id="multiline"),
        pytest.param("🔐 Unicode secret 🔑", id="unicode"),
    ])
    def test_encryption_decryption_roundtrip(
        self,
        credential_service,
        mock_environment,
        original_value
    ):
        """Test that various values can be encrypted and decrypted correctly."""
        # Act
        encrypted = credential_service._encrypt_value(original_value)
        decrypted = credential_service._decrypt_value(encrypted)
        
        # Assert
        assert encrypted != original_value  # Should be encrypted
        assert isinstance(encrypted, str)  # Should be base64 string
        assert decrypted == original_value  # Should decrypt back to original
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("decrypt", [True, False])
    async def test_get_encrypted_credential_decryption_control(
        self,
        credential_service,
        decrypt
    ):
        """Test controlling decryption when retrieving encrypted credentials."""
        # Arrange
        encrypted_value = "mock-encrypted-data"
        credential_service._cache_initialized = True
        credential_service._cache = {
            "ENCRYPTED_KEY": {
                "encrypted_value": encrypted_value,
                "is_encrypted": True,
                "category": "secrets"
            }
        }
        
        with patch.object(credential_service, '_decrypt_value', return_value='decrypted-value'):
            # Act
            result = await credential_service.get_credential("ENCRYPTED_KEY", decrypt=decrypt)
            
            # Assert
            if decrypt:
                assert result == "decrypted-value"
            else:
                assert isinstance(result, dict)
                assert result["encrypted_value"] == encrypted_value
                assert result["is_encrypted"] is True
    
    # =============================================================================
    # Category-based Operations Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("category,expected_count", [
        pytest.param("api_keys", 3, id="api-keys-category"),
        pytest.param("secrets", 2, id="secrets-category"),
        pytest.param("general", 1, id="general-category"),
        pytest.param("nonexistent", 0, id="empty-category"),
    ])
    async def test_get_credentials_by_category(
        self,
        credential_service,
        mock_supabase_client,
        make_credential_data,
        db_helper,
        category,
        expected_count
    ):
        """Test retrieving credentials filtered by category."""
        # Arrange
        all_credentials = [
            make_credential_data(key="API_1", category="api_keys"),
            make_credential_data(key="API_2", category="api_keys"),
            make_credential_data(key="API_3", category="api_keys"),
            make_credential_data(key="SECRET_1", category="secrets", is_encrypted=True),
            make_credential_data(key="SECRET_2", category="secrets", is_encrypted=True),
            make_credential_data(key="CONFIG_1", category="general"),
        ]
        
        filtered = [c for c in all_credentials if c["category"] == category]
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(filtered)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            result = await credential_service.get_credentials_by_category(category)
            
            # Assert
            assert len(result) == expected_count
            mock_supabase_client.eq.assert_called_with("category", category)
            
            for cred in filtered:
                assert cred["key"] in result
    
    # =============================================================================
    # Listing Operations Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("include_encrypted", [True, False])
    async def test_list_all_credentials_as_items(
        self,
        credential_service,
        mock_supabase_client,
        make_credential_data,
        db_helper,
        include_encrypted
    ):
        """Test listing all credentials as CredentialItem objects."""
        # Arrange
        credentials = [
            make_credential_data(key="KEY1", value="value1"),
            make_credential_data(key="KEY2", value="value2"),
        ]
        
        if include_encrypted:
            credentials.extend([
                make_credential_data(key="SECRET1", is_encrypted=True),
                make_credential_data(key="SECRET2", is_encrypted=True),
            ])
        
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            with patch.object(credential_service, '_decrypt_value', return_value='decrypted-value'):
                # Act
                result = await credential_service.list_all_credentials()
                
                # Assert
                expected_count = 2 if not include_encrypted else 4
                assert len(result) == expected_count
                
                for item in result:
                    assert isinstance(item, CredentialItem)
                    assert item.key is not None
                    assert item.category is not None
                    
                    # Check decryption for encrypted items
                    if item.is_encrypted:
                        assert item.value == "decrypted-value"
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("credential_count", [100, 500, 1000])
    async def test_load_credentials_performance(
        self,
        credential_service,
        mock_supabase_client,
        make_credential_data,
        db_helper,
        credential_count
    ):
        """Test performance of loading large numbers of credentials."""
        # Arrange
        credentials = []
        for i in range(credential_count):
            cred = make_credential_data(
                key=f"PERF_KEY_{i}",
                value=f"value_{i}",
                category=["api", "secret", "config"][i % 3]
            )
            credentials.append(cred)
        
        mock_supabase_client.execute.return_value = db_helper.create_mock_query_result(credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act & Assert
            with measure_time(f"load_{credential_count}_credentials", threshold=0.5):
                result = await credential_service.load_all_credentials()
            
            assert len(result) == credential_count
            assert credential_service._cache_initialized is True
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,operation", [
        pytest.param(Exception("Connection failed"), "load", id="connection-error-load"),
        pytest.param(Exception("Timeout"), "set", id="timeout-error-set"),
        pytest.param(Exception("Permission denied"), "delete", id="permission-error-delete"),
    ])
    async def test_database_error_handling(
        self,
        credential_service,
        mock_supabase_client,
        error_type,
        operation
    ):
        """Test graceful handling of database errors."""
        # Arrange
        mock_supabase_client.execute.side_effect = error_type
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act & Assert
            if operation == "load":
                with pytest.raises(Exception):
                    await credential_service.load_all_credentials()
            elif operation == "set":
                success = await credential_service.set_credential("KEY", "value")
                assert success is False
            elif operation == "delete":
                success = await credential_service.delete_credential("KEY")
                assert success is False
    
    @pytest.mark.parametrize("invalid_encrypted_data", [
        pytest.param("not-base64", id="invalid-base64"),
        pytest.param("", id="empty-string"),
        pytest.param(None, id="none-value"),
    ])
    def test_decrypt_invalid_data_handling(
        self,
        credential_service,
        mock_environment,
        invalid_encrypted_data
    ):
        """Test handling of invalid encrypted data."""
        # Act & Assert
        if invalid_encrypted_data is None:
            with pytest.raises(Exception):
                credential_service._decrypt_value(invalid_encrypted_data)
        else:
            # Should handle gracefully or raise appropriate error
            try:
                result = credential_service._decrypt_value(invalid_encrypted_data)
                # If it doesn't raise, it should return something safe
                assert result is not None
            except Exception as e:
                # Should be a specific decryption error
                assert "decrypt" in str(e).lower() or "invalid" in str(e).lower()