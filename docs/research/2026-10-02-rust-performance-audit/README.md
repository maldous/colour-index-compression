# Rust CIX performance audit

This is the post-Sonar performance-audit protocol. It separates an
implementation change from a compression-policy change by comparing two frozen
native-release directories on identical cached bytes, profile flags, thread
counts and fresh native decodes. It records complete `.cix` bytes, encode and
decode wall/CPU time, peak RSS, affinity and the variance of repeated runs.
Within each input/profile/thread cell it counterbalances pre/current release
order as AB then BA on alternating repetitions, so a release does not always
receive the second-run thermal or cache position.

Each phase uses the existing local transient systemd cgroup runner with
`MemoryMax`, `MemorySwapMax=0`, `RuntimeMaxSec`, process-group cancellation,
temporary-space monitoring and a physical-core CPU set. Before every trial the
harness rehashes its input, release metadata and both release binary pairs. It
then cross-decodes every archive with the other frozen release in a separate
process whose source input is inaccessible. Missing GNU Time fields remain a
durable `UNQUALIFIED` result. Wrapper wall time is recorded in nanoseconds for
tiny operations; GNU Time remains the CPU/RSS source.

After those two fresh exact-decoding checks pass, the harness records the
archive and both reconstructed-output SHA-256 values and lengths, then deletes
the archive and decoded payloads. This is deliberate: retaining one archive
and two input-sized outputs for every repeated profile/release cell would
exceed the shared 4 GB temporary-space ceiling. A retained result is a bounded
fresh-decode receipt: resume, gate and collection revalidate its immutable
plan, binaries, DSOs, commands, GNU Time files, cgroup observations and stored
payload identities. They cannot rehash payloads that were deliberately
pruned. To make a new physical archive/decode observation, run a new immutable
audit identity; the run itself always performs the fresh owning and cross
decode before pruning. Verified receipts are capped at 128 KiB each; raw phase
logs are discarded after their structured exit/command evidence is recorded.

The child records its affinity from inside the transient cgroup. Memory is
enforced by `MemoryMax` and sampled as cgroup high-water; temporary storage is
monitored and stopped at the declared limit, rather than claimed as a kernel
disk quota.

Input, release and resolved-DSO hashes are checked sequentially under the
shared WaveScheduler lease before a timed wave and again before that lease is
released. Timed worker threads therefore do not run `ldd` or rehash a fixture
while another lane is measured. `prepare` and `collect` also refuse to run
while a wave owns that lock. Interrupted and unqualified task directories are
reduced to a 128 KiB diagnostic receipt and moved under `attempts/`; a later
run makes one clean retry. A pre-prune sealing receipt permits a crash during
payload deletion to finalize the already-verified result without silently
discarding its proof. Total retained interrupted-attempt evidence is capped at
128 MiB; further retries stop for review rather than eroding the aggregate
temporary-space budget.

No benchmark has been dispatched by this directory. The cancelled 20-thread
catalog and Hutter jobs are outside this protocol.

The required order is Canterbury, Calgary and Artificial (33 gate fixtures),
then Silesia. The runner rejects a Silesia stage until every requested gate
cell is `VERIFIED`. It uses existing frozen fixtures only and never downloads
data or invokes GitHub Actions.

Prepare after the Sonar fixes have been merged and a new current release
artifact has been built:

```sh
python3 benchmarks/cix_rust_perf_audit.py prepare \
  --id post-sonar-REV-v1 \
  --before benchmark-work/PRE_SONAR/final \
  --current benchmark-work/POST_SONAR/final \
  --threads 4 \
  --include-silesia
python3 benchmarks/cix_rust_perf_audit.py profile-plan --id post-sonar-REV-v1 \
  --binding-sha PREPARE_OUTPUT_SHA --task-id FROZEN_TASK_ID \
  --execution-sha FROZEN_EXECUTION_SHA
```

`prepare` prints `binding_sha256`. Copy that exact value into every later
`run`, `collect`, and `profile-plan` command; the harness rejects a plan,
fixture, artifact, environment, runner or scheduler file whose frozen hash no
longer matches. It also freezes resolved dynamic-library hashes and records a
separate immutable CPU/resource execution identity before a stage can resume.

The normal corpus policy is four independent datasets at four CIX threads
each, bounded to 12 GB total RSS and 4 GB temporary storage:

```sh
python3 benchmarks/cix_rust_perf_audit.py run --id post-sonar-REV-v1 \
  --stage gate --threads 4 --workers-per-dataset 4 --jobs 4 \
  --binding-sha PREPARE_OUTPUT_SHA --confirm-execution
```

That command is deliberately incompatible with a plan that includes the full
thread scaling matrix. Prepare a dedicated `--threads 4` corpus plan for the
four-by-four run. Use a separate, small gate-only plan to measure scaling
`1,2,4,...` with `--jobs 1`; this avoids confusing concurrent dataset
throughput with a single-file scaling curve.

Profile before editing code. `profile-plan` writes the exact perf events,
DHAT, Criterion and build/PGO queue. DHAT and Criterion are intentionally
audit-only additions after a hotspot is measured; they are not production
dependencies. There is currently no DHAT instrumented build, so the plan marks
allocation profiling blocked rather than presenting a fictional command. Build
variants and PGO require separate immutable artifacts and the PGO training
fixture hashes must differ from held-out evaluation fixtures.

`fast` means FAST. `default` is the ordinary balanced profile and is the
historical `current` spelling. `best` is the historical `size` spelling. The
script records this mapping rather than treating those names as independent
codecs.
