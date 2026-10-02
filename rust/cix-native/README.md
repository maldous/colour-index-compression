# CIX (pronounced “six”) native command-line tools

This private research build supports CIXG1 and its versioned CIXG2 extension, plus CIXM6/CIXF1 and the versioned CIXZ1 streaming container. `.cix` means a CIX stream archive; it is not ZIP or gzip. It is native Rust and does not launch Python. Native linking uses system zlib, bzip2, liblzma, Zstd and Brotli libraries plus vendored libbsc 3.3.12 and ZPAQ 7.15 source. Explicit CIXB1 backend facilities remain separate from native route selection, and their gains are reported as backend gains.

See [FORMAT-CIXB1.md](FORMAT-CIXB1.md) for the bounded native-backend envelope,
its 14 configuration-level candidates, memory rules and cancellation limits.

## Build and install (Linux x86_64 verified)

Install Rust stable, a C compiler and the development/linker packages for zlib, bzip2, liblzma, Zstd and Brotli (on Debian/Ubuntu: `zlib1g-dev libbz2-dev liblzma-dev libzstd-dev libbrotli-dev`). From the repository root run:

```sh
cargo build --release --locked --manifest-path rust/cix-native/Cargo.toml
install -Dm755 rust/cix-native/target/release/cix ~/.local/bin/cix
install -Dm755 rust/cix-native/target/release/uncix ~/.local/bin/uncix
install -Dm755 rust/cix-native/target/release/cixcat ~/.local/bin/cixcat
```

The checked-in `Cargo.lock` pins Rust dependencies. For the delivered LTO build use `CARGO_BUILD_JOBS=2 cargo build --profile release-lto --locked --manifest-path rust/cix-native/Cargo.toml --bin cix --bin uncix --bin cixcat --lib`. Checked-in host binaries are in `dist/`; source, binary hashes and native-library versions are in [native-release.json](../../dist/native-release.json). No other operating system or architecture has been built or verified.

## Examples

