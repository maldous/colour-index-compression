# CIX cross-session requirements and release gate

**Benchmark status: STOPPED. New release-candidate status: NOT READY.**

This reconciles the current user instructions with delivered Rust migration/streaming/effort prompts, the CIX Optimisation source and release backlog, retained research evidence, and the SDK integration programme. The implementation owner has stopped the controller and descendants; systemd reported inactive/dead, MainPID 0 and no remaining cgroup. Both benchmark automations are paused. Preserve **5 verified cells, 1 interrupted/unqualified Mozilla BEST cell and 30 unstarted cells**. See the [stop receipt](../2026-10-04-automatic-specialised-models/qualification/silesia-confirmation-v1/stop-20261004-user/stop.json).

The current user direction supersedes every earlier “finish the 36 cells before fixing code” instruction. CIX-owned implementation and focused correctness/hygiene checks may proceed; no replacement benchmark may start while this gate is open. No product source was changed by this reconciliation.

## Corrections recovered from previous sessions

- The original delivered Rust user prompt says: **“The finished binaries must run without Python or a Python subprocess.”** One executable with codec libraries does not waive this. The provisional embedded-CPython shortcut is withdrawn. Python may remain reference/test tooling or an optional binding used by Python applications, not a required standalone CIX runtime. Retain successful specialist coverage through native implementation and codec libraries.
- The existing integrated launcher lacks several original CLI/expert controls. Its stdin / over-128-MiB native-only delegation and whole-output decoding do not prove full-engine streaming parity. These remain visible product gaps, not optional polish.
- The prior serial benchmark harness and a four-thread setting did not demonstrate maximum useful parallelism. Two PAQ candidates were running concurrently when stopped, but serial independent decoding left an opportunity for other admitted work. Some idle capacity is unavoidable under memory/dependency constraints; record the reason rather than claiming blanket utilization.
- Native SDK, full engine, QuixDB Squash, opaque SquashFS transport and native SquashFS are different deliverables. A callback smoke test or storing a .cix file inside Zstd SquashFS cannot satisfy native plugin/filesystem support.
- Previous native tests/format/Clippy and scoped Rust/Python Sonar success remain valid predecessor evidence. They do not qualify new source. Prepared CXX tooling has not yet completed a C++ scan.

## Scope and ownership

**All practical source deliverables in the agreed phased programme are retained for the next complete RC.** Phases determine implementation order, not permission to omit features before benchmarks. External registry/upstream/platform dependencies are listed explicitly; they are not automatic waivers. No new required-source deferral is introduced. Closed-negative research remains closed, and unproven ideas remain honestly labelled rather than being confused with missing required features. Publication and other datasets retain their separate hold.

- **Implementation, integration, scheduling and private checkpoints:** CIX Optimisation, thread `01a0f927-3e23-7cb1-bdc3-cb7d08783ade`. It assigns bounded file ownership to its existing workers and is the sole heavy-work scheduler.
- **Cross-session requirements and acceptance:** this coordinating thread, `01a103be-69f6-76b1-aa46-b1c65331c533`; owns this directory.
- **SDK/adapter/filesystem contract review:** planning thread `01a10495-8aa1-7893-81eb-3eb28ebe3f51`; planning does not itself claim implementation.

Heavy work continues to share **four physical cores, decimal 12 GB RAM, decimal 4 GB temporary storage and no swap** until explicitly changed. Use maximum useful concurrency within those totals. Past 20-core/four-by-four proposals are not silently reinstated. Preserve long model contexts, canonical priority, exactness and compression quality; do not split a sequential model just to fill cores.

## Requirement register

The [machine-readable register](requirements.json) contains source provenance, ownership, status, acceptance criteria and an empty evidence field for every new-RC requirement. “Open” means not accepted against the rewritten RC, even where predecessor implementation exists. Update evidence and status per item; never bulk-mark completion from old tests.

