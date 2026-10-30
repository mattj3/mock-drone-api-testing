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


BOUNDS = {  # field: (min, max, max_is_exclusive); None = unbounded
    "lat": (-90.0, 90.0, False),
    "lon": (-180.0, 180.0, False),
    "alt": (0.0, None, False),
    "speed": (0.0, None, False),
    "heading": (0.0, 360.0, True),
}
VALID_BASE = {"lat": 0.0, "lon": 0.0, "alt": 0.0, "speed": 0.0, "heading": 0.0}


@pytest.mark.parametrize("field", list(BOUNDS))
@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_any_in_range_float_is_accepted(field, data):
    low, high, exclusive = BOUNDS[field]
    value = data.draw(
        st.floats(
            min_value=low,
            max_value=high,
            exclude_max=exclusive,
            allow_nan=False,
            allow_infinity=False,
        )
    )

    assert getattr(Telemetry.model_validate({**VALID_BASE, field: value}), field) == value


@pytest.mark.parametrize("field", list(BOUNDS))
@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_any_out_of_range_or_non_finite_float_is_rejected(field, data):
    low, high, exclusive = BOUNDS[field]
    below = st.floats(max_value=low, exclude_max=True)
    above = (
        st.floats(min_value=high, exclude_min=not exclusive) if high is not None else st.nothing()
    )
    value = data.draw(st.one_of(below, above, st.just(float("nan")), st.just(float("inf"))))

    with pytest.raises(ValidationError) as exc:
        Telemetry.model_validate({**VALID_BASE, field: value})
    assert [err["loc"][-1] for err in exc.value.errors()] == [field]


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
