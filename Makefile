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
	nox -e format

.PHONY: f
f: format

.PHONY: test
test:
	nox -e test

.PHONY: t
t: test

.PHONY: lint
lint:
	nox -e lint

.PHONY: l
l: lint


.PHONY: build
build:
	nox -e dbuild


.PHONY: publish
publish: build
	nox -e dpublish
