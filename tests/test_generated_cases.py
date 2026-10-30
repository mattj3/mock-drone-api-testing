"""Replay the committed, human-reviewed LLM-generated cases. No model is called."""

from __future__ import annotations

import json

import pytest

from tools.gen_cases import OUT_PATH, parse_cases

DOCUMENT = json.loads(OUT_PATH.read_text())
CASES = parse_cases(json.dumps(DOCUMENT["cases"]))


def test_cases_file_records_provenance_and_review():
    assert DOCUMENT["source"]
    assert DOCUMENT["review"].startswith("Reviewed"), "review the cases before committing them"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_generated_case(client, case):
    response = await client.post("/telemetry", json=case["payload"])

    assert response.status_code == case["expected_status"], case["rationale"]
