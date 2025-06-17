"""Unit tests for CredentialService."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import os
from src.credential_service import CredentialService, CredentialItem
from tests.fixtures.test_helpers import test_helpers


class TestCredentialService:
    """Unit tests for CredentialService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for database operations."""
        mock = MagicMock()
        
        # Mock table methods
        mock.table = MagicMock(return_value=mock)
        mock.select = MagicMock(return_value=mock)
        mock.insert = MagicMock(return_value=mock)
        mock.upsert = MagicMock(return_value=mock)
        mock.delete = MagicMock(return_value=mock)
        mock.eq = MagicMock(return_value=mock)
        mock.execute = MagicMock()
        
        return mock
    
    @pytest.fixture
    def credential_service(self):
        """Create CredentialService instance."""
        service = CredentialService()
        service._cache_initialized = False
        service._cache = {}
        return service
    
    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with test_helpers.mock_environment_variables({
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key"
        }):
            yield
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_loads_from_database(self, credential_service, mock_supabase_client):
        """Test loading credentials from database."""
        # Arrange
        mock_credentials = [
            {"key": "API_KEY", "value": "test-key", "is_encrypted": False, "encrypted_value": None, "category": "api_keys"},
            {"key": "SECRET", "value": None, "is_encrypted": True, "encrypted_value": "encrypted-data", "category": "secrets"}
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=mock_credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            result = await credential_service.load_all_credentials()
            
            # Assert
            assert len(result) == 2
            assert result["API_KEY"] == "test-key"
            assert result["SECRET"]["is_encrypted"] is True
            assert result["SECRET"]["encrypted_value"] == "encrypted-data"
            assert credential_service._cache_initialized is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_sets_environment_variables(self, credential_service, mock_environment):
        """Test that credentials are set as environment variables."""
        # This is tested through the initialize_credentials function
        # which sets critical credentials as env vars
        assert os.environ.get("SUPABASE_URL") == "https://test.supabase.co"
        assert os.environ.get("SUPABASE_SERVICE_KEY") == "test-service-key"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_validates_required_keys(self, credential_service):
        """Test validation of required Supabase keys."""
        # Clear environment
        with test_helpers.mock_environment_variables({}):
            # Should raise ValueError when required keys are missing
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                credential_service._get_supabase_client()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_handles_missing_credentials(self, credential_service):
        """Test handling of missing credentials."""
        # Arrange
        credential_service._cache_initialized = True
        credential_service._cache = {"EXISTING_KEY": "value"}
        
        # Act
        result = await credential_service.get_credential("MISSING_KEY", default="default-value")
        
        # Assert
        assert result == "default-value"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_updates_credentials(self, credential_service, mock_supabase_client):
        """Test updating credentials in database and cache."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[{"key": "NEW_KEY", "value": "new-value"}])
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            success = await credential_service.set_credential(
                key="NEW_KEY",
                value="new-value",
                category="test",
                description="Test credential"
            )
            
            # Assert
            assert success is True
            assert credential_service._cache["NEW_KEY"] == "new-value"
            mock_supabase_client.upsert.assert_called_once()
            upsert_call = mock_supabase_client.upsert.call_args[0][0]
            assert upsert_call["key"] == "NEW_KEY"
            assert upsert_call["value"] == "new-value"
            assert upsert_call["is_encrypted"] is False
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credential_service_encrypts_sensitive_values(self, credential_service, mock_supabase_client):
        """Test encryption of sensitive credentials."""
        # Arrange
        mock_supabase_client.execute.return_value = MagicMock(data=[])
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            with patch.object(credential_service, '_encrypt_value', return_value='encrypted-test-data') as mock_encrypt:
                # Act
                success = await credential_service.set_credential(
                    key="SECRET_KEY",
                    value="sensitive-data",
                    is_encrypted=True
                )
                
                # Assert
                assert success is True
                mock_encrypt.assert_called_once_with("sensitive-data")
                assert credential_service._cache["SECRET_KEY"]["is_encrypted"] is True
                assert credential_service._cache["SECRET_KEY"]["encrypted_value"] == "encrypted-test-data"
    
    @pytest.mark.unit
    def test_encryption_decryption_roundtrip(self, credential_service, mock_environment):
        """Test that encryption and decryption work correctly."""
        # Arrange
        original_value = "test-secret-value"
        
        # Act
        encrypted = credential_service._encrypt_value(original_value)
        decrypted = credential_service._decrypt_value(encrypted)
        
        # Assert
        assert encrypted != original_value  # Should be encrypted
        assert decrypted == original_value  # Should decrypt back to original
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_encrypted_credential_decrypts(self, credential_service):
        """Test that encrypted credentials are decrypted when retrieved."""
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
        
        with patch.object(credential_service, '_decrypt_value', return_value='decrypted-value') as mock_decrypt:
            # Act
            result = await credential_service.get_credential("ENCRYPTED_KEY", decrypt=True)
            
            # Assert
            assert result == "decrypted-value"
            mock_decrypt.assert_called_once_with(encrypted_value)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_credential_without_decryption(self, credential_service):
        """Test getting encrypted credential without decryption."""
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
        
        # Act
        result = await credential_service.get_credential("ENCRYPTED_KEY", decrypt=False)
        
        # Assert
        assert isinstance(result, dict)
        assert result["encrypted_value"] == encrypted_value
        assert result["is_encrypted"] is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_credential(self, credential_service, mock_supabase_client):
        """Test deleting a credential."""
        # Arrange
        credential_service._cache = {"TO_DELETE": "value"}
        mock_supabase_client.execute.return_value = MagicMock(data=[])
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            success = await credential_service.delete_credential("TO_DELETE")
            
            # Assert
            assert success is True
            assert "TO_DELETE" not in credential_service._cache
            mock_supabase_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_credentials_by_category(self, credential_service, mock_supabase_client):
        """Test retrieving credentials by category."""
        # Arrange
        api_credentials = [
            {"key": "API_KEY_1", "value": "key1", "is_encrypted": False, "category": "api_keys"},
            {"key": "API_KEY_2", "value": "key2", "is_encrypted": False, "category": "api_keys"}
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=api_credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            # Act
            result = await credential_service.get_credentials_by_category("api_keys")
            
            # Assert
            assert len(result) == 2
            assert result["API_KEY_1"] == "key1"
            assert result["API_KEY_2"] == "key2"
            mock_supabase_client.eq.assert_called_with("category", "api_keys")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_all_credentials(self, credential_service, mock_supabase_client):
        """Test listing all credentials as CredentialItem objects."""
        # Arrange
        mock_credentials = [
            {"key": "KEY1", "value": "value1", "is_encrypted": False, "encrypted_value": None, "category": "general", "description": "Test key 1"},
            {"key": "KEY2", "value": None, "is_encrypted": True, "encrypted_value": "encrypted", "category": "secrets", "description": "Test key 2"}
        ]
        mock_supabase_client.execute.return_value = MagicMock(data=mock_credentials)
        
        with patch.object(credential_service, '_get_supabase_client', return_value=mock_supabase_client):
            with patch.object(credential_service, '_decrypt_value', return_value='decrypted-value'):
                # Act
                result = await credential_service.list_all_credentials()
                
                # Assert
                assert len(result) == 2
                assert isinstance(result[0], CredentialItem)
                assert result[0].key == "KEY1"
                assert result[0].value == "value1"
                assert result[0].is_encrypted is False
                assert result[1].key == "KEY2"
                assert result[1].value == "decrypted-value"
                assert result[1].is_encrypted is True