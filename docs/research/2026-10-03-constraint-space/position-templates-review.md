# RXP1 record-position template source review

Status: pre-execution, read-only adversarial review. No build, test, codec, or
benchmark command was run. This review covers
[`record_position_templates.rs`](../../../rust/cix-native/experiments/constraint-space/record_position_templates.rs)
at SHA-256
`6c62c4be0e861fbcf792f560059c31adb7a797034b55dc2e5d2d5c282c90a9f3`.
It does not qualify the experiment or modify production source.

## Decision

The physical archive accounting, arithmetic-progression inverse, combinadic
range checks, dense payload rank, exception bytes, and CRC envelope are
internally consistent. The source is not ready for a claim of bounded generic
combinadic work or three matched position-codec controls because of the
following blockers.

### Blockers before execution freeze

1. **Colex decode has a large legal-input CPU path with no operation or time
   bound.** `colex_unrank` handles as many as 8,192 records and about 4,096
   exceptions. For every exception it performs a binary search, and each search
   step recomputes `choose(mid, i)` using a multiplicative loop (lines 99-109
   and 193-219). Valid middle-density maps can therefore require many millions
   of large-`BigUint` multiply/divide steps. The encoder similarly calls
   `colex_rank`, which recomputes one binomial coefficient per exception.
   `MAX_N` bounds storage but does not establish a practical CPU bound.
2. **The forced zstd-gap control performs the unused colex rank first.**
   `position_map` constructs and packs the colex rank at line 271 before it
   checks `PositionPolicy::ZstdGaps` at lines 275-277. Thus the purported
   zstd-gap timing includes potentially dominant combinadic work for every
   discovered model. This does not change archive bytes, but it prevents a
   clean position-codec timing comparison and magnifies blocker 2.
3. **The prepared harness is not dispatch-safe yet.** It redirects the imported
   prior runner's raw-log directory but does not create that directory; it is
   currently absent, so the first `p.call` will fail while opening its logs
   unless an external wrapper creates it. The script also lacks a lease
   environment assertion, does not rehash the nine reused control archives,
   applies the imported 120-second timeout to every call despite the plan's
   30-second native limit, and omits two declared malformed classes. Details
   are below.

The smallest safe source correction is to avoid colex computation in the
forced-zstd branch. Colex also needs an algorithmic operation bound or a
stricter admitted `(records, exceptions)` domain before the format can be called
practically bounded. The runner issues require only pre-dispatch orchestration
repairs. None requires a broader candidate search.

## Later hardening and evidence conditions

- Forced colex and forced zstd rerun the whole model portfolio. They can select
  different `b`, mask, count mode, or count parameter. Their final archive
  difference is a portfolio-level result unless the harness confirms identical
  model metadata, `r`, `e`, payload bytes, and exception bytes across arms.
- The CLI has no forced progression policy. It accepts only `auto`, `colex`,
  and `zstd-gaps` (lines 769-782). Progression is an internal alternative of
  `auto`, selected only for at least two exact AP positions when its four bytes
  beat colex and zstd is not smaller (lines 278-305). The frozen plan's design
  is supportable if it describes the treatment as auto selecting progression,
  asserts that codec on every claimed AP row, and treats colex/zstd as forced
  diagnostic portfolios. It cannot describe all three arms as forced matched
  codecs without an interface change.
- The JSON `candidates` count is a count of discovered specifications, not
  necessarily costed or materialized candidates. It is incremented before
  `final_cost`; a mask/count intersection can produce an empty table and return
  `None` (lines 794-800). Evidence should use that label or separately count
  feasible/costed candidates.
- `discovery_ns` is sampled before the internal decoder check and archive write
  (lines 784-817). It includes model discovery, every `final_cost` computation,
  zstd compression performed during map selection, and construction of every
  strict incumbent. It excludes internal restoration and filesystem output.
  It is not a pure feature-discovery time.
- The source comment names host libzstd 1.5.5, but the binary neither queries
  nor records that version. The frozen build, linked/runtime zstd provenance,
  and binary hash must be bound in evidence because compressed control bytes
  can be implementation-version dependent.
- A wall-clock timeout and cgroup memory limit remain required for each encode,
  decode, and malformed case even after local bounds are corrected. The source
  has no cancellation/deadline checks inside model enumeration or BigUint work.

## Complete-cost audit

### Envelope and metadata

RXP1 has a fixed 32-byte header and a four-byte CRC. The structural header pays
for:

- version and raw/exception kind;
- original byte length;
- record width and the two sorted source symbols;
- record and exception counts;
- equality mask, count mode, and count parameter;
- position-map codec;
- position-map, dense payload-rank, and raw-exception byte lengths.

The model table is deterministically rebuilt from paid `(b, mask, count,
param)` metadata, so no hidden table bytes are needed. The raw route uses the
same 32-byte header with canonical zero metadata, stores all source bytes, and
pays the same CRC (lines 423-465).

`final_cost` returns exactly:

```text
32-byte header
+ 4-byte CRC
+ actual selected map bytes
+ ceil(log2(|table|^(records-exceptions))) / 8
+ ceil(record_width * exceptions / 8)
```

