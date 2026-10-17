"""并发性能测试 + Pydantic 模型验证。"""

from __future__ import annotations

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.mysql import get_db

pytestmark = pytest.mark.asyncio


class MockSession:
    async def execute(self, *args, **kwargs):
        return MockResult()
    async def commit(self): pass
    async def rollback(self): pass
    def add(self, obj): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass


class MockScalars:
    def all(self): return []
    def first(self): return None
    def one_or_none(self): return None


class MockResult:
    def scalars(self): return MockScalars()
    def scalar_one_or_none(self): return None


async def override_get_db():
    return MockSession()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestConcurrency:
    """验证并发请求处理能力。"""

    async def test_concurrent_health_checks(self, client: AsyncClient):
        """50并发健康检查。"""
        n = 50
        start = time.perf_counter()

        tasks = [client.get("/health") for _ in range(n)]
        responses = await asyncio.gather(*tasks)

        elapsed = time.perf_counter() - start
        success_count = sum(1 for r in responses if r.status_code == 200)

        print(f"\n--- Concurrency: Health Check ---")
        print(f"  Requests: {n}, Success: {success_count}/{n}")
        print(f"  Elapsed: {elapsed:.2f}s, QPS: {n / elapsed:.1f}")

        assert success_count == n

    async def test_concurrent_chat_requests(self, client: AsyncClient):
        """10并发对话请求。"""
        n = 10
        start = time.perf_counter()

        async def one_chat(idx: int):
            return await client.post("/api/chat", json={
                "message": f"测试消息{idx}",
                "session_id": f"perf-test-{idx}",
            })

        tasks = [one_chat(i) for i in range(n)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.perf_counter() - start
        errors = [r for r in responses if isinstance(r, BaseException)]
        success = [r for r in responses if not isinstance(r, BaseException) and r.status_code == 200]

        print(f"\n--- Concurrency: Chat SSE ---")
        print(f"  Requests: {n}, Success: {len(success)}, Errors: {len(errors)}")
        print(f"  Elapsed: {elapsed:.2f}s")

        assert len(success) + len(errors) == n


@pytest.mark.filterwarnings("ignore::pytest.PytestWarning")
class TestModelValidation:
    """Pydantic 模型校验测试。"""

    def test_chat_request_validation(self):
        from app.models.chat import ChatRequest
        req = ChatRequest(message="hello", session_id="abc123")
        assert req.message == "hello"
        assert req.session_id == "abc123"

    def test_chat_request_empty_message(self):
        from app.models.chat import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(message="", session_id="abc123")

    def test_chat_request_with_location(self):
        from app.models.chat import ChatRequest, Location
        req = ChatRequest(
            message="附近有维修点吗",
            session_id="abc",
            user_location=Location(lat=39.9042, lng=116.4074),
        )
        assert req.user_location is not None
        assert req.user_location.lat == 39.9042
