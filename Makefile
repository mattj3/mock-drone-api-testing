.PHONY: install test lint format run docker cases

install:  ## Create .venv and install pinned dev dependencies
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

test:     ## Run the suite with the coverage gate
	.venv/bin/pytest

lint:     ## Lint and check formatting
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

format:
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .

run:      ## Serve the API on http://127.0.0.1:8000 (docs at /docs)
	.venv/bin/uvicorn app.app:app --reload

docker:   ## Build and run the container
	docker build -t mock-drone-api . && docker run --rm -p 8000:8000 mock-drone-api

cases:    ## Regenerate LLM-proposed cases (needs ANTHROPIC_API_KEY); review before committing
	.venv/bin/pip install anthropic && .venv/bin/python -m tools.gen_cases