The main loop constructs a candidate only when this complete cost strictly
beats the current archive and rejects any constructed-length mismatch (lines
743-809). `build` serializes exactly those components and its winner is decoded
before being written (lines 466-518 and 813-817). Raw starts as the incumbent;
strict comparison preserves raw and earlier model order on ties.

This is exact physical byte selection among the generated, feasible candidate
specifications. It is not an exhaustive model search: the input-derived bank
uses up to ten masks, up to five count modes, truncates to 40 models at each of
the eleven widths 2 through 12, and skips widths that do not divide the source
(lines 655-741 and 789-811).

### Position maps

- **Colex:** positions are ranked as
  `sum choose(position[i], i + 1)`. The stored width is derived from
  `choose(records, exceptions)`. Decode requires the canonical byte length,
  zero high padding, rank below the cardinality, a zero terminal remainder, and
  strictly increasing reconstructed positions (lines 188-219 and 320-330).
- **Progression:** the four paid bytes are `start:u16le, step:u16le`; exception
  count is already in the header. Encoding requires at least two exceptions, a
  positive exact step, checked last-position arithmetic, and a last position
  inside the record count. Decoding repeats checked arithmetic and the same
  range requirements (lines 278-305 and 332-351). Empty and one-position AP
  maps are deliberately impossible.
- **Zstd gaps:** the uncompressed object is an exact little-endian `u16` gap
  vector. The first value is an absolute position; subsequent gaps must be
  positive. Encode checks order, record range, `u16` range, and decoded length.
  Decode requires one zstd frame consuming every map byte, exact decompressed
  length, positive later gaps, checked cumulative addition, and record range
  (lines 238-265 and 352-390). There is no hidden recompression or search in
  decode.

The installed authoritative zstd header documents that `ZSTD_decompress()` is
a single-pass API with no internally allocated window buffer; the caller's
destination capacity is a valid decompressed-size upper bound. RXP supplies an
exact `2 * exceptions <= 16,384` destination, requires the returned size to
equal it, and rejects concatenated or trailing frames by requiring
`ZSTD_findFrameCompressedSize == map.len()`. Thus the zstd output and
window-memory concern is resolved for this one-pass API. `ZSTD_compressBound`
cannot overflow or fail for RXP's at-most-16-KiB input, and the returned write
length is checked before truncation.

Auto compares actual map byte lengths. Its tie behavior is deterministic:
colex retains ties against zstd normally; for an admitted exact progression,
progression retains a four-byte tie against zstd after already proving that it
beats colex.

### Payload and exceptions

Every nonexception record is a digit in the sorted deterministic model table.
The mixed-radix rank is packed to the exact width of
`|table|^(records-exceptions)`. Decode checks rank range, extracts digits in
reverse record order, and requires a zero terminal rank (lines 492-498 and
603-651).

Each exception is stored as its full `b`-bit binary word. Decode validates byte
length and zero trailing padding, reverses exception order consistently with
the reverse record walk, and rejects an “exception” that is actually present
in the model table (lines 393-421 and 622-650). The original symbol alphabet is
fully reconstructed from the two paid bytes.

## Parser and allocation bounds

The Rust-side bounds are explicit and coherent:

- source input: at most 16,384 bytes via `Read::take(cap + 1)`;
- archive input: at most 30,000 bytes by the same mechanism;
- record width: 2 through 12, exact source divisibility, at most 8,192 records;
- model table: at most `2^12 = 4,096` `u16` entries;
- equality histogram: at most `2^11 = 2,048` entries;
- generated model specifications: at most `11 * 40 = 440`, plus raw;
- decompressed gap vector: at most 16,384 bytes;
- decoded source: at most 16,384 bytes;
- dense payload cardinality: at most 98,304 rank bits before byte rounding.

Decode verifies envelope length and CRC before interpreting model data, then
checks version/kind, exact body-length arithmetic, canonical raw metadata,
record arithmetic, sorted distinct symbols, mask range, count parameters,
nonempty table, canonical component lengths, rank range/padding, exception
padding/membership, and terminal state (lines 520-653). Component lengths are
`u16`, and their sum is checked against the already bounded archive.

These bounds prevent Rust output over-allocation and trailing/truncated body
acceptance. They do not resolve the combinadic CPU blocker above.

## Prepared harness review

The review also inspected `position-evidence/PLAN.md`, `fixtures.py`, and
`run.py` as prepared before execution.

### Blocking discrepancies

1. `run.py` imports the prior exception runner and redirects `p.RAW` to
   `position-evidence/raw`, but creates only the archive directory. The raw
   directory is absent at review time. Imported `p.call` opens its stderr,
   stdout, and time files directly, so the first call fails unless the runner
   creates `p.RAW` first.
2. The prepared runner does not require a scheduler lease environment variable.
   The prior runner's guard is inside its `if __name__ == '__main__'` body and
   does not execute on import. The new script starts work at module top level.
3. For the nine reused rows, `run.py` verifies only the input file SHA before
   copying previous candidate/reference receipts. The plan requires reuse only
   with identical input **and artifact** hashes. The earlier exception runner
   demonstrates the required pattern: locate each declared archive SHA in its
   artifact binding and rehash the retained file before copying the receipt.
