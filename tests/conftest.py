"""Shared fixtures: an isolated app state and an async client for every test."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app, reset_state

_FEATURE_ENV = ("REQUIRE_API_KEY", "API_KEY", "RATE_LIMIT_PER_MINUTE")


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch: pytest.MonkeyPatch):
    """Start every test with no flights, no rate-limit history and auth/limits off."""
    for name in _FEATURE_ENV:
        monkeypatch.delenv(name, raising=False)
    reset_state()
    yield
    reset_state()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def flight_id(client: AsyncClient) -> str:
    """A freshly created flight, for tests that need one to exist."""
    from utils import generate_valid_payload

    response = await client.post("/telemetry", json=generate_valid_payload())
    assert response.status_code == 201
    return response.json()["flight_id"]
