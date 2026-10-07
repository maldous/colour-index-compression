# Current native segmentation and selection audit

Status: read-only source audit, 2026-10-03. No build, test, codec, corpus, or
benchmark job was run for this audit. This document describes the current
production implementation and does not qualify a new segmentation method.

## Immediate conclusions

1. Production has no content-adaptive boundary selector. CIXG, CIXM6, and
   CIXZ1 read a fixed maximum block size; EOF and an optional idle flush can
   create a shorter final or partial block. Whole-file BEST can compare the
   fixed 16, 32, and 64 KiB choices on inputs no larger than 16 MiB, but it does
   not search arbitrary boundaries.
2. CIXG blocks are independent. For a fixed block, the selector compares exact
   materialized payload byte lengths, with a common 41-byte frame cost. The
   route shortlist, model beams, memory admission, and time admission are
   heuristic or bounded, so this is not an exhaustive optimum over all routes
   and parameters.
3. CIXM6 updates its one MiB source history, recent complete-block queue, and
   persistent adaptive models after every reconstructed block, including raw
   blocks and blocks encoded by another mode. A route winner does not suppress
   state advancement. Boundaries still affect the recent-block reference set,
   and possibly any model transition whose equivalence under repartitioning has
   not been proved. A position-only dynamic program is therefore not an exact
   reference for unrestricted CIXM6 segmentation.
4. CIXZ1 makes a greedy per-region choice among raw, a continuing zstd frame,
   and a complete nested CIXG2 archive. Its cost comparison charges the current
   transition/reset allowance, but choosing zstd preserves state while choosing
   raw or nested CIXG closes it. The local comparison is not a global
   segmentation optimum.
5. Production has reusable causal state and exact whole-block references. It
   has no inter-block shared-template or shared-dictionary representation with
   independently serialized template identity and edit instructions. The
   record/periodic and transform-chain structures are inferred and paid inside
   one block.

These facts block any claim that a new position-only shortest-path search is an
exact replacement for current M6 or CIXZ1 selection. Such a reference must
either use independently reset segment candidates, disable stateful/reference
routes, or carry every future-relevant state in the recurrence.

## Minimal native route trace

The smallest useful existing trace is a single CIXG2 streaming encode. Explicit
`cixg2` plus `--stream` excludes both whole-archive BEST and automatic CIXZ1,
and one candidate worker keeps trace ordering simple:

```bash
target/release/cix \
  --format cixg2 --stream --best \
  --threads 1 --parallelism candidates \
  --block-size 16KiB --memory 512MiB \
  --explain -c INPUT > TRACE.cix 2> TRACE.stderr
```

Root should substitute one already frozen, hash-bound small input and run this
once through the existing scheduler. The receipt should bind the release
binary, input, command argv, archive, stderr, exit status, cgroup path,
`cpu.max`, `memory.max`, `memory.swap.max`, and actual child affinity. A fresh
`uncix` restoration is useful qualification evidence but is a separate command
from the minimal trace.

Expected stderr contains one `region=N` record per block with
`source_bytes`, every evaluated or skipped candidate, `selected_route`, nested
`backend`, and `payload_bytes`, followed by aggregate selected source bytes.
Time and memory skips are part of the decision record. The output is an
execution trace of a bounded search, not proof that an omitted candidate could
not win.

Current `--explain` does **not** emit a corresponding per-mode CIXM6 trace.
Explicit CIXM6 only reports the set of modes omitted by its memory gates. A
whole-file BEST trace reports complete CIXM6 archive trial sizes, not the mode
chosen for each M6 frame. Automatic CIXZ1 does emit outer region costs, while
its nested CIXG candidate is deliberately encoded with `explain: false`.

## Relevant CLI semantics

The help text exposes format, route, backend, block size, memory, threads,
parallelism, history, independent blocks, streaming, idle flush, profile,
portfolio, and external-backend controls (`main.rs` lines 149-150). Their
effective segmentation semantics are narrower:

- `--block-size` sets a fixed maximum and is capped at 65,536 bytes
  (`main.rs` lines 5116-5134). It does not enable boundary search.
