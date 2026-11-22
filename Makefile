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

.PHONY: openapi
openapi:
	uv run python -m pyball.infrastructure.plugins.openapi

# Bundled plugins and the crates they share: each folder's Makefile has check and build

.PHONY: plugins-check
plugins-check:
	for dir in crates/*/ plugins/*/; do $(MAKE) -C "$$dir" check || exit 1; done

.PHONY: plugins-build
plugins-build:
	for dir in crates/*/ plugins/*/; do $(MAKE) -C "$$dir" build || exit 1; done

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
