# Source backlog handoff for consolidated RC acceptance

Root-owned handoff, 2026-10-04. This is input to the coordinator-owned
`../2026-10-04-rc-reconciliation/REQUIREMENTS.md` and `requirements.json`, not a
replacement scope decision. It incorporates bounded read-only follow-ups from
inventory, distribution, performance, quality and Squash integration agents.
Their older findings were reconciled against the retained proof below; absence
of final new-RC proof must not erase completed predecessor checks.

## Controlling state and ownership

- Benchmark stopped by user: five verified cells, one interrupted/unqualified
  Mozilla BEST encode, 30 unstarted. Controller and all children absent, unit
  inactive/dead and cgroup absent. Both continuation automations paused. Receipt:
  `qualification/silesia-confirmation-v1/stop-20261004-user/stop.json`.
- Root task `01a0f927-3e23-7cb1-bdc3-cb7d08783ade` owns source integration, shared
  heavy scheduling, commits and private pushes. Task
  `01a103be-69f6-76b1-aa46-b1c65331c533` owns cross-session requirements ledger;
  task `01a10495-8aa1-7893-81eb-3eb28ebe3f51` owns SDK/integration planning input.
  No overlapping implementation assignments have been started from these handoffs.
- Verified original user requirement: encoder/decoder/framing/checksums/selectors
  and supported routes in Rust; finished binaries run without Python or a Python
  subprocess. Original task `01a0f409-8b61-7eb3-9be6-0b7bd3817f94`.
  One compiled CIX executable with native codec libraries is accepted; embedded
  CPython was only a withdrawn proposal. Python remains reference/test tooling
  or an optional consumer binding, never a required shipping interpreter.
- Preserve useful specialists and historical archives; no upstream/vendor source
  edits, no hidden external programs, no new dataset or benchmark until the full
  agreed RC gate. Maximum useful parallelism stays within four physical cores,
  decimal 12 GB RAM, decimal 4 GB temporary and no swap.

## Retained predecessor proof

`QUALIFICATION-PROGRESS.md` and the stopped immutable receipts establish:

- Fresh optimized native build: formatting, Clippy warnings denied, 126 optimized
  tests (115 library, four CLI, seven streaming); four stripped artifact hashes
  reproduce the previously frozen native build.
- 37 focused runtime/harness tests; 15 actual specialist archive/independent-decode
  cases with post-cleanup byte parity; 55 helper parity/cross-decoder cases;
  16 image/volume cases, including low-bit images; final four harness fixtures.
- Read-only historical-family admission census for all twelve corpus members;
  ordinary staged three-mode smoke and source/stage parity.
- Fresh Sonar run-5: zero Rust and Python issues in its actual scanned scope.
  C++ was not scanned. The separately prepared community CXX/Cppcheck instrument
  covers 1,346 first-party/vendor files, with two CUDA headers excluded, but has
  not executed. It is not commercial CFamily.
- Five current CLI encode/decode cells passed exact restoration before stop.
  These are not full corpus qualification, new-RC timings or portability proof.

The native distribution candidate and integrated source snapshot both exist.
The latter is `/home/user/src/cix-integrated-source-candidate` with `native/`,
`runtime/`, `vendor/paq/` and notices. The installed predecessor is
`/home/user/src/cix-integrated-candidate`. Neither is a qualified no-Python,
single-executable full-engine RC. The development native tree, exported native
tree and immutable snapshot must be reconciled to one authoritative editing/build
source before ports; do not assume identical names imply identical revisions.

Root read-back now confirms all 40 files checked (`src/` plus Cargo/build inputs)
match between the native export and frozen snapshot.
The old development `rust/cix-native` differs in 13 shared files, lacks `src/cli.rs`
and has four extra research/oracle files. This is a concrete source-reconciliation
obligation; begin from the qualified snapshot/export bytes, not an assumed stale
development equivalent. The check covered source/Cargo/build inputs only, not
every vendor/doc/test file.

## Native implementation groups and dependencies

