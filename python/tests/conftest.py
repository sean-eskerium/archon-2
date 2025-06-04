import sys, os
import pytest
import pytest_asyncio
from httpx import AsyncClient

# Add src folder to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

try:
    from api_wrapper import app
except ModuleNotFoundError:
    from src.main import app

@pytest_asyncio.fixture
async def async_client():
    """Async client for testing FastAPI endpoints"""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

@pytest.fixture 
def sync_client():
    """Sync client for testing non-async endpoints"""
    from fastapi.testclient import TestClient
    with TestClient(app) as tc:
        yield tc