- `--flush-interval` can end a nonempty block while stdin remains open. This is
  a wall-clock producer-idle boundary, not an input-content decision.
- `--parallelism blocks` runs independent CIXG blocks in parallel and preserves
  output order. `--parallelism candidates` parallelizes trials inside the
  current CIXG block. M6 rejects an explicitly set parallelism option
  (`main.rs` lines 4979-4985).
- `--route` and `--backend` constrain CIXG dimensions. Explicit M6 rejects a
  route and backend/independent-block overrides (`main.rs` lines 4908-4910 and
  4963-4974).
- A nonzero `--history` is currently rejected with “persistent history is not
  supported by the current native routes” (`main.rs` lines 5064-5070). It is
  not a way to tune the internal fixed M6 history window.
- `--independent-blocks` describes the already-independent CIXG behavior and
  constrains whole-file BEST by excluding M6/external trials. There is no M6
  reset-block variant behind this flag.
- `--stream` prevents whole-archive BEST. At BEST with `format=auto` and no
  conflicting expert control it permits automatic CIXZ1; setting an explicit
  CIXG format prevents that stateful dispatch (`main.rs` lines 4746-4764).

## Source identity

The qualified production reference is commit
`d3a2cd416e49f93403d1dbd348a3e9a45db66ec6`, recorded in
[`release-d3a2/freeze.json`](../../2026-10-03-rust-rnd/release-d3a2/freeze.json). The audit
was made at HEAD `6c9758b9a709cb68057141afc0dcdca9f63f8664`.

The following read-only check returned exit 0 and no path log:

```bash
git diff --exit-code d3a2cd416e49f93403d1dbd348a3e9a45db66ec6..HEAD \
  -- rust/cix-native/src rust/cix-native/tests \
     rust/cix-native/Cargo.toml Cargo.lock
git log --oneline d3a2cd416e49f93403d1dbd348a3e9a45db66ec6..HEAD \
  -- rust/cix-native/src rust/cix-native/tests \
     rust/cix-native/Cargo.toml Cargo.lock
```

The recursive Git tree listing hash for those paths is the same at both
revisions:
`e3bc883d84764ce02aeabbbfc05cd31e810c6014e1a467d21550a5de7c7576ba`.
The frozen `main.rs` and `chain.rs` hashes also match the freeze:
`b26c5760...4336` and `b1aa354f...1839`. Thus there are no tracked production
Rust changes between the frozen revision and current HEAD. Untracked files
under `rust/cix-native/experiments/`, including the constraint-space and record
position template prototypes, are excluded from this production audit.

## Decision hierarchy

| Level | Current decision | Cost used | Exactness and limits |
|---|---|---|---|
| File/container | Named, seekable BEST compares complete CIXG1/CIXG2 and M6 archives at fixed block sizes, plus allowed external CIXB1 candidates | Actual complete archive bytes after in-process exact reconstruction | Strictly smaller wins; ties keep the incumbent. Exact only among trials that finish and pass memory/deadline admission. Internal CIXG/M6 trials remain bounded searches. |
| Streaming container | Automatic BEST with `format=auto` and no conflicting expert option enters CIXZ1 when its memory policy admits it | Policy eligibility, followed by per-region costs | This is not a measured whole-container competition against CIXG. The first zstd probe is materialized, but its byte count is diagnostic rather than a container-selection comparison. |
| Boundary | Fixed maximum block size; EOF or idle timeout may end a partial block | No boundary score | Not content adaptive. Idle boundaries depend on producer timing. CIXG defaults are 64 KiB FAST, 32 KiB default, and 64 KiB BEST. The global maximum is 64 KiB. |
| CIXG block route | Raw plus a profile-derived finite route/backend set | Actual payload bytes; every route has the same 41-byte outer frame for a fixed source block | Exact strict byte comparison among completed candidates. Shortlisting, memory gates, search deadline, and per-trial deadline can omit winners. Equal bytes retain the earlier ordered candidate. |
| CIXG substream coder | Each fixed route-specific byte stream chooses a coder allowed by its backend | Actual substream payload bytes; its 9-byte descriptor is common within that stream | Exact among materialized coders. The composition coder is only offered when an 8 KiB entropy sample is below 7.5; explicit context/Huffman backends compare only raw and that backend. Stream decomposition itself is fixed by the route. |
| CIXM6 block mode | Raw plus modes 1 through 20 subject to length, effort, beam, and memory conditions | Exact M6 frame bytes: mode byte, both varints, and payload | Strictly smaller wins; ties retain raw or the earlier trial. Exact only among admitted/materialized candidates. Explicit M6 has no per-block time budget; a whole-file M6 trial inherits its outer BEST deadline. |
| M6 record/periodic/chain internals | Estimated widths, lags, or transforms are shortlisted, then concrete inner encodings are materialized | Actual complete mode payload bytes after shortlist | Estimator/beam selection is heuristic. The winner within the materialized set is physical-byte exact. Chain cache reuse changes work only and is specified to fail open. |
| CIXZ1 region | Continuing zstd, raw, or a complete nested CIXG2 archive | Actual current payload plus exact three-byte zstd finalization and, when leaving an active zstd segment, its 41-byte reset frame | Locally exact for the materialized alternatives. Tie order is zstd, then nested CIXG, then raw. Greedy selection is not globally exact because it changes whether zstd state survives. |

