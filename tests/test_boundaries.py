"""Boundary-value analysis on every telemetry field."""

from __future__ import annotations

import pytest

BASE = {"lat": 0.0, "lon": 0.0, "alt": 0.0, "speed": 0.0, "heading": 0.0}

ACCEPTED = [
    ("lat", -90), ("lat", 90),
    ("lon", -180), ("lon", 180),
    ("alt", 0), ("alt", 1e6),
    ("speed", 0), ("speed", 1e4),
    ("heading", 0), ("heading", 359.999),
]  # fmt: skip

REJECTED = [
    ("lat", -90.000001), ("lat", 90.000001),
    ("lon", -180.000001), ("lon", 180.000001),
    ("alt", -0.001),
    ("speed", -0.001),
    ("heading", -0.001), ("heading", 360),
]  # fmt: skip


@pytest.mark.parametrize(("field", "value"), ACCEPTED, ids=lambda v: str(v))
async def test_value_on_boundary_is_accepted(client, field, value):
    response = await client.post("/telemetry", json={**BASE, field: value})

    assert response.status_code == 201, response.text


@pytest.mark.parametrize(("field", "value"), REJECTED, ids=lambda v: str(v))
async def test_value_past_boundary_is_rejected(client, field, value):
    response = await client.post("/telemetry", json={**BASE, field: value})

    assert response.status_code == 422
    assert [err["loc"][-1] for err in response.json()["detail"]] == [field]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
async def test_non_finite_numbers_are_rejected(client, value):
    # JSON has no NaN/Infinity literals. Before allow_inf_nan=False, "Infinity" was
    # coerced to float("inf") and accepted as an altitude.
    response = await client.post("/telemetry", json={**BASE, "alt": value})

    assert response.status_code == 422


async def test_numeric_strings_are_coerced(client):
    """Pydantic's lax mode accepts "12.5" for a float. Documented, not a bug."""
    response = await client.post("/telemetry", json={**BASE, "alt": "12.5"})

    assert response.status_code == 201
