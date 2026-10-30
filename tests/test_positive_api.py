"""Happy-path flows: create, read, append, reset."""

from __future__ import annotations

from utils import generate_valid_payload


async def test_post_telemetry_creates_flight(client):
    response = await client.post("/telemetry", json=generate_valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["flight_id"]) == 36  # UUID4 string


async def test_get_flight_returns_stored_payload(client):
    payload = generate_valid_payload()
    flight_id = (await client.post("/telemetry", json=payload)).json()["flight_id"]

    response = await client.get(f"/flight/{flight_id}")

    assert response.status_code == 200
    assert response.json() == {"flight_id": flight_id, "data": [payload]}


async def test_append_preserves_order(client, flight_id):
    first = (await client.get(f"/flight/{flight_id}")).json()["data"][0]
    second, third = generate_valid_payload(), generate_valid_payload()

    for payload in (second, third):
        response = await client.post(f"/telemetry/{flight_id}", json=payload)
        assert response.status_code == 201
        assert response.json() == {"flight_id": flight_id, "status": "appended"}

    data = (await client.get(f"/flight/{flight_id}")).json()["data"]
    assert data == [first, second, third]


async def test_flights_are_independent(client):
    a, b = generate_valid_payload(), generate_valid_payload()
    id_a = (await client.post("/telemetry", json=a)).json()["flight_id"]
    id_b = (await client.post("/telemetry", json=b)).json()["flight_id"]
    await client.post(f"/telemetry/{id_a}", json=generate_valid_payload())

    assert id_a != id_b
    assert len((await client.get(f"/flight/{id_a}")).json()["data"]) == 2
    assert (await client.get(f"/flight/{id_b}")).json()["data"] == [b]


async def test_reset_clears_all_flights(client, flight_id):
    response = await client.delete("/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert (await client.get(f"/flight/{flight_id}")).status_code == 404


async def test_reset_is_idempotent(client):
    for _ in range(2):
        response = await client.delete("/reset")
        assert response.status_code == 200
