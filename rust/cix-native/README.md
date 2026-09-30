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

| Operation | CIXG1 raw/run/composition/LZ/predictor/PPM/BWT/stride/phrases/DEFLATE | CIXG1 other routes | CIXF1/CIXM6 legacy stream |
|---|---|---|---|
| Rust encode | Yes; auto-selection over raw/run/composition/DEFLATE or fixed `--route`; routes 2–8 except 9, and 10 match Python on tested fixtures | Explicitly unavailable; never substituted | Unavailable |
| Rust decode | Yes; route IDs 0–8 except 9, and 10 with raw/run/exact-rank/range/DEFLATE substream coders | Explicit unsupported-route error | Unavailable |
| Python decode of Rust output | Yes; cross-decoded, fixed routes byte-identical | N/A | N/A |
| Exact original-byte restoration | Verified across empty, tiny, random, repetitive and mixed fixtures | Not claimed | Not claimed |

The existing Python implementation remains the complete executable reference. Exact arbitrary-precision combinatorial ranks are implemented for CIX composition tiles up to 1024 symbols; no rank is narrowed to a machine integer. The LZ match parser, predictor residual, PPM order-3 model, BWT/MTF, six-choice stride selector, and phrase dictionary routes are also ported. Type-class range coding and count-range decoding use the reference 32-bit arithmetic coder; adaptive substreams, mixture and the CIXB1 backend portfolio remain unported. Timing-dependent Python selector behavior is not reproduced; Rust's current `auto` option compares only raw, run-length, composition, and DEFLATE candidates. LZ, predictor, PPM, BWT, stride and phrases are available as explicit `--route` values; the native `auto` option is not the frozen Python effort selector. LZ uses a bounded 8-candidate chain over a 65,536-byte window and requires a 16 MiB working-memory allowance. PPM requires a 64 MiB working-memory allowance. `--memory` bounds estimated codec working allocations, not executable/shared-library RSS; peak RSS is measured separately. `--threads` does not enable parallelism. The CLI handles one input path per invocation. SIGINT returns nonzero and removes incomplete file output; this is verified on the current Unix host.

## Verification

Run `python3 scripts/verify_rust_native.py` and `python3 scripts/verify_rust_streaming.py` from the repository root. The first creates temporary correctness fixtures, cross-decodes fixed routes, verifies canonical bytes and checks malformed input. The second uses actual pipes, an idle producer, a delayed consumer, irregular writes, an empty stream and a stream larger than its codec-memory budget. Test fixtures are correctness checks only, not compression-performance evidence. Silesia-only performance evidence is recorded in `docs/research/2026-10-01-rust-native/silesia-results.json`.
