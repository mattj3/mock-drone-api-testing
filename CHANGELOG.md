# Changelog

## 1.1.0 – 2026-10-30

### Added
- Optional API-key auth (`REQUIRE_API_KEY`, `API_KEY`) and per-client rate limiting (`RATE_LIMIT_PER_MINUTE`)
- Contract tests against the OpenAPI schema, boundary tests, Hypothesis property tests
- LLM-assisted case generator (`tools/gen_cases.py`) and replayed, reviewed cases
- Dockerfile, Makefile, Dependabot, ruff; CI matrix for Python 3.11–3.13 and a Docker smoke job

### Changed
- Typed response models replace `response_model=dict`
- `heading` is now `0 <= h < 360`
- Endpoints are `async def`
- Dependencies pinned; config moved from `pytest.ini` to `pyproject.toml`
- Tests share fixtures and reset state before each test

### Fixed
- Non-finite values (`"Infinity"`, `"NaN"`) are rejected
- README badge pointed at a non-existent repository

## 1.0.0 – 2025-06
- Initial FastAPI service, async pytest suite and CI