```sh
cix -6 report.dat                 # writes report.dat.cix; keeps report.dat
uncix report.dat.cix               # writes report.dat; refuses overwrite
cix --external zstd --profile default report.dat > report.cix  # one bounded CIXB1 backend
cix --external bsc --profile size --memory 2GiB report.dat     # libbsc BWT/QLFC CIXB1 backend
cix --portfolio default report.dat  # compare CIXG1 and eligible CIXB1 candidates
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

`--fast` minimizes compression latency, no effort flag uses balanced DEFAULT, and `--best` expands the bounded candidate search for complete archive size. `-1`, `-6` and `-9` are aliases. `--explain` reports decisions and omissions; `--verbose` reports totals. Explicit route/backend overrides constrain their own dimension and retain compatible searches. Intrinsic coders reject contradictory pairs.

FAST uses bounded greedy matching with a fixed 256 KiB index and cheap
raw/run/DEFLATE substream comparisons. Automatic FAST selection does not run
exact composition-rank trials. Explicit expert backend choices remain
available. FAST defaults to 64 KiB blocks; DEFAULT retains 32 KiB, and BEST streaming
uses 64 KiB; admitted whole-file BEST also explores smaller legal blocks. The CLI and Squash splice entry point share this block policy.
Larger FAST blocks retain more opportunities and reduce frame overhead, but
can increase first-frame latency on a slow producer. Use `--block-size` or
`--flush-interval` to bound that delay. Route 3's wire grammar is unchanged;
existing CIXG1 decoders read the new FAST output.

`-f` permits replacing an output. File output uses a same-directory temporary file and atomic replacement. Inputs are retained by default; `-k` is accepted. Omitting FILE defaults to stdin and stdout, and `--` permits dash-prefixed names. `-c` with a named `-o` is rejected. Streaming is the default, with `--stream` available to state the requirement explicitly. The source is read once without seeking or spooling; only bounded blocks are buffered. Compression and decoding emit complete frames incrementally.

`--threads N` accepts 1 through 4. Native CIXG compression defaults to up to four available CPUs, reducing that default when the memory budget cannot accommodate the worker buffers. `--parallelism blocks` (default) runs independent blocks through one persistent worker pool. Results are written in input order; the outstanding queue is capped at the worker count. Slow output prevents further input admission. `--parallelism candidates` is an expert alternative that runs trials within one block concurrently. Workers share one scratch-memory reservation ledger. Heavy trials wait for permits; impossible requests are reported as omissions. There is no nested worker pool.

`--block-size` accepts bytes, KiB, MiB and GiB. CIXG1/CIXG2 frames currently allow at most 65,536 source bytes; larger requests are clamped with a stderr diagnostic. `--memory` accounts for retained buffers, worker stacks/profiling reservations and conservative route scratch estimates. Runtime, allocator and linked-library overhead are measured as RSS separately; this is not an OS RSS limit. Search and trial deadlines are cooperative in Rust loops. A coarse native-library call can finish after its deadline and is then omitted. Equal-size results use candidate order. Completed winners are capped by the raw fallback, including framing cost.

Parallel CIXG blocks have explicit model reset boundaries. Nonzero `--history` is rejected here; `--independent-blocks` describes this mode. CIXM6 retains its legacy causal history and persistent adaptive state, and remains serial. Its incompatible explicit independent-block request is rejected. Decode, external wrappers and portfolio modes also remain serial. `--external`/`--portfolio` are explicit CIXB1 backend facilities, not native CIX routes; they buffer a named regular input of at most 128 MiB and reject streaming.

FAST/DEFAULT use bounded CIXG selection. BEST on a named regular file of at most 128 MiB, admitted by the memory budget, compares complete CIXG1/CIXG2/CIXM6 archives and all 14 configured CIXB1 candidates. Explicit controls filter only incompatible candidates. Pipes, `--stream` and oversized inputs use bounded framed selection: CIXZ1 supports persistent Zstd history and bounded native candidates when admitted, otherwise CIXG streaming remains available. New automatic packaging and streaming coverage require the expanded release qualification; frozen d667 benchmark results do not describe these changes. CIXG1 gates PPM at order 3 and legacy mixture payload version 1. CIXG2 admits orders through 8 and versioned substream coders. The Python decoder is a historical compatibility validator, not a runtime or current optimization constraint. The corrected recurrence mixer uses payload version 3 and remains experimental; older version 2 prototypes retain their legacy decoding behavior.

`--flush-interval 100ms` emits a partially filled frame after the interval expires, including while a pipe producer remains open but idle. It uses Unix `poll`; it is best-effort and actual output time also includes encoding and downstream backpressure. Flushing occurs only at valid container frame boundaries. The decoder may emit verified block bytes before it sees the footer. Whole-stream integrity is confirmed only after it reads and validates the terminal SHA-256 frame; a missing or corrupt footer returns nonzero even if earlier blocks were already written.

## Compatibility at this checkpoint

| Operation | CIXG1 | CIXB1 direct archives | CIXB1 portfolio selection | CIXF1/CIXM6 |
|---|---|---|---|---|
| Rust encode | Yes; routes 0–10 and bounded route selection | Yes; eligible gzip, bzip2, xz, zstd, Brotli, ZPAQ 7.15 L5 and libbsc 3.3.12 with `--external`; input capped at 128 MiB | Yes; `--portfolio fast|default|size` compares a fixed, finite candidate plan under the 128 MiB CIXB1 input cap | CIXM6 bounded selector considers legacy modes 0–20 subject to block eligibility, effort and memory; automatic CIXM6 packaging remains contingent on final qualification; CIXF1 adds a validated UTF-8 basename wrapper |
| Rust decode | Yes; routes 0–10 with raw/run/exact-rank/range/DEFLATE substream coders | Yes; bounded backend decoders validate archive length and SHA-256 | N/A | CIXM5/CIXM6 modes 0–20; validates CRC/footer and optional CIXF1 metadata, errors explicitly on unknown modes |
| Python decode of Rust output | Yes; canonical fixed-route fixtures are byte-identical | Historical IDs 1–5 only; new IDs 6–7 require native decoding | N/A | Frozen Python decodes every implemented mode's canonical Rust payloads; CIXF1 wrapper round trips on tested fixtures |
| Exact original-byte restoration | Verified across empty, tiny, random, repetitive and mixed fixtures | Verified for every currently eligible backend/profile pair | N/A | Verified on frozen Python-produced CIXM5/CIXM6 fixtures for every mode 0–20, including nested PPM v2–v5 and malformed/truncated frames |

The frozen Python implementation remains available for historical compatibility checks; native Rust round trips and fresh decoder processes qualify new Rust features. Exact arbitrary-precision combinatorial ranks are implemented without narrowing exact ranks to machine integers. Fixed CIXM6 payload routes target Python's canonical bytes; Rust's bounded per-block selector charges complete frame size and uses `-1` through `-9` as an effort budget. Fixed routes are deterministic; bounded automatic search can omit candidates at time/resource limits and is not an exact reproduction of Python's timing-dependent route selection, and the LZ route uses a bounded hash-chain parser rather than Python's optional suffix-array parser on large blocks. Candidates exceeding the shared configured memory allowance are explicitly omitted with a stderr diagnostic. CIXM5/CIXM6 decoding covers the frozen modes 0–20 and rejects unknown modes. The explicit CIXB1 portfolio and external-backend facilities use finite candidates; ordinary named-file BEST compares all 14 configured direct candidates automatically when each is legal and admitted. Explicit CIXB1 selection is capped at 128 MiB, rejects streaming, and charges complete archive bytes. `--memory` bounds estimated codec working allocations, not executable/shared-library RSS; peak RSS is measured separately. The CLI handles one input path per invocation. Use tar pipelines for directories. SIGINT and SIGTERM return nonzero and remove incomplete file output; nonblocking Unix stdout writes make stalled pipe consumers interruptible; this is verified on the current Unix host.

## Verification

Run `python3 scripts/verify_rust_native.py`, `python3 scripts/verify_rust_streaming.py`, `python3 scripts/verify_rust_cixb1.py`, `python3 scripts/verify_rust_portfolio.py`, `python3 scripts/verify_rust_cixm6.py` and `python3 scripts/verify_rust_cixm6_selector.py` from the repository root. The native fixture verifier cross-decodes fixed routes and checks malformed input. The streaming verifier uses actual pipes, an idle producer, a delayed consumer, irregular writes, an empty stream and a stream larger than its codec-memory budget. The selector verifier checks all nine effort levels on six input classes with Python and Rust decoding. These tests are correctness checks, not compression-performance evidence. Silesia-only performance evidence is recorded in `docs/research/2026-10-01-rust-native/silesia-results.json`.


The [Squash plugin](../../squash/README.md) registers the codec through Squash 0.8 splice callbacks and streams directly through the Rust C ABI.

Local Rust tests: `CARGO_BUILD_JOBS=2 cargo test --release --manifest-path rust/cix-native/Cargo.toml`. Process tests exercise explicit two-worker pre-EOF output, idle flushing, slow consumers, stream length beyond the memory budget, fixed-route archive identity across worker counts, decoder model admission and stalled-output SIGINT. See the [adversarial review](../../docs/research/2026-10-01-cix-optimization/adversarial-parallel-review.md) for findings and remaining scope gaps.

The [current local optimization evidence](../../docs/research/2026-10-01-cix-optimization/adversarial-parallel-results.md) reports the measured scheduling and DEFAULT selector improvements, losses and remaining scope. DEFAULT PPM eligibility uses an input-derived prediction rate above 0.1 plus at least 64 prediction opportunities; tiny blocks retain the cheap shortlist. This policy does not affect FAST or BEST breadth.


## Expanded automatic BEST archive comparison

Ordinary `cix --best input` considers complete CIXG1/CIXG2/CIXM6 archives and all
14 configured CIXB1 descriptors: gzip, bzip2, XZ, Zstd, Brotli, two explicit
XZ dictionary settings, pinned ZPAQ 7.15 level 5, and libbsc 3.3.12. All
headers, backend framing, model/configuration bytes and integrity bytes count.
Backend gains are reported as backend gains, not as native-model improvements.
Conditional rank, transform-beam, prediction-event,
cost-aware parsing and rANS experiments remain contingent on final qualification.

The buffered BEST operation reads a bounded named file once; its source,
incumbent, trial and validation allocations are charged. Pipe and `--stream` operation retains bounded incremental framed output. Candidate reconstruction is checked against the source
without another whole-output buffer. `--explain` reports complete candidate
costs and native inner selection; ordinary BEST reports omissions to stderr.
Backend libraries are native; no Python process is used. XZ encoding polls
cancellation between native calls. One-shot bzip2, Zstd, Brotli and libbsc
calls can delay interruption until the library returns. In particular, a BSC
block may be as large as the 128 MiB CIXB1 input cap. This is a remaining
limitation of CIXB1 whole-archive candidates, not of framed CIXG streaming.

BEST searches a declared finite candidate space under safety budgets. The
current host has a verified portable Rust build and native C++ dependencies;
the release documentation makes no build or performance claim for another
host until it is built and checked there. BEST/decode default to a 2 GiB
working-memory budget, and candidates that cannot fit are reported as
omissions. It is not an exhaustive search of all segmentation, history,
transform-chain or packaging combinations. Explicit route/backend constraints
retain native candidate search in the other supported dimensions; incompatible
whole-archive candidates are excluded with an explanation.
