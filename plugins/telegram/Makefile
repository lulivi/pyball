.PHONY: check
check:
	uv run --locked black --check src tests
	uv run --locked isort --check-only src tests
	uv run --locked mypy src tests
	uv run --locked pylint src tests
	uv run --locked pytest -q

.PHONY: build
build:
	uv build --wheel
