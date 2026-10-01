# Native implementation smoke checks (not performance measurements)

## CIXG2 / coder 6

- `cargo check --manifest-path rust/cix-native/Cargo.toml --bin cix` passed.
- `cargo build --manifest-path rust/cix-native/Cargo.toml --bin cix --bin uncix` passed on the current host.
- Small synthetic CLI cases confirmed `--fast --format auto` emits CIXG1, `--best --format cixg1` emits CIXG1, and `--fast --format cixg2` emits CIXG2. Each restored byte-exactly with Rust `uncix`.
- `--format cixg1 --route predictor --backend context-range-o1-b4` rejects the incompatible coder with a clear stderr error.
- A small complete CIXG2 archive with predictor residual plus substream coder 6, order 1/bucket width 4, independently restored byte-exactly with Rust and with the isolated Python decoder extension. This validates the wire decoder path; the archive was materialized from a fixed synthetic input, not selected or scored by Python.
- A Rust predictor-route candidate trial on a 32 KiB synthetic Markov fixture considered the configured context backend, but DEFLATE coder 3 won its internal payload comparison. This is only a correctness/selection smoke; it is not a compression result or benchmark.

## Extended PPM

- Direct Python checks round-tripped PPM payloads at orders 4, 6, and 8.
- A small Rust CIXG2 PPM archive decoded in Rust and the Python decoder extension. The selector chose order 3 on that fixture; this does not verify a Rust-emitted order-4..8 payload.
- Full crate `cargo test` was attempted again with `CARGO_BUILD_JOBS=2`; all unit tests before `chain::tests::encoder_fixtures_cross_decode_in_rust` passed, but that fixture consumed one CPU continuously for over five minutes without finishing. The run was interrupted to avoid leaving an unbounded job. The focused modified-code suites and example compile passed separately. Treat the full suite as incomplete; qualify or bound the chain fixture before claiming a full-suite pass.

## Python test runner constraint

`pytest` is absent from the current environment, and `uv --offline` could not resolve the repository's optional benchmark extras. New Python checks were run as direct assertions with the interpreter; no package was installed. This is a test-runner limitation, not a test pass for the full Python suite.
The explicit `context-range-*` backend now constrains the substream coder
dimension and compares only that coder with raw fallback. Automatic effort
selection remains free to compare routes under the selected backend. A
post-change `--best` CLI exercise over a synthetic 128 KiB repeating fixture
was interrupted during route search; its partial output was discarded and is
not correctness, size, or performance evidence.

## Bounded payload oracle

- `cargo test --manifest-path rust/cix-native/Cargo.toml --test oracle`: 7 passed.
- Deterministic synthetic fixtures cover tiny, random, high-entropy repeated-substring, repetitive, mixed-region, empty and malformed/bounds cases. Every materialized non-raw candidate is decoded and byte-compared before entering the exact payload minimum.
- The oracle distinguishes shortlist miss, nonwinning selection, equal-size tie and decode failure. It covers only its documented finite public-library candidate configuration; it does not inspect CLI-private candidates or compare complete archive framing, formats, transforms, segmentation, shared history or external codecs.

## Recurrence-distance feature prototype

- `cargo test --manifest-path rust/cix-native/Cargo.toml --test zpaq_context`: 6 passed.
- `cargo test --manifest-path rust/cix-native/Cargo.toml --test fixedmix_recurrence`: 3 passed; frozen v1 bytes are unchanged, v2 restores with prefix history, and malformed/truncated/corrupt payloads reject.
- `zpaq_context` keeps last-seen position state for 256 byte values, yields a causal logarithmic distance bucket, validates a versioned fixed-size config and passes a one-million-symbol bounded-state test.
- Fixed-mix payload v2 incorporates that recurrence feature and reconstructs it during decode. It is not a production selector candidate or a ZPAQ port. No compressed-size or speed result exists.

## Huffman and archive oracles

- `cargo test --manifest-path rust/cix-native/Cargo.toml --test huffman`: 4 passed. The deterministic canonical Huffman coder is CIXG2 coder 7; CIXG1 rejects it.
- Rust-generated CIXG2 coder-7 archive decoded byte-exactly in Rust and the isolated Python decoder; relabeling it CIXG1 was rejected by both.
- `cargo test --manifest-path rust/cix-native/Cargo.toml --test cli_archive_oracle`: passed. On two ≤192-byte synthetic inputs, 35 CIXG1 route/backend constraints per fixture (144 bounded child invocations total) included full archive bytes and a fresh `uncix` decode. BEST matched the enumerated minimum on both.
- These finite oracles do not establish completeness across transforms, full parameter products, segmentation/history, other format packages or external codecs.

## CIXM6 mode families

The canonical Rust tree already offers CIXM6 modes 3 (legacy LZ), 4 (BWT),
and 5 (transform) behind effort and memory gates, includes complete per-frame
costs and stable first-winner tie behavior, and has matching decoder dispatch.
Focused frozen fixture suites were reported passing for LZ, BWT, and the
transform family, including malformed BWT/transform inputs. A dedicated test
that forces each mode to win through the full selector and cross-package
comparison remains pending; this does not establish CIXM6/CIXG1/CIXF1 global
package search.

The six fixture commands were rerun in this checkout with `CARGO_BUILD_JOBS=2`:

```text
python3 scripts/verify_rust_cixm6_lz_encode.py
python3 scripts/verify_rust_cixm6_lz.py
python3 scripts/verify_rust_bwt_encode.py
python3 scripts/verify_rust_bwt_legacy.py
python3 scripts/verify_rust_transform_encode.py
python3 scripts/verify_rust_transform.py
```

All exited successfully against frozen Python reference commit
`80b95427725ecf59d626b2982d50f6349abd56e1`: LZ canonical encode fixtures and
four cross-decode payloads passed; LZ decoder forced nested stream modes and
retained version-1 fixtures passed; 25 BWT encodes across versions 1–6 matched
Python and 39 frozen Python BWT fixtures decoded in Rust; 128 explicit and 12
beam transform encodes matched Python, and 32 Python transform frames decoded
in Rust. Malformed BWT and transform versions, IDs and truncations were
rejected. Python was used only as the frozen wire-compatibility reference and
independent decoder; it did not select or tune compression candidates. These
fixtures leave transient harnesses and do not produce durable per-fixture
logs. This is correctness evidence, not a size or speed measurement.

Record/periodic CIXM6 encoder parity was also rerun with:

```text
CARGO_BUILD_JOBS=2 python3 scripts/verify_rust_record_periodic_encode.py
```

It verified 10 canonical payloads byte-for-byte against the frozen Python
implementation, Python and Rust decoding of all 10, periodic inner modes 0–4,
local byte modes 4–5, and invalid option/truncation/corruption rejection.
Again, the Python implementation was only the frozen compatibility oracle; no
candidate selection or tuning used it. This script also leaves no durable
per-fixture output log.
