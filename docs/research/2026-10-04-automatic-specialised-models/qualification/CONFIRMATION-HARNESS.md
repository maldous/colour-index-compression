# Silesia confirmation harness

[confirm.py](confirm.py) prepares one immutable plan containing exactly 36
sequential cells: the twelve canonical Silesia members under FAST, DEFAULT and
BEST. It does nothing unless called later with `--run`; the root-owned
WaveScheduler remains the only executor.

Each cell performs a fresh ordinary staged CLI encode followed by a separately
timed fresh archive-only decode. The encode command includes the profile,
`--threads 4`, `--memory 11000000000B`, and `--report` for selection
coverage. The decode command includes the same memory allowance and
`--max-output` equal to the frozen source length. Encode and decode phase
ceilings are 48 and 12 hours respectively. The scheduler receives one phase at
a time with four leased physical cores, decimal 12 GB aggregate memory and
decimal 4 GB temporary storage. The product receives decimal 11 GB; the remaining
allowance covers wrappers and process overhead. Swap is disabled.

Each CLI phase is executed through [measure_cli.py](measure_cli.py). Its receipt
records wall time around only the ordinary CLI subprocess, CPU from the
`RUSAGE_CHILDREN` delta, and kernel cgroup v2 `memory.peak` and `cpu.stat`
read after the child exits while the wrapper remains alive. The peak includes
small wrapper/phase overhead and is a cgroup-phase measurement, not a process
RSS claim. A missing or invalid cgroup receipt fails the phase.

Before dispatching every phase, the harness verifies frozen identities for the
staged CIX and decoder, policy, local historical-reference document,
source-export tree, stage tree, host libraries/Python standard library, the three
harness files and the scheduler's complete local execution closure. The frozen
scheduler entry and interpreter are invoked directly. These checks occur
outside the timed wrapper. There is no `ldd` proxy or source/build hashing
inside the measurement phase.

The plan contains only source identities for validation. Runtime receives the
ordinary source argument and does not receive corpus names, hashes, saved
streams, model decisions or candidate data.

A cell is resumable only when its own `result.json` says `VERIFIED` and
carries the current plan hash. The summary is derived output and never controls
resumption. Any `STARTED`, failed, scheduler-failed, or malformed result state
stops execution; it cannot trigger an implicit retry. A verified decoder output
is SHA-256 checked against the frozen source and then deleted. Retained
archives, reports, scheduler logs and all other qualification-area files count
toward the shared four-gigabyte temporary cap. Each active phase receives only
the remaining allowance after previously retained evidence. Its scratch directory
is inside the monitored work directory and is passed through `TMPDIR`. Final
directory accounting runs after each phase. Temporary storage enforcement is
sampled by the existing scheduler; it is not a filesystem quota.

Before any dispatch the harness revalidates exact member/profile order, flags,
budgets, cross-mode source identity, and the twelve canonical source hashes and
211,938,580-byte total against frozen references. The tiny fake-command test is
explicitly marked `fixture_only` and makes no compression claim.

The summary reports per-cell complete archive bytes, source percentage,
reduction percentage, encode/decode wall and CPU totals, phase cgroup peaks,
and encode/decode MiB/s. Historical portfolio and public figures are frozen in
the separately supplied references document and remain outside these measured
totals.

A root-run tiny fixture should use a fake staged encoder/decoder plus a fake
schedule that invokes the wrapper, then confirm: plan has 36 cells; canonical
tie/status flow reaches `VERIFIED`; an injected failed state prevents a second
dispatch; and a missing cgroup receipt fails qualification. It must be run under
the same reviewed scheduler path before the real pass.