## Wire costs relevant to segmentation

- A CIXG1/CIXG2 archive has a 13-byte global header, each data frame costs
  `41 + payload_len` bytes, and the terminal digest frame costs 41 bytes.
  Therefore a new boundary has a real 41-byte price even though that price is
  common to route candidates for one already-fixed block.
- A CIXM6 archive starts with five magic bytes and a varint history limit. Each
  data frame costs `1 + varint(source_len) + varint(payload_len) + payload_len`.
  Its footer costs one mode byte, `varint(total_source_len)`, and four CRC
  bytes. CIXF1 additionally appends the basename, a four-byte name length, and
  five trailer magic bytes.
- CIXZ1 has a 13-byte global header and the same 41-byte frame prefix as CIXG.
  Its footer is a 41-byte terminal frame plus any active zstd finalization
  bytes. Leaving an active zstd segment for raw or nested CIXG writes a separate
  reset frame and its zstd tail.

These costs are not interchangeable. In particular, summing standalone CIXG
archive sizes would overcharge global headers and footers, while summing only
payloads would omit the boundary cost that makes segments decodable.

### File/container evidence

[`portfolio_auto.rs`](../../../../rust/cix-native/src/portfolio_auto.rs) lines
51-75 restrict whole-archive BEST to bounded regular named inputs at effort 9,
without streaming, flush, history, external, or portfolio conflicts. Lines
317-338 validate each archive and replace the incumbent only on strict size
improvement. Lines 432-618 enumerate CIXG and M6 trials. For inputs up to
16 MiB the only automatic block sizes are 16, 32, and 64 KiB. Lines 461-500 and
572-601 divide finite family deadlines among remaining trials. Lines 714-853
select and report the final complete archive.

The production CLI dispatch in [`main.rs`](../../../../rust/cix-native/src/main.rs)
lines 4746-4868 orders whole-archive BEST, explicit M6/CIXF1, explicit
portfolio/external encoding, automatic persistent CIXZ1, and ordinary CIXG.
Lines 5256-5279 compute these eligibility decisions before opening the selected
output route.

### CIXG boundary and route evidence

`main.rs` lines 2279-2316 fill the caller-selected block size and stop early
only for EOF or idle flush. Lines 2483-2560 select and write one independent
route per block and then one whole-stream digest footer. The parallel block
implementation states its independence directly in
[`gstream.rs`](../../../../rust/cix-native/src/gstream.rs) lines 1-2 and submits
the same selector independently at lines 253-289. Ordered output does not add
cross-block model state.

[`selection.rs`](../../../../rust/cix-native/src/selection.rs) lines 10-22 name
the eleven CIXG routes. Lines 101-155 construct the ordered finite backend and
PPM candidate set. Lines 319-344 define the effort-dependent block, sample,
route-cap, deadline, and worker-memory values. Lines 419-458 take four spread
samples from each block. Lines 529-583 apply the feature thresholds and ordered
fallback list, then truncate to the effort route cap.

