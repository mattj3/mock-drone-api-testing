"""Contract tests: the live responses match the published OpenAPI schema."""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from app.app import app
from utils import generate_valid_payload

SPEC = app.openapi()

EXPECTED_OPERATIONS = {
    ("/telemetry", "post"): {"201", "422"},
    ("/flight/{flight_id}", "get"): {"200", "404", "422"},
    ("/telemetry/{flight_id}", "post"): {"201", "404", "422"},
    # 422 appears because every route accepts an optional X-API-Key header.
    ("/reset", "delete"): {"200", "422"},
}


def _validator_for(path: str, method: str, code: str) -> Draft202012Validator:
    schema = SPEC["paths"][path][method]["responses"][code]["content"]["application/json"]["schema"]
    # Resolve "#/components/schemas/..." refs against the whole spec.
    return Draft202012Validator({**schema, "components": SPEC["components"]})


def test_spec_declares_exactly_the_expected_operations():
    actual = {
        (path, method): set(op["responses"])
        for path, ops in SPEC["paths"].items()
        for method, op in ops.items()
    }

    assert actual == EXPECTED_OPERATIONS


def test_telemetry_schema_constraints_are_published():
    props = SPEC["components"]["schemas"]["Telemetry"]["properties"]

    assert (props["lat"]["minimum"], props["lat"]["maximum"]) == (-90, 90)
    assert (props["lon"]["minimum"], props["lon"]["maximum"]) == (-180, 180)
    assert (props["heading"]["minimum"], props["heading"]["exclusiveMaximum"]) == (0, 360)
    assert set(SPEC["components"]["schemas"]["Telemetry"]["required"]) == set(props)


async def test_every_success_response_matches_its_schema(client):
    created = await client.post("/telemetry", json=generate_valid_payload())
    flight_id = created.json()["flight_id"]
    appended = await client.post(f"/telemetry/{flight_id}", json=generate_valid_payload())
    fetched = await client.get(f"/flight/{flight_id}")
    reset = await client.delete("/reset")

    for response, path, method, code in [
        (created, "/telemetry", "post", "201"),
        (appended, "/telemetry/{flight_id}", "post", "201"),
        (fetched, "/flight/{flight_id}", "get", "200"),
        (reset, "/reset", "delete", "200"),
    ]:
        assert str(response.status_code) == code
        _validator_for(path, method, code).validate(response.json())


@pytest.mark.parametrize("body", [{}, {"lat": "x"}])
async def test_validation_errors_match_the_published_error_schema(client, body):
    response = await client.post("/telemetry", json=body)

    assert response.status_code == 422
    _validator_for("/telemetry", "post", "422").validate(response.json())
