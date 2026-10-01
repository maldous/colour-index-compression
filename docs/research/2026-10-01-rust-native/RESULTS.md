# Native Rust implementation and measurements

## Subsequent code update (correctness checked, not performance measured)

The native encoder/decoder now supports CIXG1 route IDs 2 (composition), 3
(LZ), 4 (predictor), 5 (BWT), 6 (stride), 7 (phrases), 8 (PPM), 9
(fixed mixer), and 10 (DEFLATE), in addition
to raw, runs and DEFLATE. LZ uses the frozen 4-byte key, 8-candidate chain and
65,536-byte window. PPM uses order 3 and escape mass one. Exact arbitrary-
precision `BigUint` ranks are used for alphabet-set, histogram and permutation
ranks; fixed composition tiles are 1024 symbols. The reference 32-bit arithmetic
coder supports PPM, type-class range decoding, adaptive coder 4 and count-range
coder 5. Fifty-three fixtures cross-decode both ways with canonical route
bytes; the PPM fixtures are 1 KiB, and an adaptive-range predictor archive is
byte-identical to the Python reference. Count-range coder 5 and fixed mixer route 9 have canonical Python parity checks. These code
updates have not been performance-timed. The prior timing table below measures
the earlier raw/run/DEFLATE implementation and remains exploratory because swap
was active.

Reference: Python commit `80b95427725ecf59d626b2982d50f6349abd56e1`, isolated in a separate worktree. The frozen Python sources are unchanged by this branch. Format references are `CIXF1`/`CIXM6` and `CIXG1`; this implementation writes and reads CIXG1, bounded CIXB1 and a limited CIXM6 subset without changing any format version.

Build/host: Rust `1.98.1`, Cargo `1.98.1`, system zlib `1.3`, Linux x86_64. Build IDs were portable optimized `release`, `release-lto` (thin LTO), and a release build trained with merged LLVM profile data from the full Silesia set. All data comparisons use the existing local Silesia manifest only.

## Verified native subset

A bounded CIXB1 direct-backend path has now been added in Rust. It writes and reads the frozen 47-byte envelope for policy-eligible gzip, bzip2, xz, zstd, and Brotli settings (11 backend/profile combinations total). The new synthetic fixture verifier checks both decode directions plus truncation, envelope trailing bytes, and checksum damage. The native portfolio selector is now implemented with a profile-fixed candidate count: 4 for fast, 5 for current and 16 for size, including complete archive overhead in comparisons. Inputs are limited to 16 MiB; fast/current require 128 MiB working budget and size requires 384 MiB. The selector is bounded by input and candidate count, but does not reproduce the Python worker deadlines/timing-dependent selection. CIXM6 remains a separate format and is not replaced by this selector. A synthetic correctness verifier cross-decodes the selected output with Rust and Python-compatible backend decoders. A separate legacy verifier decodes Python-produced raw/multinomial CIXM6 streams and CIXF1-wrapped streams.

The current supported CIXG1 route set and explicit remaining gaps are documented in the compatibility matrix below; the performance results that follow are from the earlier raw/run/DEFLATE-only build. Correctness fixtures include all currently ported routes.

The compatibility matrix and unsupported paths are in [`rust/cix-native/README.md`](../../../rust/cix-native/README.md). Legacy CIXM5/CIXM6 decoding now supports every frozen block mode 0–20, including nested LZ/BWT/PPM, all defined transforms and chain inner codecs, persistent adaptive models, periodic coding, and expert mix. The verifier checks Python-produced payloads, cross-decodes complete archives, and validates stream CRC/footer; undefined modes are rejected. CIXM6 encoding writes modes 0/1 (raw/multinomial), but its complete mode selector remains unsupported. CIXF1 metadata footers are emitted and validated, and `uncix` uses the safe embedded basename as its default output on regular files. CIXB1 portfolio selection is supported as a bounded native selector, but does not reproduce the frozen Python timing-dependent selector. CIXB1 direct single-backend encoding/decoding is supported for the eligible preset combinations documented in the CLI README. A native Squash 0.8 plugin (upstream quixdb/squash commit `713eeca85cccadde39bf57f8b59ea663a085a347`) was built and smoke-tested through its file API: empty, tiny and mixed inputs round-tripped at Squash levels 1 and 9. This is integration correctness evidence only; it is not a compression data comparison or performance benchmark.

## Streaming checks

Actual Unix pipes verified a partial frame and reconstructed bytes become available before encoder EOF/footer. A 100 ms idle flush produced the first output in 100–101 ms in repeated checks. A 3 MiB irregular-chunk input, larger than its 1 MiB codec-work budget, round-tripped through a consumer delayed 200 ms; the producer blocked until the consumer drained output. Empty streams, truncation, frame/footer corruption, extra DEFLATE bytes, contradictory history flags and SIGINT temporary-file cleanup were checked. Evidence is in `streaming-verification.json` and `fixtures.json`.

Every frame is independently decodable. No native route retains history across frames. Positive `--history` is explicitly unsupported; persistent-history streaming therefore has no comparison result. `--block-size 1MiB` is accepted but effective CIXG1 frames are capped at 65,536 bytes to retain Python format compatibility. Decoder output can precede whole-stream footer verification; only a valid terminal checksum confirms the complete stream.

## Silesia comparison

All 12 complete inputs were read from the existing pinned local manifest and rehashed before each run (211,938,580 bytes total). The matched fixed configuration was Python `cix.pipeline` forced route `deflate`, backend `deflate`, effort `fast`, 32,768-byte frames, history zero; Rust used the same frame size/route and level six. Rust input was piped through `cat`; archives went directly to files. Both decoders independently restored and SHA-256 verified each file. Rust auto-selection was also run and Python-decoded. The complete per-file receipts are in the three `silesia-results-*.json` files.

| Build | Fixed archive total | Rust fixed encode | Rust auto encode | Rust decode | Peak Rust RSS |
|---|---:|---:|---:|---:|---:|
| Release | 73,650,399 B | 31.26 MiB/s | 31.26 MiB/s | 199.57 MiB/s | 2.75 MiB |
| Thin LTO | 73,650,399 B | 31.43 MiB/s | 31.29 MiB/s | 199.04 MiB/s | 2.50 MiB |
| Silesia-trained PGO | 73,650,399 B | 31.20 MiB/s | 31.18 MiB/s | 189.77 MiB/s | 2.75 MiB |
| Python forced reference | 73,650,399 B | 2.22 MiB/s encode | — | 123.12 MiB/s | 21.68 MiB encode / 20.00 MiB decode |

All Rust fixed archives matched Python byte-for-byte. Rust auto-selection saved 70 bytes across the 12 files. The Python forced-route receipt attributed 26.73 seconds to profiling/worker launch/selection overhead. Native auto-minus-fixed encode time was below 0.03 seconds across the suite and within timing resolution. PGO did not improve these timings. Current release binaries are 669,008/669,224/669,328 bytes (`cix`/`uncix`/`cixcat`); thin-LTO binaries are 567,072/567,144/567,296 bytes (15.2% smaller).

**Timing limitation:** the frozen experiment required no swap, but an audit after the runs found active host swap devices (`/swap.img` and `/swap`, with 6.5 GiB and 20.5 GiB shown in use). Per-command swap attribution is unavailable. These performance and RSS numbers are therefore exploratory only, not qualification results. No further timing run was made under this condition. Correctness, complete sizes and hashes remain valid.

The PGO training profile used all 12 Silesia files. Its merged `llvm-profdata` file and training binaries were temporary and are not packaged. Rebuild instructions appear in the CLI README; repeat the benchmark on a no-swap host before relying on performance claims.
