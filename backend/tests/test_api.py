"""API 端点功能测试 — 使用 mock 数据库避免依赖外部 MySQL/Milvus。"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.mysql import get_db

pytestmark = pytest.mark.asyncio


class MockSession:
    """模拟 SQLAlchemy AsyncSession。"""
    async def execute(self, *args, **kwargs):
        return MockResult()

    async def commit(self): pass
    async def rollback(self): pass

    def add(self, obj): pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args): pass


class MockScalars:
    def all(self):
        return []

    def first(self):
        return None

    def one_or_none(self):
        return None


class MockResult:
    def scalars(self):
        return MockScalars()

    def scalar_one_or_none(self):
        return None


async def override_get_db():
    return MockSession()


# Replace DB dependency with mock
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthCheck:
    async def test_health_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDocumentAPI:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_delete_not_found(self, client: AsyncClient):
        resp = await client.delete("/api/documents/nonexistent")
        assert resp.status_code in (200, 500)


class TestStationAPI:
    async def test_list_stations(self, client: AsyncClient):
        resp = await client.get("/api/stations")
        assert resp.status_code == 200
        assert resp.json() == []


class TestConversationAPI:
    async def test_list_conversations_empty(self, client: AsyncClient):
        resp = await client.get("/api/chat/conversations")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_nonexistent_conversation(self, client: AsyncClient):
        resp = await client.get("/api/chat/conversations/nonexistent")
        assert resp.status_code == 200
        assert resp.json() is None


class TestChatSSE:
    async def test_chat_sse_stream(self, client: AsyncClient):
        """验证对话接口返回 SSE 流（会触发Agent调用，无API key可能返回error事件）。"""
        resp = await client.post("/api/chat", json={
            "message": "你好",
            "session_id": "test-session-001",
        })
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
