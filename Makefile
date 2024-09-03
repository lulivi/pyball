default: build

# Production

.PHONY: up
up: build
	docker compose up

# Development

.PHONY: format
format:
	poetry run nox -e format

.PHONY: f
f: format

.PHONY: build
build:
	poetry run nox -e dbuild