`main.rs` lines 1248-1258 define strict cost/tie behavior; lines 1317-1489 show
the memory and deadline exclusions; lines 1516-1598 preserve deterministic
candidate-index ties even when candidate work is parallel. Lines 1691-1778
state why payload length is the complete per-block discriminator and construct
the exact `--explain` record. Lines 2393-2410 show the common 41-byte frame.

Substream choice is in `main.rs` lines 551-613. Raw is always available. RLE is
normally available; the selected backend adds composition, deflate, range, or
count-range, while explicit context-range and Huffman use their own restricted
raw-versus-coder comparison. `min_by_key(payload.len())` retains the earlier
candidate on equality. Route-specific transformations and stream partitions
are fixed at lines 1087-1107; CIXG mixture explicitly receives empty history.

### M6 modes, state, and references

`main.rs` lines 2580-2605 compute complete frame size and accept only strict
improvement. Lines 2618-2628 reserve the one MiB source history, recent-block
reference budget, and optional persistent-state allowance. Lines 2631-2810
contain the mode gates and canonical trial order:

```text
raw;
type-class and context;
wavelet and adaptive;
sparse and runs;
recent exact block reference;
legacy LZ/BWT/transform;
bitplane, chain, numeric;
histogram;
record and periodic;
PPM;
expert mix and fixed mix;
persistent adaptive.
```

The implementation's actual call order is visible at lines 2904-2930. The
record/periodic candidate requires at least 256 bytes and effort 4; the chain
candidate requires at least 32 bytes and effort 8. Other modes have their own
length, effort, and memory gates. These conditions are candidate policy, not a
proof that an excluded mode loses.

After selection, lines 2931-2943 write the winner, append the source bytes to
history, and retain the complete source block for later exact-reference mode 9.
The recent queue is independent of which route won, but it is defined by prior
block boundaries. The encoder keeps at most 1,024 recent blocks and the byte
budget. The decoder uses the same source history and retains up to 4,096 blocks
within the same byte budget (`main.rs` lines 4117-4179); the byte budget is the
binding practical limit for legal encoder output.

[`stateful.rs`](../../../../rust/cix-native/src/stateful.rs) lines 1-6 specify
that all three persistent models observe every reconstructed block. Lines
394-413 choose the smallest complete mode-13 payload with lower model ID on a
tie, and lines 435-440 update every model. Encoder line 2808 and decoder line
4165 both perform that update regardless of the selected block mode.

History-consuming M6 candidates include context type classes, legacy LZ,
adaptive context coding, PPM, expert mix, fixed mix, and persistent adaptive
mode. The transform-chain decoder explicitly uses no preceding M6 history in
[`chain.rs`](../../../../rust/cix-native/src/chain.rs) lines 1581-1603.

Modes 14 and 15 do not share a template across blocks.
[`record_periodic.rs`](../../../../rust/cix-native/src/record_periodic.rs) lines
117-174 discover and score widths from the current block; lines 176-205 write a
width and independently code every lane; lines 219-325 discover current-block
lags and serialize the chosen lag, operation, inner mode, and payload. All
information required by their decoder is paid within that mode payload.

### CIXZ1 state transitions

[`streaming_backend.rs`](../../../../rust/cix-native/src/streaming_backend.rs)
lines 388-415 materialize a complete independent CIXG2 archive for the current
region. Lines 489-528 also advance a tentative persistent zstd context. Lines
531-552 compare the three current costs. Lines 596-635 close and reset zstd
before raw or nested CIXG, or confirm identical advancement of the two zstd
contexts before preserving zstd state. Lines 667-734 apply this greedy decision
to fixed-size/EOF/idle regions. This is real state sharing, but it is zstd stream
state rather than a CIX shared-template format.

## What a segmentation experiment can reuse now

- CIXG offers independently decodable segments, common frame accounting,
  exact materialized payload sizes, deterministic tie order, candidate
  explanations, bounded memory admission, and fresh archive decoding.
