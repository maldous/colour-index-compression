# Next matched Rust performance audit plan

This is a nonexecuting plan. It uses `benchmarks/cix_rust_perf_audit.py`, whose
`prepare` freezes two immutable release directories and validates the 33 cached
CCA fixtures (11 Canterbury, 18 Calgary, 4 Artificial) against the frozen
census before any run. Silesia remains refused until all requested CCA rows are
freshly verified.

## Artifact comparability

The older `scaling-qualified` evidence is explicitly unqualified: its retained
result says the executed harness source is unattested and two/four-thread decode
rows exited natively with status 2. It is not a valid pre-refactor baseline.
The current `45e` evidence is attested but answers its own frozen question.
Build a fresh release-lto baseline from frozen pre-refactor `99f4f7319` and the
current final revision with the same direct stable toolchain, frozen per-revision lockfiles,
`--profile release-lto`, C/C++ flags, environment, DSO hashes and build cgroup.
Each directory needs `cix`, `uncix`, and matching `native-release.json`; the
harness rejects altered binary hashes and records resolved DSO hashes.

## Proposed commands after final freeze

```sh
python3 benchmarks/cix_rust_perf_audit.py prepare --id 2026-10-03-matched-final \
  --before /ABS/pre-final-release --current /ABS/final-release \
  --profiles fast,default,best --threads 4 --repetitions 5 --include-silesia
python3 benchmarks/cix_rust_perf_audit.py run \
  --id 2026-10-03-matched-final --stage gate --threads 4 \
  --workers-per-dataset 4 --jobs 4 --rss-per-job 2900000000 --temp-per-job 900000000 --binding-sha BINDING_SHA --confirm-execution
python3 benchmarks/cix_rust_perf_audit.py run \
  --id 2026-10-03-matched-final --stage silesia --threads 4 \
  --workers-per-dataset 4 --jobs 4 --rss-per-job 2900000000 --temp-per-job 900000000 --binding-sha BINDING_SHA --confirm-execution
```

The runner enforces distinct physical CPU sets, systemd `MemoryMax` and
`MemorySwapMax=0`, child affinity/cgroup readbacks, GNU time, fresh own and
cross-native decode hashes, and complete archive size. It must receive a
dedicated Sonar-free lease; do not overlap Docker, builds, or other benchmark
units. The harness intentionally uses four datasets × four threads, not a
single uncontrolled twenty-thread process.

## Audit gaps to resolve before execution

- Rebuild frozen pre-refactor `99f4f7319` with matching provenance. The
  attested current `45e` record is not a substitute for that matched rebuild.
- `--threads>1` is currently rejected for decode, so decode scaling must remain
  one thread until a separately qualified decoder change exists.
- Validate harness argument names against `--help` after final freeze and
  retain the prepared plan/binding hash before `run`.
- The harness records wall/user/system/RSS, archive bytes and cgroup sampled
  high water. It does not establish cache-miss, allocation, perf, or PGO
  attribution; those need independent scoped probes.

## Dependency control

Root parsed both frozen Cargo lockfiles: every common package retains the same
version and none was removed. The final lockfile adds optional DHAT and Criterion
instrumentation dependencies. The normal CLI has no DHAT global allocator;
instrumentation lives in separate audit binaries. Preserve both lock hashes
instead of claiming that the lockfiles are identical.
