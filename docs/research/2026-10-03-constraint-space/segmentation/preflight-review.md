# Segmentation reference preflight review

Status: approved for the frozen staged screen after read-only adversarial
review. No build, test, codec, generator, or benchmark command was run for this
review. Production source is unchanged.

Reviewed artifacts:

- `rust/cix-native/experiments/constraint-space/segmentation_reference.rs`
  at SHA-256
  `967c965dde6640039039a9a7b880ad5e3e1c0112f5c9de3c8ed75d95bbba5f3e`;
- `evidence/PLAN.md` at
  `a639df4fc710ce888d87d28078b5a0251b196fb5a9fa9bd06b99914937f467f2`;
- `evidence/run.py` at
  `f5d377d790b2f9a3c69cf3478762dd2dc3628704ebd106581a371bf89441d27f`;
- `evidence/fixtures.py` at
  `971f3fe063d543ff3636f7fa776f9b7ad94f793e62572d0e5793bbca98436601`;
- `evidence/schedule.py` at
  `e6fcb0db00395f29f42285075d75d1dddba0c196317daa1e0246758a33b9a261`;
- `evidence/freeze.json` at
  `be6f38a9274610582f1d146e259b46b3f903635e01bedfebdbcc811be5c61df7`.

## Decision

No blocking source or prepared-evidence defect remains for this scope. The
screen may run under the frozen scheduler lease. Execution results still need
their declared fresh restoration, hashes, raw receipts, resource readbacks,
and final artifact binding before they become qualification evidence.

## Source correctness

Every admitted edge tries exactly four fixed routes: raw identity, canonical
Huffman, order-0 adaptive with an empty history and one model, and legacy LZ at
effort 1 with an empty history. Each candidate pays its complete route payload.
The selected edge additionally pays the common nine-byte route, decoded-length,
and payload-length record. The 17-byte archive header is added once. Because
all route state resets at every edge, these costs are additive; the source does
not imply cross-segment history or model sharing.

The fixed controls are mandatory segmentations. `fixed_choice` visits only
each adjacent pair returned by `fixed_points`, so it cannot silently coalesce
declared blocks. The adaptive score only creates a bounded candidate-cut bank;
the actual route and partition decision uses materialized physical edge costs.

The dynamic program retains a state for every endpoint and admitted segment
count. It therefore remains exact under the 32-segment cap even when a cheaper
prefix has used more segments than a costlier prefix. Final selection minimizes
physical cost and then segment count. Equal-cost, equal-count partitions keep
the first stable predecessor; route-ID tie-breaking applies within an edge.
The admitted partition counter uses the same segment cap and fits the frozen
64-bit host at the largest 64-byte all-cut reference.

Tiny exhaustive checking independently enumerates partitions but deliberately
reuses the source's measured best-edge matrix. The Python runner implements a
separate endpoint-by-count recurrence over that emitted matrix. These checks
support exact partition-cost claims for the supplied edge weights. They are
not independent implementations of the four route encoders and must not be
reported as such.

## Framing and parser bounds

The archive pays all boundary information through each segment's decoded
length. Decode bounds the archive, source length, segment count, cumulative
decoded length, and each payload slice before reconstruction. It rejects zero
length segments, unknown route IDs, truncation and trailing bytes, inconsistent
empty framing, length overflow, and final source-length or CRC disagreement.
The Huffman wrapper checks the nested decoded-length field against the already
bounded segment length before entering the Huffman decoder. Adaptive and legacy
decoders receive the bounded segment length and fixed model limits.

The prepared malformed set covers truncation, trailing bytes, excessive source
length and segment count, zero segment length, excessive payload length,
unknown route ID, source CRC disagreement, and a contradictory nested Huffman
length. Decoder output is written only after full validation, and the harness
requires failure without an output file.

## Prepared evidence

Each retained native archive is decoded by a distinct child invocation and the
restored file is SHA-256 checked against its frozen input. The in-process check
inside the encoder is only an internal round trip and is labelled accordingly.
The runner independently parses the NCSC envelope and accounts for the
17-byte header plus every nine-byte segment record and payload. The fixed,
adaptive, tiny, and all-cut arms all use the same archive format and four-route
portfolio.

The freeze binds the reviewed source, plan, runner, generator, scheduler,
toolchain, sealed native library and native dependencies, production control,
and external control binaries. The schedule declares one CPU, a 2 GiB memory
limit, no swap, 64 MiB active temporary space, and phase deadlines. Actual
compliance remains conditional on post-run cgroup, affinity, exit-status, hash,
and artifact readback.

## Claim limits and later hardening

- Exactness is limited to the four reset routes, supplied candidate cuts, and
  32-segment cap. It is not global codec or streaming segmentation optimality.
- The exhaustive and Python checks share source-emitted edge weights. They
  validate partition selection rather than route implementations.
- The runner's independent archive accounting records the actual numeric route
  ID but does not compare it with the route-name string in encoder JSON. Archive
  size, framing, and restoration do not depend on that string, so this does not
  block the staged screen. A final report should prefer the parsed numeric route
  ID or add the simple mapping assertion before making route-name claims.
- The synthetic held-out variants are only frozen variants within this staged
  experiment. They do not support corpus, production, or unseen-data claims.

