.PHONY: check
check:
	uv run --locked black --check src tests
	uv run --locked isort --check-only src tests
	uv run --locked mypy src tests
	uv run --locked pylint src tests
	uv run --locked pytest -q

# A library: the plugins that use it install it.
.PHONY: build
build:
