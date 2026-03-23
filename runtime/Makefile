build:
	cargo build --workspace

test:
	cargo test --workspace

check:
	cargo check --workspace

clippy:
	cargo clippy --workspace -- -D warnings

fmt:
	cargo fmt --all

fmt-check:
	cargo fmt --all -- --check

run-gateway:
	cargo run --bin omega-gateway

run-cli:
	cargo run --bin omega-cli -- $(ARGS)