| ID | Requirement | Scope | Required result |
| --- | --- | --- | --- |
| RC01 | Native executable and full-engine parity | Required RC | One compiled CIX executable; no required Python interpreter, embedded CPython, shell launcher, separate native-CIX/PAQ program or hidden extraction. Use native codec libraries and, where isolation is needed, the same CIX executable. Optional Python bindings call native code. |
| RC02 | Reusable library-first core | Required RC | Extract the engine from CLI main; CLI, SDK and adapters share native codec/container/selection/resource code rather than embedding CLI side effects. |
| RC03 | Generic automatic specialist selection | Required RC | Accept arbitrary input bytes and discover standard formats/data structure without corpus names, hashes, known contents, benchmark offsets/lengths or saved streams. Supported format knowledge is allowed. |
| RC04 | Arbitrary heterogeneous input | Required RC | Support varied structured/unstructured and known/unknown combinations, late/nonzero/interleaved/nested supported regions; text–numeric–text is only an example. Preserve unknown bytes. |
| RC05 | Historical model and decoder coverage | Required RC | Map all 12 portfolio26 winners, current useful generic routes and known-better references to actual native admission and decoders. Keep PAQ variants, image/JXL, molecular, numeric/grid, database and executable families where feasible. |
| RC06 | FAST / DEFAULT / BEST semantics | Required RC | FAST limits latency, DEFAULT balances cost, BEST minimizes complete valid bytes over its disclosed admitted search. DEFAULT means normal invocation. Search objective is separate from format or one fixed preset. |
| RC07 | Selection dimensions and overrides | Required RC | Audit routes × backends × transforms × parameters × boundaries × history × containers. Explicit expert options constrain only their chosen dimensions; no override disables unrelated automatic optimization. |
| RC08 | Paid representation and index packing | Required RC | Charge every header, dictionary, boundary, model ID, constraint, reset, index and integrity field. Preserve exact combinatorial arithmetic and exploit applicable higher-dimensional packing without forcing CIX rank coding where another coder wins. |
| RC09 | Genuine bounded streaming | Required RC | Non-seekable/unknown-length input read once with bounded blocks/history/queues, no whole-input spool; output before EOF; decode incrementally with backpressure. |
| RC10 | Streaming and full-engine coverage contracts | Required RC | Preserve supported history across flushes; declare whole-input-only models and capability/size limits. Remove silent specialist loss through current stdin/>128 MiB delegation; report any inherent limitation explicitly. |
| RC11 | Complete conventional CLI | Required RC | Preserve cix/uncix/cixcat aliases as the same compiled implementation, -d/-c/-k/-f/-t/-l, levels, memory/workers, - and multi-file I/O, help/version, expert/stream controls and useful diagnostics. |
| RC12 | Safe file and interruption semantics | Required RC | Preserve input by default, refuse unintended overwrite, temporary output plus atomic replacement, clean interruption/corrupt-input behavior and path handling. |
| RC13 | Maximum useful internal parallelism | Required RC | Use global resource-aware scheduling across independent candidates, independent regions/blocks and work stages, including tail utilization. Preserve dependent model history and quality. |
| RC14 | Concurrent benchmark scheduling design | Required RC | Replace unconditional one-file/phase serial scheduling with bounded admission across independent cells where resources permit. Reserve actual declared requirements, not an automatic four-core reservation for every job. |
| RC15 | Portable product resource controls | Required RC | Standalone product enforces total memory, output, temporary storage, queue and worker limits without relying on research WaveScheduler. Explicit cancellation/deadlines and backend environment allowlisting. |
| RC16 | Performance carry-forward | Required RC | Preserve exact rank/cardinality reuse, immutable fixedmix tables, borrowed PPM lookup, bounded readers, ordered backpressure, exact per-encode cache, T1 histogram avoidance and append-only pruning proof. |
| RC17 | Hardware execution policy | Required RC | Document sustainable CPU/cooling/power policy and isolate unrelated work where practical. Resolve intermittent thermal throttling and dynamic limits sufficiently for truthful qualification; no blind power-limit increase or automatic BIOS flash. |
| RC18 | Historical wire compatibility | Required RC | Retain all supported native and legacy frame decoders, binary/ASCII magic distinctions, exact joint-discount dispatch and installed dependency requirements. |
| RC19 | No hidden runtime inputs | Required RC | Archive plus documented installed runtime must suffice. No source files, corpus caches, result certificates, network fetches, pretrained assets or undeclared dictionaries required. |
| RC20 | Stable SDK buffer/context ABI | Required RC | Stable Rust/C APIs: checked bounds, buffer compression/decompression, opaque reusable contexts, versioned/sized options, typed errors, explicit ownership and limits. |
| RC21 | SDK incremental I/O and chunks | Required RC | Process/flush/finish/reset, consumed/produced counts, needs-input/output/finished statuses, callbacks, Rust Read/Write and independent chunks with compressed/stored outcomes. |
| RC22 | Native versus full-engine interfaces | Required RC | Expose both capabilities explicitly. Native SDK is process-free and host-scheduled (one worker default); full engine exposes complete eligible specialist coverage and explicit same-CIX worker isolation. |
| RC23 | Full-engine job protocol | Required RC | Versioned same-executable SDK/job mode with capabilities, structured request/result/error records, separate binary transport, progress/cancel and complete coverage reporting. |
| RC24 | SDK development artifacts | Required RC | Public header, Rust docs, C++ RAII, static/shared libraries, pkg-config, CMake package metadata and small installed embedding examples. |
| RC25 | Genuine standard compression formats | Required RC | Add --output-format and SDK equivalent for gzip/zlib/raw DEFLATE/bzip2/xz/Zstd/Brotli, plus LZ4 frame and Snappy framed. Keep --format CIX-container and wrapped --external/CIXB1 semantics distinct. |
| RC26 | Dictionary APIs | Required RC | Dictionary handles and Zstd training/use first; expose support per codec with dictionary identity, ownership and resource bounds. No unversioned CIX dictionary extension. |
| RC27 | Tar and libarchive integration | Required RC | Qualify tar -I, pipelines/stdin/stdout/-d, libarchive external filter and optional native adapter with exact contracts. |
| RC28 | QuixDB Squash plugin | Required RC | Use public SDK for buffer/stream/splice with accurate bounds/options/flush claims; preserve compatibility wrapper; distinguish from SquashFS. |
| RC29 | 7-Zip adapter | Required RC | Provide CIX coder adapter with explicit method/version IDs and decoder distribution; keep ZIP compatibility separate. |
| RC30 | HDF5 / h5py / netCDF | Required RC | Native chunk filter with parameters, capabilities, bounds and truthful filter identity. |
| RC31 | Numcodecs / Zarr | Required RC | Provide Numcodecs configuration/registration and Zarr v2 codec, plus distinct v3 BytesBytesCodec. |
| RC32 | Blosc2 | Required RC | Native codec plugin with size bounds, versioning and host-compatible incompressible handling. |
| RC33 | RocksDB / WiredTiger | Required RC | Pinned experimental RocksDB CompressionManager adapter and WiredTiger WT_COMPRESSOR sizing/compress/decompress behavior. |
| RC34 | Hadoop and seekable chunks | Required RC | CompressionCodec lifecycle and streams, independent chunks and optional archive-identity-bound seek index. Splittable/random-access support only when proved. |
| RC35 | Primary language bindings | Required RC | C/C++, Rust and Python bindings over native library; Python optional for Python consumers, never required by standalone CIX. |
| RC36 | Additional language bindings | Required RC | Go cgo, Java JNI, .NET P/Invoke and Node Node-API; idiomatic buffers/streams/disposal/cancellation. |
| RC37 | Portable WASM subset | Required RC | Native portable subset with browser stream wrappers and explicit capabilities; no process-dependent specialist claim. |
| RC38 | gRPC and HTTP | Required RC | gRPC negotiation/message caps; standard gzip/br/zstd HTTP interoperability and explicitly negotiated CIX between controlled endpoints. |
| RC39 | GIO / GStreamer and storage examples | Required RC | Byte-stream adapters with flush/EOS/cancel; object-storage/backup examples with manifests/indexes. |
| RC40 | Native SquashFS userspace | Required RC | Distinct CIX adapters for mksquashfs/unsquashfs/libsquashfs/squashfuse, bounded independent storage profile, data/metadata/fragment handling. Do not substitute opaque .cix transport. |
| RC41 | Native SquashFS restricted decoder and VM | Required RC | Small bounded portable native decoder for the chosen storage profile, differential to Rust; experimental kernel integration and disposable-VM mount qualification. |
| RC42 | Additional platform format proposals | External dependency | EROFS, Btrfs, OpenZFS, ZIP, Parquet, Arrow IPC and OCI require individual compatibility proposals and feasible CIX-owned prototypes; distinguish standard-format alternatives. |
| RC43 | Platform qualification | Required RC | Linux x86-64/ARM64, macOS ARM64/x86-64 and Windows x64 source/build/binding coverage; actual execution required for qualification, not cross-compile alone. |
| RC44 | Lean professional distribution | Required RC | Reproducible root build/install, allowlisted source export excluding research/datasets/evidence, conventional layout/README/man/help/examples, native runtime dependencies, Debian/RPM and appropriate Mac/Windows packaging. |
| RC45 | Licenses and provenance | Required RC | Preserve all codec source identities/notices and dependency/linking/license requirements; project license proposal does not relicense third-party code. |
| RC46 | Sonar C/C++ actually works | Required RC | Execute proven CXX analysis including CIX and vendor visibility; prepared plugin is not completion. Replace stale all-36-verified gate with exact authenticated stop/idle/lease contract. |
| RC47 | Quality and dead-code closure | Required RC | Final formatting, Clippy warnings policy, Sonar, appropriate native checks and proven dead-code removal. Repairs restricted to CIX-owned code/build/adapters/tooling. |
| RC48 | Focused correctness and robustness | Required RC | Validate actual release paths, historical/cross-interface decode, arbitrary/empty/mixed input, malformed/truncated/trailing data, bounded expansion, concurrency and cancellation isolation; relevant fuzzing. |
| RC49 | Optimized build and reproducibility | Required RC | Optimize measured bottlenecks; retain qualified O3/LTO/CGU/SIMD choices with portable dispatch. PGO/allocator changes require evidence, not blanket tuning. |
| RC50 | Complete opportunity/backlog disposition | Required RC | Reconcile every historical queued method by distinct mechanism and actual source/evidence, including original Squash-codec inventory. Keep closed negative and unproven research separate from missing required product features. |
| RC51 | Release and benchmark gate | Required RC | No new benchmark until every required source/quality/compatibility/performance row is accepted and source, binary, dependency, options, limits and harness identities frozen. |
| RC52 | Later single-pass confirmation | Required RC | After gate only: one FAST/DEFAULT/BEST pass on canonical Silesia, each with fresh independently timed archive-only decode and maximum useful bounded concurrency. |
| RC53 | Later reporting and publication | User-paused | Preserve requested tables, comparisons, mobile dark/light private review portal and three-mode performance explorer/scatterplots. Other datasets, new corpus acquisition, Hutter and publication remain stopped by later direction. |
| RC54 | External registries and host acceptance | External dependency | Codec/filter/method identifiers, upstream acceptance, pinned host SDKs/toolchains and platform runners must be real and documented; development capability is distinct from stock compatibility. |
| RC55 | Canonical source baseline and port map | Required RC | Start from reconciled qualified native export/snapshot bytes, not the stale development tree. Map all 41 production reference modules to native owners and parity evidence. |

