# Native retained-port coverage and historical dispatch contract

**Status: scoped source and interface evidence refreshed 2026-10-05.** This
inventory records the current 41-module Python reference map, current native
source, and only the bounded evidence named below. It preserves failed and
interrupted job scopes: no passing substep upgrades a whole job, and no scoped
CLI result is a release or benchmark claim.

Native BEST portfolio parity is restored at the library selection boundary.
`FullEngine` dispatch contains CIXY feedback, CIXZ interval, CIXB\x1f SGCC1
count, CIXB\x20 SGCC2 conditional, and CIXI\x01 JPEG-2000/JPEG-LS spatial
paths. The ordinary CLI now calls automatic full-engine selection for a narrow,
explicitly bounded input class: an unconstrained named regular file of at most
128 MiB, with the selected memory/output reservations available. It writes the
selected complete archive and ordinary CLI decode dispatches its full archive.

That is **scoped CLI reachability**, not a blanket per-family CLI qualification.
The whole-engine path declines stdin, stream/flush, history/reset,
independent-block, explicit format/route/backend/block/external/portfolio
controls, non-regular files, oversized files, and insufficient budget. Those
uses retain their existing bounded streaming or legacy paths. Explicit
whole-engine dimensions, stdin and large-stream specialist admission remain
open. Individual retained modules below therefore keep their library-focused
status unless their own ordinary CLI contract has been qualified.

## Wire boundary

`CIXB1` is an ASCII generic portfolio container. It is separate from binary
historical specialist prefixes `CIXB\x03`, `CIXB\x0b`, `CIXB\x0c`,
`CIXB\x13`, `CIXB\x1d`, `CIXB\x1e`, `CIXB\x1f`, and `CIXB\x20`.
Generic `CIXG1`, `CIXG2`, `CIXM5`, `CIXM6`, and `CIXZ1` are likewise separate
from `CIXG\x01`, `CIXD\x01`, and other specialist envelopes. There is no
`CIXF1` wire magic: the compatibility option maps to the M6 format and its M6
footer. Dispatch uses exact bytes; it must never infer a family from a printable
prefix.

The complete 41-module and wire map is
[native-coverage.json](native-coverage.json). Status terms mean:

- **library-only**: reversible native functions exist without a route claim.
- **library-tested-unwired**: bounded source-bound tests cover the library
  route. A retained candidate can be considered by scoped automatic CLI
  selection where admitted, but it has no per-family ordinary CLI qualification.
- **partial-unwired**: source has part of a route but lacks an edge.
- **internal dependency / inactive history**: a helper sits inside a retained
  route or is not reachable from a supported production wire.
- **absent**: no native equivalent was found.

## Current scoped coverage

| Reference family | Native evidence | Status | Boundary still open |
|---|---|---|---|
| Native BEST portfolio | Library selection, with scoped ordinary CLI automatic admission for eligible whole inputs | scoped CLI reachable | Per-profile/per-candidate CLI qualification and broader resource qualification. |
| FullEngine retained families | Catalogue, providers, transforms, exact frame dispatcher, and selected complete archive output through eligible CLI inputs | scoped CLI reachable | Per-family paid selection and ordinary CLI qualification. |
| Grid feedback / interval | SGFB1/CIXY\x01 and SGBI1/CIXZ\x01 transforms and dispatch | library-tested; scoped candidate admission only | Normal per-family CLI selection/qualification. |
| Count / conditional grids | SGCC1/CIXB\x1f and SGCC2/CIXB\x20 transforms and dispatch | library-tested; scoped candidate admission only | Normal per-family CLI selection/qualification. |
| Spatial JPEG-LS / JPEG-2000 | Provider bridge, CIXI1 representation-2/3 framing, dispatch and appended catalogue alternatives | library-tested; scoped candidate admission only | Per-family CLI and broader release/provider qualification. |
| Dictionary C API | Retained-capacity/lifecycle contract plus relocated shared/static consumers | focused-tested SDK surface | ABI/provider loading and platform qualification. |
| Explicit standard streams | Nine one-shot formats via generic CLI and C format API | focused-tested explicit operation | Not an automatic portfolio/full-engine route. |

