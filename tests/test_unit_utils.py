"""Property tests: the payload builders agree with the API's own model."""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.app import Telemetry
from utils import INVALID_PAYLOADS, generate_invalid_payloads, generate_valid_payload


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_every_generated_valid_payload_passes_the_model(seed):
    payload = generate_valid_payload(random.Random(seed))

    assert Telemetry.model_validate(payload).model_dump() == payload


def test_seeded_generation_is_reproducible():
    assert generate_valid_payload(random.Random(7)) == generate_valid_payload(random.Random(7))


@pytest.mark.parametrize(
    ("payload", "fields"),
    [pytest.param(p, f, id=n) for n, p, f in INVALID_PAYLOADS],
)
def test_every_invalid_payload_fails_on_the_expected_fields(payload, fields):
    with pytest.raises(ValidationError) as exc:
        Telemetry.model_validate(payload)

    assert {err["loc"][-1] for err in exc.value.errors()} == fields


def test_generate_invalid_payloads_returns_bodies_only():
    assert generate_invalid_payloads() == [p for _, p, _ in INVALID_PAYLOADS]