Every shipping native/full-engine profile must satisfy RC01's no-Python condition. RC40 includes extended attributes as well as data, metadata and fragment paths. RC11's detailed parser parity matrix must cover `-t`, `-l`, `--format`, `--route`, `--backend`, `--block-size`, `--history`, `--independent-blocks`, `--stream`, `--flush-interval`, `--parallelism`, `--profile`, `--portfolio`, `--external` and worker-range behavior.

The final register contains **55 requirements: 52 required RC items, 2 explicit external-dependency items and 1 user-paused reporting/programme item**. The scope review found no missing SDK integration category. These are requirement counts, not completed feature counts.

Gate phases are explicit in the JSON: source/quality requirements are `pre_benchmark`; RC51 is the readiness review; RC52 is `post_gate_confirmation`. Only RC52's frozen plan and scheduler readiness precede the benchmark, not the benchmark results themselves. External dependencies affecting a promised feature keep that feature open; RC53 retains its separate user hold.

## Work order and readiness proof

1. Bind the reconciled source revision, inventory all existing implementations and assign disjoint owners. Extract library interfaces and a native-port map with wire IDs, encoder/decoder dependencies and parity fixtures. Resolve retained performance and source gaps as part of that map.
2. Complete the native library/full-engine/CLI/streaming/scheduling contracts; integrate unchanged third-party codecs through CIX-owned native bridges. Port the still-Python successful specialist/selector/framing/decoder paths. No feature deletion or runtime Python workaround.
3. Implement SDK artifacts, formats, dictionaries, bindings and adapters in dependency order. Keep every later phase visible in this register. Resolve platform/SDK/identifier limitations with explicit evidence; do not mark unsupported targets working.
4. Run focused compatibility, streaming, interop, installed-consumer, cancellation/resource and relevant fuzz checks. These are acceptance checks, not a new corpus ranking benchmark. Preserve all failed attempts and useful predecessor evidence.
5. Repair Sonar CXX execution gating for the specific authenticated user-stop state and absent benchmark processes while retaining source identity and exclusive-resource guards. Execute actual CXX coverage, then fresh final-source quality checks. Repair CIX-owned code only; preserve and separately report external findings.
6. Build the optimized, lean distribution and qualify installation. Address host thermal/power/interference findings or explicitly retain unresolved qualification blockers; this instruction does not authorize a BIOS flash or unrestricted power limits.
7. Before any new benchmark, produce a readiness receipt mapping every required ID to current source and passing evidence, with no required item silently deferred. An external blocker keeps its dependent promise open unless the user changes scope. Freeze source, dependencies, binaries, flags, options, worker policy, budgets and harness. Coordinator/contract review verifies the mapping before the gate can change.
8. Only after that gate: perform the authorized single-pass FAST/DEFAULT/BEST Silesia confirmation on the new candidate. Record useful parallelism and contention, full selection costs, independent decode, archive bytes, aggregate resources and properly scoped comparisons. No repetitive averages, other dataset campaign or publication is added here.

