default: build

# Production

.PHONY: up
up:
	docker compose up --build

.PHONY: setup
setup:
	[ -f ".env" ] || cp sample.env .env

# Development

.PHONY: format
format:
	poetry run nox -e format

.PHONY: f
f: format

.PHONY: build
build:
	docker compose build
