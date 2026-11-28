# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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

# Bundled plugins and the clients they share: each folder's Makefile has check and build

.PHONY: plugins-check
plugins-check:
	for dir in clients/*/ plugins/*/; do $(MAKE) -C "$$dir" check || exit 1; done

.PHONY: plugins-build
plugins-build:
	for dir in clients/*/ plugins/*/; do $(MAKE) -C "$$dir" build || exit 1; done

# The contract suite, against the Python core unless PYBALL_CORE_CMD names another

.PHONY: contract
contract:
	uv sync --frozen
	$(MAKE) -C contract check

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