“Equal or better than every record” remains a target to measure, not an assurance available before testing or a reason to hide exclusions. Acceptance ensures the intended mechanisms and full costs are present; results must establish the achieved ranking. Search is finite under disclosed bounds.

## Source ledger

- **current:** This coordinator thread 01a103be-69f6-76b1-aa46-b1c65331c533: automatic mixed-content scope, hygiene, CIX-only fixes, single executable/libraries, benchmark stop and all-features-before-RC instructions.
- **rust-origin:** Port CIX tools to Rust, thread 01a0f409-8b61-7eb3-9be6-0b7bd3817f94: original delivered USER migration prompt and repeated full-parity/automatic-selection/queue-completion instructions, read directly from retained session user messages.
- **stream-origin:** Same Rust thread: delivered USER bounded-streaming prompt; supported by CIX Compression Diagram chat 6abce623-7428-83ec-89b4-836f0b26a81d.
- **modes:** Rust thread delivered FAST/DEFAULT/BEST prompt; Clarify CIX Compression Modes chat 6abdee68-a6ec-83ec-9b7e-66d6fd1f0d0b.
- **sdk:** SDK/integration planning thread 01a10495-8aa1-7893-81eb-3eb28ebe3f51: CIX SDK and compression integration programme plan, four explicit user selections and latest coordination request; ten-group handoff and corrected no-Python authority.
- **architecture:** CIX Compression Diagram 6abce623-7428-83ec-89b4-836f0b26a81d; Branch · Write R&D Prompt 6abccceb-aaf0-83ec-b71c-5d94e0ed5174; CIX Architecture Summary 6ac09c00-f7b8-83ec-921f-7f8bb0800b25 and Branch · CIX Architecture Summary 6ac0c202-3a28-83ec-ae89-e1a2210feb64.
- **parallel:** Delivered Rust-thread parallelism/performance directives; Rust Performance Optimisation Guidance chat 6abf3fd8-3c6c-83ec-9cea-2d5abf205456; current user maximum-parallelism instruction.
- **distribution:** CIX Optimisation thread 01a0f927-3e23-7cb1-bdc3-cb7d08783ade: delivered user version-0.1 source/package/man/platform/SDK/SquashFS/reporting request, subject to later no-publication/Silesia-first holds.
- **review:** ../2026-10-04-automatic-specialised-models/REVIEW-SUPPLEMENT.md, ACCEPTANCE.md, FINAL-OPPORTUNITY-REVIEW.md, known-better-candidates.md, performance-carry-forward.md; ../2026-10-04-release-0.1/OPPORTUNITIES.md and closed result reports.
- **host:** ../2026-10-04-host-performance-audit.md: passive governor/topology/busy-frequency/thermal/power observations, not a claimed improvement.
- **source-backlog:** Implementation owner's direct 2026-10-04 post-stop backlog handoff, groups A–G: CLI/streaming, 41-module native port, concurrency, resource/environment, SDK/adapters, distribution and quality.