| Group | Still-Python reference | Required native coverage / reuse limits |
| --- | --- | --- |
| Orchestration | `engine.py`, `model.py`, `cli.py`, `backends.py` | Candidate catalogue, input-only admission, whole-archive selection/ties, resources, receipts, CIXP, backend routing and historical decode; reuse native CLI/resources/selection only with behavior proof. |
| Mixed content | `heterogeneous.py`, `regions.py` | CIXH1 framing, paid boundaries/IDs/checksums, unknown fallback, region/nested selection, decode and aggregate budgeting. Native CIXZ1/CIXG streaming does not establish CIXH1 parity. |
| Registry | `specialized.py`, `image_grid.py`, legacy dispatch modules | Every eligible family and binary/ASCII magic; distinguish binary CIXB variants from ASCII CIXB1. No filename/hash/corpus selection. |
| Chemical/database | `sdf_geometry`, `sdf_hydrogen`, `mysql_record_constraints`, `mysql_remaining_counts`, `mysql_fixed_columns`, `multinomial` | Exact SDF/MyISAM grammars, side information/ranks/counts, framing and inverse validation. Rust rank/combinatorics are primitives, not demonstrated schema parity. |
| Grid/image/volume | `record_float_grid`, `grid_context`, `grid_feedback`, `grid_interval`, `grid_conditional`, `grid_backend`, `grid_grouped`, spatial/volume/multiscale codecs | WCSTools and validated DICOM layouts, grouped prediction, JXL native API, sample dtype/size limits, all historical frames. Preserve shared-current-payload optimization. |
| Executables | ECOFF constraints/fields/GOT/relocation/pointers/calls/sections/symbol/pdata modules, `ordered_subset`, `executable`, `framing` | Input-derived ELF/ECOFF/TAR-carried structure, reversible chains, filtered/joint-discount semantics and exact historical binary frames. Generic external CIXB1 is not a substitute. |

The maintained reference checker inventories 41 production modules. Existing
Rust generic PPM/LZ/BWT/context/rank/transform modules remain reusable, with their
actual proven wire contracts. Preserve closed composition/predictive-mixture
negative evidence; porting is not authorization to reopen those research branches.

Native codec bridges must cover PAQ v215, v216, joint-discount and store-state,
plus required JXL/Brotli/library dependencies. Use CIX-owned build/ABI adapters
around unchanged vendor snapshots, isolate colliding symbols/state, preserve
floating-point/SIMD behavior and codec attribution. Same-CIX workers are permitted
for full-engine isolation; a process-free native SDK must not silently launch them.

## Concrete CLI, resource and parallelism gaps

The maintained Python CLI lacks native `-t`, `-l`, `--format`, `--route`,
`--backend`, `--block-size`, `--history`, `--independent-blocks`, `--stream`,
`--flush-interval`, `--parallelism`, `--profile`, `--portfolio` and `--external`.
Its thread range is 1–4 while native exposes a broader range. Restore or explicitly
reconcile original CLI compatibility in the ledger; do not silently reduce it.
New standard `--output-format` must remain distinct from CIX `--format`.

Whole-input specialists currently stop at 128 MiB; stdin/oversized regular files
delegate to native with no specialist selection. Large non-native archives still
face bounded input reading; CIXH reconstructs a whole bytearray. True streaming,
partial I/O/backpressure, flush/finish/error behavior, historical decode, output
bounds, input preservation and atomic destination semantics need an explicit
cross-interface matrix. A delegation notice is not a full selection report.

Actual old parallelism: one corpus phase at a time; native candidate reserves the
requested four workers, raw runs alone, and independent candidates co-run only
when declared memory/thread/temp reservations permit. Two PAQ trials were active
at stop. PAQ decoding is sequential across adaptive state; four allowed cores do
not make that path four-threaded. Heterogeneous scanning, region competition,
nested search and ordered decode are serial. First-child polling can add bounded
idle delay. Python candidate processes avoid a shared GIL across candidates, but
that does not parallelize loops within each candidate.

The new design must account for candidate versus region/chunk/file concurrency,
tail utilization, host-owned SDK pools and aggregate costs. Do not replace safe
reservations with optimistic measured peaks, split long contexts, change finite
deadline order/ties or drop expensive winners without explicit evidence/policy.
No speedup is established by these source observations.

