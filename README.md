# mock-drone-api-testing

[![Drone API Tests](https://github.com/mattj3/mock-drone-api-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/mattj3/mock-drone-api-testing/actions/workflows/ci.yml)
[![Test Plan](https://img.shields.io/badge/docs-test--plan-blue)](./test_plan.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

A small FastAPI service that simulates drone telemetry, and the API test suite that exercises it. It is built as a test-automation portfolio piece: the service is deliberately simple so the testing techniques stay in focus.

**What this demonstrates**

- **107 pytest tests** at 100% branch coverage, with a 90% gate in CI and warnings treated as errors
- **Boundary-value analysis** on every field, which caught a real bug: `"alt": "Infinity"` was accepted
- **Contract tests** that validate live 2xx and 422 responses against the service's own OpenAPI schema
- **Property-based tests** (Hypothesis) over every field's numeric range, plus the payload builders
- **Auth and rate-limit scenarios** (401, 429 with `Retry-After`, sliding window) behind env toggles
- **LLM-assisted test design**: a script asks Claude for edge cases; the output is committed with its review status and replayed offline, so CI never depends on a model
- **CI** on Python 3.11–3.13, lint, and a Docker build-and-smoke job; Dependabot keeps pins current

## Quick start

```bash
make install   # .venv + pinned dev dependencies
make test      # full suite with coverage
make run       # http://127.0.0.1:8000/docs
```

No `make`? `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest`.

Docker: `make docker`, then open http://localhost:8000/docs.

## API

| Method | Endpoint                 | Success | Errors        | Description                                  |
| ------ | ------------------------ | ------- | ------------- | -------------------------------------------- |
| POST   | `/telemetry`             | 201     | 422           | Create a flight; returns `flight_id`          |
| GET    | `/flight/{flight_id}`    | 200     | 404           | All telemetry for a flight, in order          |
| POST   | `/telemetry/{flight_id}` | 201     | 404, 422      | Append telemetry to a flight                  |
| DELETE | `/reset`                 | 200     |               | Clear all flights (test helper)               |

Telemetry body: `lat` −90…90, `lon` −180…180, `alt` ≥ 0, `speed` ≥ 0, `heading` 0 ≤ h < 360 (use 0 for north). All finite floats; numeric strings such as `"12.5"` are coerced (Pydantic lax mode).

### Optional auth and rate limiting

Both are off by default.

| Variable                 | Effect                                                                 |
| ------------------------ | ---------------------------------------------------------------------- |
| `REQUIRE_API_KEY=1`      | Every request needs header `X-API-Key` equal to `API_KEY`, else 401    |
| `API_KEY=<value>`        | The accepted key (503 if auth is required but this is unset)           |
| `RATE_LIMIT_PER_MINUTE=N`| N requests per 60 s per key (or client IP), else 429 with `Retry-After` |

## Tests

| File                              | What it covers                                              |
| --------------------------------- | ----------------------------------------------------------- |
| `tests/test_positive_api.py`      | Create → append → fetch → reset flows, flight isolation     |
| `tests/test_negative_api.py`      | Invalid bodies (and which field is blamed), 404s, 405s      |
| `tests/test_boundaries.py`        | On/just-past every bound, NaN/Infinity, lax coercion        |
| `tests/test_contract.py`          | Responses validated against the OpenAPI schema              |
| `tests/test_auth_and_rate_limit.py` | 401/503/429, header countdown, sliding window             |
| `tests/test_unit_utils.py`        | Hypothesis: in-range floats accepted, out-of-range rejected  |
| `tests/test_generated_cases.py`   | Replays the committed LLM-proposed cases                    |
| `tests/test_gen_cases_tool.py`    | The generator itself, with a fake client                    |

`tests/conftest.py` resets in-memory state and feature env vars before every test, so tests can run in any order.

### LLM-assisted cases

`tools/gen_cases.py` sends the `Telemetry` JSON schema to Claude and asks for edge cases with a predicted status and a one-line rationale. It validates the reply's shape and writes `tests/generated/cases.json` marked *Unreviewed*; the suite refuses an unreviewed file. A person checks each `expected_status`, records who reviewed it in the `review` field, and commits. The suite replays the file and never calls a model.

```bash
ANTHROPIC_API_KEY=... make cases
```

The committed seed set was written by Claude in the session that added the tool, not by running the script. Its `source` and `review` fields say so, and owner review is still pending.

## Project layout

```text
app/app.py              FastAPI app, models, auth and rate-limit dependencies
utils.py                Valid/invalid payload builders
tools/gen_cases.py      LLM test-case generator
tests/                  Test suite (see table above)
tests/generated/        Committed, reviewed generated cases
test_plan.md            Strategy, scope and case summary
Dockerfile, Makefile    Container and task shortcuts
```

## License

MIT