- `--format cixg2 --stream` prevents whole-file packaging and automatic CIXZ1,
  making it the safest existing control for an additive segmentation reference.
- Explicit `--route` and `--backend` constrain representation and coder while
  preserving raw fallback. They can isolate route effects, but a forced route
  is still allowed to lose to raw.
- M6 offers a much broader native candidate family, causal prefix history,
  persistent learned counts, and exact full-block deduplication. Reusing that
  family in an exact partition search requires an explicit reset variant or a
  stateful reference.
- Existing frame writers, varints, hashes/CRC, complete archive decoders,
  bounded readers, and resource ledgers can support materialization and
  verification. They do not supply a boundary optimizer.

## Correctness conditions before segmentation implementation

These are blockers for an *exact* claim, not requests for a larger production
change:

1. Freeze whether every candidate edge resets or preserves state. Do not mix
   CIXG-reset costs with M6/CIXZ1-preserving transitions in one position-only
   recurrence.
2. Define the target wire format before scoring. Pay the actual per-segment
   route/mode byte, lengths, boundary representation, model/parameter bytes,
   padding, checksums, reset/finalization bytes, global header, and footer.
3. Preserve candidate order and strict tie behavior. A segmentation experiment
   using a different tie rule cannot claim byte identity with production.
4. Treat heuristic shortlist/beam estimates only as pruning hypotheses. An
   exact small reference must materialize every member of its declared finite
   candidate bank and independently restore it.
5. If M6 references are allowed, the state key must distinguish the ordered
   recent complete-block queue, not only the last source bytes or current
   position. If persistent model state is collapsed to source position, prove
   that its update is invariant under every allowed repartitioning.
6. Report memory/deadline omissions as omissions. They do not establish a
   size lower bound.

## Test and evidence coverage already present

- [`cli_archive_oracle.rs`](../../../../rust/cix-native/tests/cli_archive_oracle.rs)
  lines 134-301 runs explicit CIXG1 streaming controls, enumerates 35 complete
  route/backend archives for a fixed tiny block, fresh-decodes them, and invokes
  the existing automatic BEST `--explain` path. It is deliberately CIXG1 and
  fixed-boundary coverage.
- [`auto_best_portfolio.rs`](../../../../rust/cix-native/tests/auto_best_portfolio.rs)
  tests named BEST complete archives and fresh CLI decode, an explicit block
  override retaining the matching M6 packaging trial, streaming exclusion from
  whole-archive BEST, and valid empty-input fallback.
- [`selection_overrides.rs`](../../../../rust/cix-native/tests/selection_overrides.rs)
  tests route/backend compatibility, raw fallback, intrinsic labels, and invalid
  candidate dimensions.
- [`streaming_pipe.rs`](../../../../rust/cix-native/tests/streaming_pipe.rs)
  tests pre-EOF frame emission, idle partial frames, live decode, malformed and
  truncated streams, slow consumers, and bounded-memory failure paths.
- `stateful.rs` lines 510-530 test mode-13 restoration across an observed block
  boundary. `streaming_backend.rs` lines 1094-1200 cover mixed persistent
  regions, corrupt frames, bounded nested output, reset behavior, and footer
  state. `chain.rs` lines 1956-2017 cover exact cache parity and fail-open
  admission.
- [`sonar_m6_routes.rs`](../../../../rust/cix-native/tests/sonar_m6_routes.rs)
  is an environment-gated fixture emitter for legacy modes 4, 11, and 12. It
  returns without assertions when `CIX_M6_FIXTURE_DIR` is absent; it is not a
  comprehensive M6 selector/history test by itself.
- [`oracle.rs`](../../../../rust/cix-native/src/oracle.rs) lines 1-13 explicitly
  excludes framing, M6 modes, transforms, block segmentation, history sharing,
  external codecs, and the private CLI route encoder. Its exact payload oracle
  must not be cited as an exact segmentation or production-selector oracle.

No current test enumerates arbitrary boundary sets against production M6 or
CIXZ1 state transitions. That absence is expected because production has no
such optimizer, but it means a new segmentation claim needs its own frozen
small exhaustive reference and archive-only restoration evidence.
