"""
Basic smoke tests using pytest + httpx AsyncClient.
Run: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    r = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "password123",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "test@example.com"

    # Login
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401