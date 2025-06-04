import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.credential_service import CredentialItem


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_projects(async_client):
    mock_project = {
        "id": "1",
        "title": "Test",
        "github_repo": None,
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02",
        "prd": {},
        "docs": [],
        "features": [],
        "data": []
    }

    execute_mock = MagicMock(data=[mock_project])
    table_mock = MagicMock()
    table_mock.select.return_value.order.return_value.execute.return_value = execute_mock
    supabase_mock = MagicMock()
    supabase_mock.table.return_value = table_mock

    with patch('src.api.projects_api.get_supabase_client', return_value=supabase_mock):
        response = await async_client.get('/api/projects')

    assert response.status_code == 200
    assert response.json() == [mock_project]
    supabase_mock.table.assert_called_with('projects')


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_project(async_client):
    def dummy_bg(*args, **kwargs):
        return None

    with (
        patch('src.api.projects_api.project_creation_manager.start_creation') as start_mock,
        patch('src.api.projects_api._create_project_background', dummy_bg),
        patch('src.api.projects_api.asyncio.create_task', return_value=None) as create_task_mock,
    ):
        response = await async_client.post('/api/projects', json={"title": "New"})

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'started'
    assert 'progress_id' in data
    start_mock.assert_called_once()
    create_task_mock.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_knowledge_items(async_client):
    dummy_source = {
        'source_id': 'src1',
        'title': 'Title',
        'metadata': {'knowledge_type': 'technical', 'tags': []},
        'total_words': 0,
        'created_at': '2024-01-01',
        'updated_at': '2024-01-02'
    }
    pages_execute = MagicMock(data=[{'url': 'https://example.com'}])
    page_chain = MagicMock()
    page_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = pages_execute
    supabase_mock = MagicMock()
    supabase_mock.from_.return_value = page_chain

    crawling_context = MagicMock()
    crawling_context._initialized = True
    crawling_context.supabase_client = supabase_mock

    with patch('src.api.knowledge_api.get_crawling_context', return_value=crawling_context), \
         patch('src.api.knowledge_api.get_available_sources_direct', AsyncMock(return_value={'success': True, 'sources': [dummy_source]})):
        response = await async_client.get('/api/knowledge-items')

    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert data['items'][0]['id'] == 'src1'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_credentials(async_client):
    cred = CredentialItem(key='OPENAI_API_KEY', value='sk-test', encrypted_value=None, is_encrypted=False, category='api_keys', description='OpenAI')
    with patch('src.api.settings_api.credential_service.list_all_credentials', AsyncMock(return_value=[cred])):
        response = await async_client.get('/api/credentials')

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]['key'] == 'OPENAI_API_KEY'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_credential(async_client):
    with patch('src.api.settings_api.credential_service.set_credential', AsyncMock(return_value=True)) as set_mock:
        payload = {"key": "TEST", "value": "123", "is_encrypted": False}
        response = await async_client.post('/api/credentials', json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    set_mock.assert_awaited_once()
