"""Replay the committed LLM-proposed cases. No model is called.

The file's `review` field records who checked the expected statuses; freshly
generated ("Unreviewed") files are refused so they cannot slip into the suite.
"""

from __future__ import annotations

import json

import pytest

from tools.gen_cases import OUT_PATH, parse_cases

DOCUMENT = json.loads(OUT_PATH.read_text())
CASES = parse_cases(json.dumps(DOCUMENT["cases"]))


def test_cases_file_records_provenance_and_review():
    assert DOCUMENT["source"]
    assert not DOCUMENT["review"].startswith("Unreviewed"), "review the cases before committing"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_generated_case(client, case):
    response = await client.post("/telemetry", json=case["payload"])

    assert response.status_code == case["expected_status"], case["rationale"]
