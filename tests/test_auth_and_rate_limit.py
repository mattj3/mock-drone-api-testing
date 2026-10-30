"""Optional API-key auth and rate limiting, switched on by environment variables."""

from __future__ import annotations

import pytest

from app import app as app_module
from utils import generate_valid_payload

KEY = "s3cret-test-key"


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "1")
    monkeypatch.setenv("API_KEY", KEY)


async def test_auth_is_off_by_default(client):
    assert (await client.post("/telemetry", json=generate_valid_payload())).status_code == 201


@pytest.mark.usefixtures("auth_on")
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
async def test_missing_or_wrong_key_is_rejected(client, headers):
    response = await client.post("/telemetry", json=generate_valid_payload(), headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "ApiKey"


@pytest.mark.usefixtures("auth_on")
async def test_correct_key_is_accepted_on_every_endpoint(client):
    h = {"X-API-Key": KEY}
    created = await client.post("/telemetry", json=generate_valid_payload(), headers=h)
    flight_id = created.json()["flight_id"]

    assert created.status_code == 201
    assert (await client.get(f"/flight/{flight_id}", headers=h)).status_code == 200
    assert (
        await client.post(f"/telemetry/{flight_id}", json=generate_valid_payload(), headers=h)
    ).status_code == 201
    assert (await client.delete("/reset", headers=h)).status_code == 200


async def test_auth_required_without_configured_key_is_a_server_error(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "true")

    response = await client.get("/flight/x", headers={"X-API-Key": "anything"})

    assert response.status_code == 503


async def test_auth_is_checked_before_rate_limit(client, auth_on, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")

    for _ in range(3):
        assert (await client.get("/flight/x")).status_code == 401


async def test_requests_over_the_limit_get_429_with_retry_after(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")

    codes = [(await client.get("/flight/x")).status_code for _ in range(4)]
    blocked = await client.get("/flight/x")

    assert codes == [404, 404, 404, 429]
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 61


async def test_rate_limit_headers_count_down_on_success(client, monkeypatch):
    # Headers ride on successful responses; an HTTPException builds a fresh response.
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")

    first = await client.post("/telemetry", json=generate_valid_payload())
    second = await client.post("/telemetry", json=generate_valid_payload())

    assert first.headers["X-RateLimit-Limit"] == "2"
    assert [first.headers["X-RateLimit-Remaining"], second.headers["X-RateLimit-Remaining"]] == [
        "1",
        "0",
    ]


async def test_limits_are_per_api_key(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("REQUIRE_API_KEY", "1")
    monkeypatch.setenv("API_KEY", KEY)

    assert (await client.get("/flight/x", headers={"X-API-Key": KEY})).status_code == 404
    assert (await client.get("/flight/x", headers={"X-API-Key": KEY})).status_code == 429


async def test_window_slides(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    clock = iter([1000.0, 1001.0, 1061.0])
    monkeypatch.setattr(app_module, "_clock", lambda: next(clock))

    assert (await client.get("/flight/x")).status_code == 404
    assert (await client.get("/flight/x")).status_code == 429
    assert (await client.get("/flight/x")).status_code == 404  # first request aged out
