# mock-drone-api-testing

What this repo demonstrates: API test automation (pytest, contract, boundary, property and LLM-assisted tests) against a small FastAPI service.

Install: `make install`. Test: `make test`. Lint: `make lint`. Run: `make run`.
CI: `.github/workflows/ci.yml`, runs on push to main and on every PR.

Do not:
- Make the test suite call a model or the network. Generated cases are committed and replayed.
- Commit a freshly generated `tests/generated/cases.json` (its `review` field starts with "Unreviewed"), or claim a human review that did not happen.
- Lower the coverage gate or turn off `filterwarnings = ["error"]` to get green.

Conventions: ruff config in `pyproject.toml` is authoritative; dependencies are pinned in `requirements*.txt` and updated by Dependabot; every PR keeps the badge green and updates `test_plan.md` when behaviour changes.