4. The plan declares 30 seconds for native work and 120 seconds for references.
   Every new call currently uses imported `p.call`, whose timeout is fixed at
   120 seconds. The actual command timeout therefore disagrees with the frozen
   native budget.
5. The plan declares malformed AP step, start, count, length, IDs, rank, CRC,
   and compressed trailing-byte cases. The prepared variants cover step, start,
   codec ID, map length, CRC, truncation, and one intended zstd trailing case;
   they do not cover exception count or payload/map rank. The zstd trailing
   case also takes `rows[0]` without asserting that the forced-zstd archive is a
   structural archive whose stored codec is `zstd-gaps`. If that arm selects
   raw, the mutation exercises raw metadata rather than trailing zstd bytes.

### Evidence strengths and remaining binding work

- The independent Python oracle recomputes the table, exception positions,
  colex rank, dense payload rank, and exception bitstream from source bytes. Its
  zstd arm uses a separate `/bin/zstd` decode and compares the exact gap vector.
  Every archive also receives a fresh native decode and restored-source hash.
- The two irregular controls preserve each source's record multiset while
  applying a deterministic predeclared permutation. The encoder receives only
  the resulting byte path, not the generator labels or expected model.
- `artifact-binding.json` currently covers files below the outside-Git WORK
  directory only. A final binding must additionally seal the reviewed source,
  executed-source copy, binary, plan, runner, fixture generator, generated
  input registry, scheduler, results, malformed results, raw receipts, and any
  reused artifact manifest. This is expected pre-execution work, but the
  prepared binding alone is not complete provenance.
- Policy arms may legitimately select raw. Reports must derive AP or zstd
  claims from the oracle's stored `kind` and `position_codec`, rather than the
  requested policy name.

## Input policy and claim scope

The encoder reads only the caller-supplied path, derives a sorted two-symbol
alphabet from its bytes, and derives every model/position list from those bytes.
There is no filename, corpus identity, fixed dictionary, or pretrained asset in
the source. Inputs with any alphabet size other than two, empty inputs, or
lengths not divisible by a candidate width retain the complete paid raw
archive as applicable.

The source tests a bounded representation of exception-position regularity. A
win can be attributed to the paid model plus its selected position-map codec
relative to the declared controls. It does not establish a generic
shared-template mechanism, a production integration result, or new theory.

## Resolution addendum — final source and completed screen

The decision and blockers above are a historical review of source SHA-256
`6c62c4be0e861fbcf792f560059c31adb7a797034b55dc2e5d2d5c282c90a9f3`
and its then-prepared harness. They do not describe the subsequently frozen
source. A later read-only re-review covered
`record_position_templates.rs` at SHA-256
`bedd86e7cea40e8cf0ec7ba0780439d7d032ac991aab258ea4eedd2085eeb6e0`.
No build, test, codec, or benchmark command was run by the reviewer.

The final source resolved the source blockers:

- combinadic unranking now performs one bounded downward recurrence scan over
  at most 8,192 record positions instead of repeated binary searches that
  recomputed large binomial coefficients;
- forced zstd-gap selection returns before colex rank construction, so that arm
  does not perform the unused combinadic map work;
- progression is an explicit source policy, while the frozen executed screen
  uses automatic selection plus forced colex and forced zstd-gap arms.

The frozen runner also resolved the prepared-harness blockers. It creates its
raw-log directory, requires the scheduler lease environment, applies the
declared 30-second native and 120-second CIX child limits, rehashes retained
archives before importing their receipts, performs a fresh native decode, and
checks table, exception positions, position-map representation, payload rank,
and exception bits with an independent Python oracle. Its malformed set covers
truncation, CRC, progression step and range, codec ID, map length, exception
count, rank, and trailing compressed-map bytes.

Static review found the final complete-cost calculation consistent with the
wire format. It charges the 32-byte header, four-byte CRC, actual selected map,
exact mixed-radix payload width, and exception bits. The progression inverse,
colex range and padding checks, zstd exact-one-frame and exact-output checks,
model reconstruction, terminal rank, exception membership, source bound, and
archive bound are coherent. The final source and prepared screen were therefore
approved for the frozen experiment.

The retained results now contain 11 rows, 33 newly encoded candidate archives,
and 16 new reference archives for the two added irregular controls: 49 new
archives in total, all marked verified after fresh restoration. The candidate
archives store 17 colex, 10 zstd-gap, three progression, and three raw
selections. The nine declared malformed invocations have nonzero exit statuses.
These counts are a read-back of `results.json` and `malformed.json`; the final
report and artifact manifest remain authoritative for execution provenance and
resource receipts.

Two scope qualifications remain:

- progression evidence comes from progression selected by the automatic arm;
  it is not a forced matched progression portfolio in the executed runner;
- policy names do not prove the stored codec because a portfolio may retain raw
  or another winning model. Claims must use the archive oracle's stored kind,
  model, and `position_codec` fields.

Within those limits, the earlier blocked decision is resolved for source
`bedd86e…`; it remains preserved above only as the audit history of `6c62c4…`.
