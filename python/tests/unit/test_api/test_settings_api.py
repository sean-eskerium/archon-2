"""Unit tests for Settings API endpoints."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.api.settings_api import router, SetOpenAIKeyRequest, CredentialRequest


class TestSettingsAPI:
    """Unit tests for Settings API endpoints."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def mock_credential_service(self):
        """Mock credential service."""
        return AsyncMock()
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def sample_credential(self):
        """Sample credential data."""
        return {
            "key": "test_api_key",
            "value": "sk-test123",
            "is_encrypted": True,
            "category": "api_keys",
            "description": "Test API key"
        }
    
    @pytest.mark.unit
    @patch('src.api.settings_api.get_supabase_client')
    def test_openai_key_management(self, mock_get_client, test_client, mock_supabase_client):
        """Test OpenAI API key CRUD operations."""
        mock_get_client.return_value = mock_supabase_client
        
        # Test GET status - no key configured
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        response = test_client.get("/api/openai-key/status")
        assert response.status_code == 200
        assert response.json()["configured"] is False
        
        # Test POST - set new key
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"key_name": "openai_api_key", "key_value": "sk-test123"}]
        )
        
        response = test_client.post("/api/openai-key", json={"api_key": "sk-test123"})
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Test DELETE - remove key
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"key_name": "openai_api_key"}]
        )
        
        response = test_client.delete("/api/openai-key")
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.unit
    @patch('src.api.settings_api.credential_service')
    def test_credential_encryption_decryption(self, mock_cred_service, test_client):
        """Test credential encryption and decryption functionality."""
        # Mock credential service methods
        mock_cred_service.set_credential = AsyncMock(return_value=True)
        mock_cred_service.get_credential = AsyncMock(return_value="decrypted_value")
        
        # Test creating encrypted credential
        credential_data = {
            "key": "secret_key",
            "value": "sensitive_data",
            "is_encrypted": True,
            "category": "secrets"
        }
        
        response = test_client.post("/api/credentials", json=credential_data)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "encrypted and saved" in response.json()["message"]
        
        # Verify encryption was requested
        mock_cred_service.set_credential.assert_called_with(
            key="secret_key",
            value="sensitive_data",
            is_encrypted=True,
            category="secrets",
            description=None
        )
    
    @pytest.mark.unit
    @patch('src.api.settings_api.credential_service')
    def test_credential_category_filtering(self, mock_cred_service, test_client):
        """Test filtering credentials by category."""
        # Mock credentials with different categories
        from src.credential_service import CredentialItem
        
        mock_credentials = [
            CredentialItem(
                key="api_key_1",
                value="value1",
                is_encrypted=False,
                category="api_keys"
            ),
            CredentialItem(
                key="api_key_2",
                value="value2",
                is_encrypted=False,
                category="api_keys"
            ),
            CredentialItem(
                key="db_password",
                value="value3",
                is_encrypted=True,
                category="database"
            )
        ]
        
        mock_cred_service.list_all_credentials = AsyncMock(return_value=mock_credentials)
        
        # Test listing all credentials
        response = test_client.get("/api/credentials")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test filtering by category
        response = test_client.get("/api/credentials?category=api_keys")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(cred["category"] == "api_keys" for cred in response.json())
    
    @pytest.mark.unit
    @patch('src.api.settings_api.credential_service')
    def test_credential_crud_operations(self, mock_cred_service, test_client, sample_credential):
        """Test Create, Read, Update, Delete operations for credentials."""
        # Mock service methods
        mock_cred_service.set_credential = AsyncMock(return_value=True)
        mock_cred_service.get_credential = AsyncMock(return_value=sample_credential["value"])
        mock_cred_service.delete_credential = AsyncMock(return_value=True)
        
        # CREATE
        response = test_client.post("/api/credentials", json=sample_credential)
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # READ
        response = test_client.get(f"/api/credentials/{sample_credential['key']}")
        assert response.status_code == 200
        assert response.json()["value"] == sample_credential["value"]
        
        # UPDATE
        update_data = {"value": "new_value", "category": "updated_category"}
        response = test_client.put(f"/api/credentials/{sample_credential['key']}", json=update_data)
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # DELETE
        response = test_client.delete(f"/api/credentials/{sample_credential['key']}")
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.unit
    @patch('src.api.settings_api.get_supabase_client')
    def test_database_metrics_endpoint(self, mock_get_client, test_client, mock_supabase_client):
        """Test database metrics retrieval."""
        mock_get_client.return_value = mock_supabase_client
        
        # Mock table count responses
        mock_supabase_client.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(count=10),  # projects
            MagicMock(count=25),  # tasks
            MagicMock(count=100), # crawled_pages
            MagicMock(count=5)    # credentials
        ]
        
        response = test_client.get("/api/database/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tables"]["projects"] == 10
        assert data["tables"]["tasks"] == 25
        assert data["tables"]["crawled_pages"] == 100
        assert data["tables"]["credentials"] == 5
        assert data["total_records"] == 140
    
    @pytest.mark.unit
    @patch('src.api.settings_api.credential_service')
    def test_credential_not_found_error(self, mock_cred_service, test_client):
        """Test 404 error for non-existent credential."""
        mock_cred_service.get_credential = AsyncMock(return_value=None)
        
        response = test_client.get("/api/credentials/non_existent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["error"]
    
    @pytest.mark.unit
    @patch('src.api.settings_api.initialize_credentials')
    def test_initialize_credentials_endpoint(self, mock_init_creds, test_client):
        """Test credentials initialization endpoint."""
        mock_init_creds.return_value = None
        
        response = test_client.post("/api/credentials/initialize")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "reloaded" in response.json()["message"]
        mock_init_creds.assert_called_once()
    
    @pytest.mark.unit
    def test_health_check_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "settings"