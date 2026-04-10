default: build

# Production

.PHONY: up
up: build
	docker compose up

.PHONY: run
run: build
	docker compose run --remove-orphans bot

# Development

.PHONY: format
format:
	poetry run nox -e format

.PHONY: f
f: format

.PHONY: test
test:
	poetry run nox -e test

.PHONY: t
t: test

.PHONY: lint
lint:
	poetry run nox -e lint

.PHONY: l
l: lint


.PHONY: build
build:
	poetry run nox -e dbuild


.PHONY: publish
publish: build
	poetry run nox -e dpublish
