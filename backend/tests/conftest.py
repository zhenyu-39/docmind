"""pytest 配置与共享 fixtures"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.dependencies import get_db


@pytest.fixture(scope="session", autouse=True)
def mock_chroma_init():
    """全局 Mock ChromaDB 初始化，避免测试时依赖 ChromaDB 环境"""
    with patch("app.core.chroma_client.init_chroma"):
        yield


@pytest.fixture
def mock_db():
    """Mock 异步 DB session — 各测试用例可自定义其返回值"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
async def async_client(mock_db):
    """带 mock DB 的 async HTTP 客户端，自动覆盖 get_db 依赖"""
    app.dependency_overrides[get_db] = lambda: mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