## Unresolved evidence, not waived requirements

The implementation owner's [RC backlog handoff](../2026-10-04-automatic-specialised-models/RC-BACKLOG-HANDOFF.md) is incorporated. Its source comparison found all 40 checked native source/Cargo/build inputs identical between the qualified export and frozen snapshot, while the old development native tree differs in 13 shared files, lacks split `src/cli.rs`, and contains four additional research files. Resolve this baseline before edits; the comparison does not cover every vendor/doc/test file.

The native port map has six groups: orchestration/CIXP/backend bridges; heterogeneous regions/CIXH1; complete registry and historical frame dispatch; chemical/database exact transforms; grid/image/volume with direct JXL; and ELF/ECOFF/TAR executable transforms/filter/joint-discount paths. Preserve PAQ v215/v216/joint-discount/store-state as unchanged native library dependencies and port CIX-owned adapters. Existing generic Rust primitives are reuse candidates, not proof that these schema/frame implementations already match. The machine register includes this grouping.

The implementation owner's source backlog identifies: 41 Python runtime/model modules needing native mapping; missing integrated CLI parity; bounded whole-input fallback; serial heterogeneous processing; Linux-specific process/resource enforcement; inherited backend environment cleanup; no integrated reproducible root build/package closure; unavailable Squash 0.8 SDK; unexecuted CXX scan; missing platform/adapter qualification. Some historic review findings have already been fixed, so map current code rather than reopening stale bugs. The detailed RC tests remain open until their own source identity is known.
