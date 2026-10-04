# Native retained-port coverage and historical dispatch contract

**Status: source and bounded-interface inventory refreshed 2026-10-05.** This
is not full-route, portfolio, or release qualification. It records the current
41-module Python reference tree, the native source tree, and the constrained
catalogue-v4 and interfaces-v7/v8 evidence cited below. The stopped benchmark
remains stopped.

The native tree has a compiled content-only catalogue, `FullEngine` provider and
frame dispatch, a CIXH1 carrier, region discovery, C stream/C format APIs,
registered selection/mixed-selection/grid-feedback/spatial-provider modules,
and explicit standard-format CLI handling. The ordinary CLI and generic
portfolio selector still do **not** call the full-engine catalogue or automatic
specialist selector. Current `selection.rs::NativeExecutor` uses the fixed 64 KiB
`core::encode_buffer`/CIXG1 path; it is not yet parity with the retained
historical native BEST portfolio (CIXG2 whole, CIXM6 and external complete archives). A route can therefore be library-tested but unwired,
without being a normal CIX command-line route.

## Wire boundary

`CIXB1` is an ASCII generic portfolio container. It is separate from binary
historical specialist prefixes `CIXB\x03`, `CIXB\x0b`, `CIXB\x0c`,
`CIXB\x13`, `CIXB\x1d`, `CIXB\x1e`, `CIXB\x1f`, and `CIXB\x20`.
Generic `CIXG1`, `CIXG2`, `CIXM5`, `CIXM6`, `CIXF1`, and `CIXZ1` are likewise
separate from historical `CIXG\x01`, `CIXD\x01`, and specialist envelopes.
Dispatch must use exact bytes, never infer a family from a printable prefix.

The machine-readable 41-module map is [native-coverage.json](native-coverage.json).
Status means:

- **library-only**: reversible native functions exist, with no route claim.
- **library-tested-unwired**: bounded source-bound tests pass but normal CLI
  selection/encoding does not reach the route.
- **partial-unwired**: source has part of the route but lacks a transform,
  provider, envelope, or dispatch edge.
- **internal dependency / inactive history**: a helper belongs inside a
  supported route or is not reachable from a supported production wire.
- **absent**: no equivalent native implementation was found.

## Current coverage

| Reference family | Current native evidence | Status | Boundary still open |
|---|---|---|---|
| Backends, catalogue, records, structured/address, bounded/grouped grids | `catalogue.rs`, `dispatch.rs`, providers and retained transform modules | library-tested-unwired | Ordinary CLI candidate evaluation, winner selection and FullEngine binding. |
| Regions / heterogeneous carrier | `mixed.rs`, `regions.rs`, recursive CIXH1 decode, `mixed_selection.rs` | library-tested-unwired | Automatic region-to-recipe encoding and CLI binding. |
| Grid feedback | `grid_context.rs`: all six SGFB1 mode/model raw transforms and CIXY\x01 envelope | library-tested-unwired | `FullEngine` does not dispatch CIXY; no CLI selection. |
| Historical context/conditional/interval grids | `CIXB\x1f`, `CIXB\x20`, and CIXZ1 routes remain separate | absent / partial-unwired | Exact legacy frame dispatch and any missing transforms. |
| Spatial image providers | `spatial_provider.rs` bridges CharLS 2.4.2 and OpenJPEG 2.5.0; JXL remains distinct | library-tested-unwired | Historical CIXI mode-2/3 envelopes, FullEngine dispatch, reference cross-decoding and CLI selection. |
| Volume and strided values | `volume_lifting.rs`, `jxl_provider.rs`, `strided_values.rs` | library-tested-unwired | Catalogue recipe where absent and normal CLI encoding. |
| Explicit standard streams | `standard_formats.rs`, `c_format_api.rs`, generic CLI | focused-tested explicit operation | Not an automatic portfolio/full-engine selection route. |
| C buffer/stream/C++ SDK | `c_api.rs`, `c_stream_api.rs`, `c_format_api.rs` | focused-tested SDK surface | Broader SDK/release/platform qualification. |

`ECRP1` and `ECBR2` are not missing production frames: `ECRP1` is the
relocated-pointer helper beneath supported `ECRD1`/`CIXB\x0b`, and `ECBR2`
belongs only to inactive SectionPointers mode 6. The pointer-delta mode-5
fixture is narrow raw parity evidence for the supported `ECRD1` path.

## Interfaces checkpoint

`interfaces-v7` bound a frozen source snapshot, completed its all-target build,
and passed 29 focused tests: selection (5), mixed selection (4), spatial
provider (3), grid context (2), backend provider (3), address reference (1),
and C/dictionary/standard-format contracts (11). This covers all six SGFB1
raw feedback identities plus CIXY\x01 envelope identity, and 14 generated
CharLS/OpenJPEG provider round trips. It does **not** establish image-envelope
or FullEngine dispatch compatibility.

The v7 SDK stage was interrupted after temporary use reached 4,007,783,035
bytes. It is not credited. The narrow `interfaces-v8` rerun used the same
source and binary prerequisites for SDK work only: shared/static installation
and relocation, then installed C buffer, C stream, C standard-gzip and C++
consumers all passed. That is bounded SDK evidence, not a complete release,
ordinary CLI, or platform qualification.

The generic CLI’s explicit `--output-format` and `--input-format` contracts
cover nine one-shot byte-stream formats: gzip, zlib, raw DEFLATE, bzip2, XZ,
Zstd, Brotli, LZ4 frame and Snappy framed. These use complete buffers with a
128 MiB ceiling; they do not imply streaming standard-format support or
portfolio admission.

## Required work before engine completion

1. Restore a pure-library complete native portfolio before CLI binding: the
   current selector is fixed 64 KiB CIXG1, not historical native BEST CIXG2
   whole/CIXM6/external complete-archive parity.
2. Bind full-engine catalogue, bounded automatic selection and exact dispatch
   into ordinary CLI operation with resource accounting.
3. Bind automatic mixed selection and paid CIXH1 comparison into that route.
4. Complete and qualify remaining legacy CIXB context/conditional, CIXZ
   interval and image-envelope decoder/dispatch edges.
5. Qualify image envelope/reference compatibility beyond the current provider
   bridge tests.
6. Complete full quality, package, cross-platform, SquashFS and final release
   checks before any public release claim.

A completed native route needs admission, a named candidate/provider, a paid
exact frame ID, a top-level native decoder, bounded inverse, checksum/original
byte verification, malformed/limit cases, resource accounting and proof that
no Python process, PATH lookup or undeclared backend is involved.
