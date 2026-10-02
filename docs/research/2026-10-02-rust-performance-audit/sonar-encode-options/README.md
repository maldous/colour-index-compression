# Encode-options Sonar refactor

`EncodeOptions` groups existing native CIXG encode controls at the `encode`, `encode_with_strategy`, and `encode_candidates` boundary. The only out-of-file changes are the three authorized forwarding constructors in `portfolio_auto.rs` and `streaming_backend.rs`; every field preserves its former positional value. No wire, route, or policy behavior changed.

## Checkpoint

- Base: `52cd25716f577dc46c0f7cd6dfa9854dd2d80361`
- Toolchain: stable Rust at `/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/`
- `cargo check --bin cix`: passed.
- `cargo test cixg_huffman_tests --bin cix -- --test-threads=1`: 2 passed.

Archive and pipe qualification remains to be run before review.
