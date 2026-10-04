# Job interface and installed consumers

This checkpoint implements the same-executable job interface, conventional
multiple-file CLI processing, additional native SDK bindings, and explicit
Linux runtime staging. It does not accept the complete release candidate or
resume benchmarks. See `jobs-consumers-evidence.json` for exact snapshots,
artifact identities, scopes, and retained failures.

## Source-bound checks

| Surface | Passing evidence | Scope |
| --- | --- | --- |
| Multiple-file CLI | `job-mode-v3` | Five tests: individual outputs/restoration, aggregation, no overwrite, plan collision checks, and `--` filenames. Existing full-engine and stdin contracts also passed. |
| Same-executable jobs | `job-mode-v5` | Four protocol tests, three private command tests, five process tests; bounded records/errors, exact decode, no overwrite, malformed cleanup, cancellation cutoff, and output/worker temporary admission. |
| Node Node-API | `language-consumers-v2` | Installed SDK build and buffer/fragmented stream/lifecycle contract; numeric input and borrowed-receiver rejection. |
| Java JNI | `language-consumers-v2` | Installed headers/library, native shim, javac compilation and buffer/fragmented stream/reset/alias rejection contract. |
| Python SDK | `language-consumers-v3` | Twelve tests, including pre-copy/preallocation admission, second-pass length validation, streams, formats and dictionary persistence. |
| Numcodecs/Zarr | `language-consumers-v4` | Four tests with Numcodecs 0.17.0 and Zarr 3.4.0, including v2/v3 MemoryStore reopening through registered metadata. Persisted configuration cannot select a native library. |
| .NET P/Invoke | `dotnet-consumer-v2` | .NET 8.0.425 build with zero warnings/errors and native buffer, fragmented/empty stream, reset, cancellation and disposal contract. |
| Linux runtime staging | `runtime-closure-v1` | Explicit six bridges/eight companions, relocation, SONAME links, all bridge loads, spatial exact CLI/alias decode, wrong-RPATH rejection without source mutation. |

Language consumers used the explicitly hashed shared SDK installed by
`cli-bindings-v8`, compiled in `cli-bindings-v5`. They do not establish a fresh
final-source SDK build or another operating system. Runtime staging used the
new executable built in `job-mode-v5`. PAQ and JXL bridge loading is established
for that relocated package; actual codec operations through that exact package
remain to be qualified. The spatial fixture exercises JPEG-LS only.

The job protocol has separate control and file channels. Cancellation is
cooperative and has a defined commit cutoff. A failed final control-channel
write may leave an already committed output. It does not claim immediate
preemption of native calls or a process RSS ceiling. Worker memory and temporary
reservations remain conservative; the declared job staging cap is checked
before creating output.

## Preserved attempts and resources

`job-mode-v1` was prepared but not dispatched during active source review.
`job-mode-v2` found a mutable-reference compile error in the new CLI loop;
`job-mode-v4` found an error-string type mismatch in temporary admission. Their
corrected successors passed. `language-consumers-v1` found a missing parenthesis
in Node source. `v2` passed Node/Java then could not resolve package hosts from
the isolated runner; pinned wheel retrieval was staged separately and hashed.
`v3` passed Python/Numcodecs but exposed incompatible Zarr test keyword arguments;
`v4` used the actual installed APIs and passed. `.NET v1` built the library but
found missing imports in its contract program; `v2` passed both build and run.

All builds, installations, and tests used the root scheduler and the shared
four-core, decimal 12 GB RAM, decimal 4 GB temporary-storage, no-swap policy.
Individual jobs reserved 6 GB. Network dependency staging is separately
identified; it is not codec work or corpus acquisition. Closed test/SDK artifacts
were compressed one at a time, with hashes and archive-member verification
before expanded copies were removed. Recovery manifests are retained in
`consumer-space-v1` and `consumer-space-v2`.

## Open boundaries

Explicit expert overrides and full-engine streaming, useful scheduling,
heavy-model default effort policy, additional host adapters, native SquashFS,
platform execution, complete source/build/package closure, Sonar/dead-code
remediation and final optimized-source acceptance remain open. None is waived
by this checkpoint. Historical compression evidence remains separate from
these correctness checks. Benchmark and publication HOLD are unchanged.
