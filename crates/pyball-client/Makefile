.PHONY: check
check:
	cargo fmt --check
	cargo clippy --all-targets --locked -- -D warnings
	cargo test --locked

# A library: the plugins that use it build it.
.PHONY: build
build:
