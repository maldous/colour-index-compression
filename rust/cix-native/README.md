# CIX (pronounced “six”) native command-line tools

This private research build uses the existing CIXG1 stream format. `.cix` means a CIX stream archive; it is not ZIP or gzip. It is native Rust and does not launch Python. The DEFLATE route links system zlib.

## Build and install (Linux x86_64 verified)

Install Rust stable, a C compiler and zlib development headers, then from the repository root run:

```sh
cargo build --release --manifest-path rust/cix-native/Cargo.toml
install -Dm755 rust/cix-native/target/release/cix ~/.local/bin/cix
install -Dm755 rust/cix-native/target/release/uncix ~/.local/bin/uncix
install -Dm755 rust/cix-native/target/release/cixcat ~/.local/bin/cixcat
```

The checked-in `Cargo.lock` pins Rust dependencies. For a thin-LTO build use `cargo build --profile release-lto --manifest-path rust/cix-native/Cargo.toml`. No other operating system or architecture has been built or verified.

## Examples

```sh
cix -6 report.dat                 # writes report.dat.cix; keeps report.dat
uncix report.dat.cix               # writes report.dat; refuses overwrite
cix --external zstd --profile current report.dat > report.cix  # one bounded CIXB1 backend
cix --portfolio current report.dat  # compare CIXG1 and eligible CIXB1 candidates
cix --format cixm6 -c report.dat > report.cix  # legacy stream, raw/multinomial routes
cix --format cixf1 report.dat  # legacy stream plus basename metadata
uncix -t report.cix                  # verify integrity without restoring bytes
cix -9 --route deflate -c input | ssh host 'cat > input.cix'
cixcat input.cix | tar -x  # use tar pipelines for directory workflows
uncix -t input.cix                  # verify checksums without restoring bytes
uncix -l input.cix                  # show block route and sizes on stderr
cat input | cix -c - > input.cix
cat input.cix | cixcat - > restored
cix --stream --block-size 1MiB --memory 64MiB --flush-interval 250ms -c < input.bin > output.cix
uncix --stream -c < output.cix > restored.bin
```

`-f` permits replacing an output. File output uses a same-directory temporary file and atomic rename; stdout output is never spooled. `-k` is accepted for conventional CLI compatibility; inputs are retained by default. `-1` through `-9` select DEFLATE effort; `-9` requests 65,536-byte frames and levels 1–8 request 32,768-byte frames. `--stream` makes streaming intent explicit; streaming is already the default for regular and non-seekable inputs. It reads each input once, retains one bounded block, emits and flushes complete frames, and decodes frames incrementally. Pipes provide natural backpressure; there are no queued workers.

`--block-size` accepts bytes, KiB, MiB or GiB. CIXG1 limits frames to 65,536 bytes, so larger requests (including `1MiB`) are clamped to that format limit with a stderr diagnostic. `--memory` accepts the same units and bounds the native codec's estimated live block/candidate working set (eight times effective block size plus 64 KiB). Runtime and shared-library RSS is measured separately. `--threads N` accepts only `1`; larger worker counts are rejected. `--history SIZE` accepts zero; nonzero history is rejected because supported routes are stateless. Every emitted frame is independently decodable; `--independent-blocks` states this explicitly. Combining it with nonzero `--history` is rejected.

`--flush-interval 100ms` emits a partially filled frame after the interval expires, including while a pipe producer remains open but idle. It uses Unix `poll`; it is best-effort and actual output time also includes encoding and downstream backpressure. Flushing occurs only at valid CIXG1 frame boundaries. The decoder may emit verified block bytes before it sees the footer. Whole-stream integrity is confirmed only after it reads and validates the terminal SHA-256 frame; a missing or corrupt footer returns nonzero even if earlier blocks were already written.

## Compatibility at this checkpoint

| Operation | CIXG1 | CIXB1 direct archives | CIXB1 portfolio selection | CIXF1/CIXM6 |
|---|---|---|---|---|
| Rust encode | Yes; routes 0–10 and bounded route selection | Yes; eligible gzip, bzip2, xz, zstd and Brotli presets with `--external`; input capped at 16 MiB | Yes; `--portfolio fast|current|size` compares a fixed, finite candidate plan (up to 16 candidates), input capped at 16 MiB | CIXM6 bounded selector considers legacy modes 0–20 subject to block eligibility, effort and memory; CIXF1 adds a validated UTF-8 basename wrapper |
| Rust decode | Yes; routes 0–10 with raw/run/exact-rank/range/DEFLATE substream coders | Yes; bounded backend decoders validate archive length and SHA-256 | N/A | CIXM5/CIXM6 modes 0–20; validates CRC/footer and optional CIXF1 metadata, errors explicitly on unknown modes |
| Python decode of Rust output | Yes; canonical fixed-route fixtures are byte-identical | Yes; Python cross-decodes tested backend/profile fixtures | N/A | Frozen Python decodes every implemented mode's canonical Rust payloads; CIXF1 wrapper round trips on tested fixtures |
| Exact original-byte restoration | Verified across empty, tiny, random, repetitive and mixed fixtures | Verified for every currently eligible backend/profile pair | N/A | Verified on frozen Python-produced CIXM5/CIXM6 fixtures for every mode 0–20, including nested PPM v2–v5 and malformed/truncated frames |

The existing Python implementation remains the complete executable reference. Exact arbitrary-precision combinatorial ranks are implemented without narrowing exact ranks to machine integers. Fixed CIXM6 payload routes target Python's canonical bytes; Rust's bounded per-block selector charges complete frame size and uses `-1` through `-9` as an effort budget. This selector is deterministic but is not an exact reproduction of Python's timing-dependent route selection, and the LZ route uses a bounded hash-chain parser rather than Python's optional suffix-array parser on large blocks. Candidates exceeding the configured memory allowance are explicitly omitted with a stderr diagnostic. CIXM5/CIXM6 decoding covers the frozen modes 0–20 and rejects unknown modes. The CIXB1 portfolio and external-backend behavior is unchanged: it uses finite candidates, is limited to 16 MiB, rejects streaming, and charges complete archive bytes. `--memory` bounds estimated codec working allocations, not executable/shared-library RSS; peak RSS is measured separately. `--threads` does not enable parallelism. The CLI handles one input path per invocation. SIGINT returns nonzero and removes incomplete file output; this is verified on the current Unix host.

## Verification

Run `python3 scripts/verify_rust_native.py`, `python3 scripts/verify_rust_streaming.py`, `python3 scripts/verify_rust_cixb1.py`, `python3 scripts/verify_rust_portfolio.py`, `python3 scripts/verify_rust_cixm6.py` and `python3 scripts/verify_rust_cixm6_selector.py` from the repository root. The native fixture verifier cross-decodes fixed routes and checks malformed input. The streaming verifier uses actual pipes, an idle producer, a delayed consumer, irregular writes, an empty stream and a stream larger than its codec-memory budget. The selector verifier checks all nine effort levels on six input classes with Python and Rust decoding. These tests are correctness checks, not compression-performance evidence. Silesia-only performance evidence is recorded in `docs/research/2026-10-01-rust-native/silesia-results.json`.


The [Squash plugin](../../squash/README.md) registers the codec through Squash 0.8 splice callbacks and streams directly through the Rust C ABI.