`ECRP1` and `ECBR2` are not missing production frames: `ECRP1` is the
relocated-pointer helper below supported `ECRD1`/`CIXB\x0b`; `ECBR2` belongs
only to inactive SectionPointers mode 6.

## Scoped evidence

Source reachability is bounded in
[`cli_full_engine.rs`](../../../rust/cix-native/src/cli_full_engine.rs):
`whole_encode_ineligibility` rejects the controls listed above;
`whole_input_ineligibility` requires a regular input file no larger than 128
MiB and enough baseline memory; `encode_whole` runs selection and writes its
complete chosen archive. Its decode path treats a recognized full frame as a
full-frame buffered decode. This source observation says nothing about every
candidate being selected for every input.

The older `cli-bindings-v2` through `cli-bindings-v6` runs ended nonzero and
remain negative or incomplete evidence. `cli-bindings-v8` completed with exit
code 0, including installed C/C++ SDK relocation, Python/Go binding checks, and
relocated runtime stream-command checks. Its scope is recorded in
[`jobs/cli-bindings-v8/spec.json`](jobs/cli-bindings-v8/spec.json) and its
individual results in
[`jobs/cli-bindings-v8/consumer-results.json`](jobs/cli-bindings-v8/consumer-results.json).
It does not exercise every retained specialist family through ordinary CLI
automatic selection.

`interfaces-v7` completed its all-target build and passed 29 focused tests. Its
later SDK stage was interrupted at the temporary-space cap and is not credited.
The same-source/binary `interfaces-v8` reran SDK-only relocation and installed
C/C++ consumers successfully. These are bounded interface facts, not a whole
release or platform qualification.

`dictionary-grid-v3` passed after the zero-rank helper correction and
fixture-bound repair. It establishes SGCC1 raw parity across five modes, SGCC2
raw parity across twelve context/coding combinations, 17 Brotli-backed archive
dispatch cases, five Rust C-dictionary retained-capacity/lifecycle checks, and
relocated shared/static installed dictionary consumers.
`installed-discovery-v1` passed four focused `full_engine::installed`
filesystem-discovery tests: six exact names present/missing, explicit multiarch
directory, invalid paths, and no temporary-root creation. It does not qualify
ABI/provider loading or platforms.

`spatial-counts-v2` supplies passing scoped evidence for spatial provider (3),
spatial frames (5), frozen Python JPEG-LS/JP2/raw-J2K cross-decoding,
historical spatial dispatch, and both native spatial candidates after the JP2
seek correction. Its recorded grid failure remains a failed job component.
`spatial-counts-v1` likewise retains passing installed C/C++/stream/formats SDK
substeps, while its grid and encode checks failed. Neither job is credited as a
complete checkpoint.

The generic CLI’s explicit `--output-format` and `--input-format` contracts
cover gzip, zlib, raw DEFLATE, bzip2, XZ, Zstd, Brotli, LZ4 frame and Snappy
framed as one-shot complete-buffer operations with a 128 MiB ceiling. This does
not imply standard-format streaming or automatic portfolio admission.

## Work still required

1. Qualify each retained family that is expected to win or decode through the
   ordinary CLI automatic path, including paid exact framing, malformed/limit
   cases and candidate-admission diagnostics. Do not infer this from the scoped
   selector or smoke evidence.
2. Extend or explicitly decline whole-engine specialist admission for stdin,
   inputs larger than 128 MiB, and explicit dimensions/controls. The present
   bounded streaming and legacy paths are not evidence of full-engine coverage.
3. Qualify installed ABI/provider loading and platforms beyond the completed
   filesystem-discovery receipt.
4. Complete release adapters, packages, cross-platform/SquashFS, quality and
   final release checks before making a public claim.
5. Account for the historical LSTM/prediction route: no native implementation
   or frame decoder was found, and the recorded `-12L` path remains outside the
   stated 12 GiB bound.

A completed route still requires named admission, paid exact framing, bounded
native inverse, checksum/original-byte verification, malformed/limit cases,
resource accounting, and evidence that it uses no Python process, PATH lookup,
or undeclared backend.
