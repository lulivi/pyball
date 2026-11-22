.PHONY: check
check:
	cargo fmt --check
	cargo clippy --all-targets --locked -- -D warnings
	cargo test --locked

.PHONY: build
build:
	cargo build --release --locked
