"""Error paths: invalid bodies, unknown flights, wrong methods."""

from __future__ import annotations

import pytest

from utils import INVALID_PAYLOADS, generate_valid_payload

CASES = [pytest.param(payload, fields, id=name) for name, payload, fields in INVALID_PAYLOADS]


def _rejected_fields(response) -> set[str]:
    return {err["loc"][-1] for err in response.json()["detail"]}


@pytest.mark.parametrize(("payload", "fields"), CASES)
async def test_create_rejects_invalid_payload(client, payload, fields):
    response = await client.post("/telemetry", json=payload)

    assert response.status_code == 422
    assert _rejected_fields(response) == fields


@pytest.mark.parametrize(("payload", "fields"), CASES)
async def test_append_rejects_invalid_payload_and_keeps_flight_unchanged(
    client, flight_id, payload, fields
):
    response = await client.post(f"/telemetry/{flight_id}", json=payload)

    assert response.status_code == 422
    assert _rejected_fields(response) == fields
    assert len((await client.get(f"/flight/{flight_id}")).json()["data"]) == 1


async def test_get_unknown_flight_returns_404(client):
    response = await client.get("/flight/nonexistent-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "Flight ID not found"}


async def test_append_to_unknown_flight_returns_404(client):
    response = await client.post("/telemetry/nonexistent-id", json=generate_valid_payload())

    assert response.status_code == 404
    assert response.json() == {"detail": "Flight ID not found"}


async def test_non_json_body_is_rejected(client):
    response = await client.post(
        "/telemetry", content="lat=1", headers={"Content-Type": "text/plain"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/telemetry"), ("PUT", "/telemetry"), ("POST", "/reset"), ("DELETE", "/flight/x")],
)
async def test_wrong_method_returns_405(client, method, path):
    response = await client.request(method, path)

    assert response.status_code == 405