Current runtime isolation uses fork, procfs, RLIMIT and process groups. It is
Linux-specific; global temporary/RAM enforcement partly depends on the research
scheduler. The distributed CLI must have a real resource/cancellation contract.
The native embedding API must avoid global handlers, process exits/resource-limit
writes or unsolicited output. Uniform errors/reporting, timeout cleanup, nested
resources and output limits require tests. Environment cleanup remains CIX-owned
work (`ENVIRONMENT-TRIAGE.md`); the examined frozen run had no identified model
environment contamination. Do not modify PAQ sources to repair the adapter.

## SDK, adapter and platform scope to classify explicitly

The SDK planner supplied the full phased programme: reusable library-first
contexts and buffer/stream/callback/chunk APIs; checked bounds and typed errors;
capabilities/target-decoder profiles; C/Rust/C++ artifacts and build metadata;
versioned full-engine job protocol; real standard-format outputs/dictionaries;
tar/libarchive/QuixDB Squash/7-Zip; HDF5/netCDF/Zarr/Blosc2/RocksDB/WiredTiger/Hadoop;
language bindings and Linux/macOS/Windows architectures; gRPC/HTTP/GIO/GStreamer;
object storage/backup examples; genuine native SquashFS tools/userspace decoder/
kernel-VM qualification; separate other-filesystem/format extension proposals.

Every item needs current-RC, external-dependent or explicit later classification,
owner, reason, dependencies and user-visible scope. This handoff makes no silent
deferral. Existing `cix_squash_splice` is a narrow whole-stream callback ABI with
fixed defaults, not the proposed complete native SDK. It has retained ABI proof.
QuixDB Squash 0.8 plugin loader qualification is missing because the SDK/runtime
is absent; the local 0.7 source cache lacks its generated header. Standard Zstd
SquashFS carrying opaque CIX files passed a transport check, not a native CIX
filesystem check. Native tools/library/kernel work and a non-conflicting codec ID
remain open; no stock compatibility or random access may be claimed from transport.

## Quality, build and distribution work

The CXX runner `tools/sonar-cxx/repair.py` still requires 36 verified cells at both
parent and worker entry. Replace this obsolete prerequisite only with a narrowly
validated stop contract tied to this exact plan/user-stop receipt, zero active
benchmark processes and exclusive shared lease. Do not delete safety checks or
forge verification. Preserve prepared-v1 and failed attempts; scan its immutable
source snapshot separately from the later final RC scope. Validate real analyzer
boot/probe, indexed files and issues; repair only CIX-owned findings. Vendor
findings remain visible, source unchanged. Server/plugin/Squash SDK limitations
are unresolved until actual execution.

After implementation: fresh formatting/Clippy/Sonar for actual final source,
proven dead-code disposition with historic decoder retention, cross-decoder and
deterministic byte parity, corrupt/truncated/overlarge inputs, cancellation and
concurrent-context isolation, sanitizer/fuzz/resource boundaries, library loader
traces, and independent installed-consumer tests. Earlier fixtures are reusable
regression evidence, not automatic final acceptance.

Native package/man/install recipes exist, but integrated root source build,
dependency lock/provenance, install manifest, licenses, Debian/RPM payloads and
all native platform builds must be completed for the actual chosen RC. Earlier
macOS/Windows/Homebrew materials are templates, not qualification. Root snapshot
notices do not by themselves prove complete install-time attribution. Export only
required source/build/headers/docs/licenses; exclude research, corpus/results,
archives, benchmark controllers, venvs and generated caches. New README/man pages
must describe the shipping interface and real limitations. Publication/Sites and
new dataset benchmarks remain gated by the consolidated source/RC decision.

Read-only host audit is `../2026-10-04-host-performance-audit.md`: performance
governors and turbo already enabled, with sampled thermal throttling/dynamic power
policy and nonisolated background work. Later Mozilla samples do not quantify
earlier Dickens decode losses. Cooling/policy review is separate from source
optimization; no blind power increase, firmware write or old-result correction.
