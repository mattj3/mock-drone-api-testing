"""Payload builders for the drone telemetry API tests."""

from __future__ import annotations

import random


def generate_valid_payload(rng: random.Random | None = None) -> dict:
    """Return a random telemetry payload that satisfies every field constraint."""
    r = rng or random
    return {
        "lat": round(r.uniform(-90, 90), 6),
        "lon": round(r.uniform(-180, 180), 6),
        "alt": round(r.uniform(0, 500), 2),
        "speed": round(r.uniform(0, 100), 2),
        "heading": round(r.uniform(0, 359.99), 2),
    }


# Each invalid payload is paired with the field(s) the API must reject it for.
INVALID_PAYLOADS: list[tuple[str, dict, set[str]]] = [
    (
        "wrong types and missing fields",
        {"lat": "invalid_latitude", "lon": None, "alt": "high"},
        {"lat", "lon", "alt", "speed", "heading"},
    ),
    (
        "every value out of range",
        {"lat": 200, "lon": -181, "alt": -10, "speed": -5, "heading": 400},
        {"lat", "lon", "alt", "speed", "heading"},
    ),
    (
        "missing alt, speed and heading",
        {"lat": 45.0, "lon": 90.0},
        {"alt", "speed", "heading"},
    ),
    (
        "heading as a compass word",
        {"lat": 45.0, "lon": 90.0, "alt": 100, "speed": 50, "heading": "east"},
        {"heading"},
    ),
    (
        "heading of exactly 360 (use 0 for north)",
        {"lat": 45.0, "lon": 90.0, "alt": 100, "speed": 50, "heading": 360},
        {"heading"},
    ),
]


def generate_invalid_payloads() -> list[dict]:
    """Return just the invalid payload bodies (kept for backwards compatibility)."""
    return [payload for _, payload, _ in INVALID_PAYLOADS]
