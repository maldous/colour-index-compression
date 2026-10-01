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
| Rust encode | Yes; routes 0–10 and bounded route selection | Yes; eligible gzip, bzip2, xz, zstd and Brotli presets with `--external`; input capped at 16 MiB | Yes; `--portfolio fast|current|size` compares a fixed, finite candidate plan (up to 16 candidates), input capped at 16 MiB | Unavailable |
| Rust decode | Yes; routes 0–10 with raw/run/exact-rank/range/DEFLATE substream coders | Yes; bounded backend decoders validate archive length and SHA-256 | N/A | Unavailable |
| Python decode of Rust output | Yes; canonical fixed-route fixtures are byte-identical | Yes; Python cross-decodes tested backend/profile fixtures | N/A | N/A |
| Exact original-byte restoration | Verified across empty, tiny, random, repetitive and mixed fixtures | Verified for every currently eligible backend/profile pair | N/A | N/A |

The existing Python implementation remains the complete executable reference. Exact arbitrary-precision combinatorial ranks are implemented for CIX composition tiles up to 1024 symbols; no rank is narrowed to a machine integer. The LZ match parser, predictor residual, PPM order-3 model, BWT/MTF, six-choice stride selector, and phrase dictionary routes are also ported. Type-class range coding, adaptive-range coder 4, and count-range coder 5 use the reference 32-bit arithmetic coder. Route 9 mixture uses the frozen integer mixer. CIXB1 direct backend routes preserve eligible preset values. Native `--portfolio` compares those direct candidates with CIXG1 candidates using complete archive byte lengths; the number of candidates is fixed by the profile (fast: 4, current: 5, size: 16). This is a bounded native selector with a 16 MiB input limit, not an exact reproduction of the frozen Python timing-dependent selector. `--external BACKEND --profile PROFILE` writes one CIXB1 archive; it requires a named input file, has a 16 MiB source cap and rejects streaming flags. Fast permits gzip, zstd and dictionary-free Brotli quality 0; current/size permit gzip, bzip2, xz and zstd. Unsupported combinations are explicitly rejected. Portfolio selection is offline, does not accept `--stream` or `--flush-interval`, requires at least 128 MiB working memory for fast/current or 384 MiB for size, and examines the input once into a bounded buffer. Fast/current compare CIXG1 adaptive output with eligible direct backends. Size also tries each fixed CIXG1 route ID 0–10 on 64 KiB frames. It picks the smallest complete candidate archive, including every header and checksum. CIXM6's 21-mode selector and CIXF1 filename wrapper are not yet ported. The predictor route can select adaptive-range with `--backend range`; `--backend count-range` selects coder 5. Both use the frozen order-0, bucket-bits-8 model. The fixed mixer tries all three reference learning rates and retains the shortest canonical payload. Timing-dependent Python selector behavior is not reproduced; Rust's current `auto` option compares only raw, run-length, composition, and DEFLATE candidates. LZ, predictor, PPM, BWT, stride and phrases are available as explicit `--route` values; the native `auto` option is not the frozen Python effort selector. LZ uses a bounded 8-candidate chain over a 65,536-byte window and requires a 16 MiB working-memory allowance. PPM requires a 64 MiB working-memory allowance. `--memory` bounds estimated codec working allocations, not executable/shared-library RSS; peak RSS is measured separately. `--threads` does not enable parallelism. The CLI handles one input path per invocation. SIGINT returns nonzero and removes incomplete file output; this is verified on the current Unix host.

## Verification

Run `python3 scripts/verify_rust_native.py`, `python3 scripts/verify_rust_streaming.py`, `python3 scripts/verify_rust_cixb1.py`, and `python3 scripts/verify_rust_portfolio.py` from the repository root. The first creates temporary correctness fixtures, cross-decodes fixed routes, verifies canonical bytes and checks malformed input. The second uses actual pipes, an idle producer, a delayed consumer, irregular writes, an empty stream and a stream larger than its codec-memory budget. Test fixtures are correctness checks only, not compression-performance evidence. Silesia-only performance evidence is recorded in `docs/research/2026-10-01-rust-native/silesia-results.json`.


The [Squash plugin](../../squash/README.md) registers the codec through Squash 0.8 splice callbacks and streams directly through the Rust C ABI.
