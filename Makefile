default: format test lint

# Development

.PHONY: format
format:
	uvx nox -e format

.PHONY: fmt
fmt: format

.PHONY: f
f: format

.PHONY: test
test:
	uvx nox -e test

.PHONY: t
t: test

.PHONY: lint
lint:
	uvx nox -e lint

.PHONY: l
l: lint

# Docker development

.PHONY: build
build:
	./deploy/docker_build.sh

.PHONY: publish
publish:
	./deploy/docker_build.sh --push

.PHONY: run
run: build
	./deploy/run_locally.sh

.PHONY: up
up: run
