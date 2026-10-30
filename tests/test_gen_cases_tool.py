"""Unit tests for the case generator, using a fake client (no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools import gen_cases

GOOD = [{"name": "a", "payload": {}, "expected_status": 422, "rationale": "empty"}]


class FakeClient:
    def __init__(self, text: str):
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)
        self._text = text

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._text)])


def test_parse_accepts_fenced_json_and_fills_rationale():
    reply = '```json\n[{"name": "x", "payload": 1, "expected_status": 201}]\n```'

    assert gen_cases.parse_cases(reply) == [
        {"name": "x", "payload": 1, "expected_status": 201, "rationale": ""}
    ]


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        ("no array here", "no JSON array"),
        ("[{bad json}]", "invalid JSON"),
        ('[{"name": "x"}]', "missing required keys"),
        ('[{"name": "x", "payload": 1, "expected_status": 500}]', "has status 500"),
        (json.dumps(GOOD * 2), "duplicate case name"),
    ],
)
def test_parse_rejects_bad_replies(reply, message):
    with pytest.raises(gen_cases.CaseFormatError, match=message):
        gen_cases.parse_cases(reply)


def test_generate_sends_schema_and_count_to_the_model():
    client = FakeClient(json.dumps(GOOD))

    cases = gen_cases.generate(client, "test-model", {"title": "Telemetry"}, count=7)

    assert cases == GOOD
    (call,) = client.calls
    assert call["model"] == "test-model"
    prompt = call["messages"][0]["content"]
    assert '"title": "Telemetry"' in prompt
    assert "Propose 7 distinct" in prompt


def test_main_without_api_key_exits_cleanly(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert gen_cases.main(["--out", str(tmp_path / "c.json")]) == 2
    assert "not set" in capsys.readouterr().err
    assert not (tmp_path / "c.json").exists()


def test_main_writes_unreviewed_document(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    fake_sdk = SimpleNamespace(Anthropic=lambda: FakeClient(json.dumps(GOOD)))
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_sdk)
    out = tmp_path / "cases.json"

    assert gen_cases.main(["--out", str(out), "--model", "m"]) == 0

    document = json.loads(out.read_text())
    assert document["cases"] == GOOD
    assert document["source"].endswith("with m")
    assert document["review"].startswith("Unreviewed")
