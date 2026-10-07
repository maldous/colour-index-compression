# Parallel scaling audit: prepared protocol

Status: `PREPARED_NOT_DISPATCHED`.  This is a single-file scaling study, not a
multi-file throughput score.  It must run only in a root-reserved quiet epoch:
no Docker scan, compiler, profiler, or unrelated benchmark process may share
the selected CPUs.

## Frozen measurement design

The runner will copy the release `cix` and `uncix` binaries into a unique
artifact directory, hash the binaries and every resolved runtime DSO, make the
copies read-only, and verify the manifest before and after every phase.  It
will capture `rustc -Vv`, Cargo profile/flags, kernel, CPU topology and
effective affinity before the first trial.  It refuses an artifact that changes
after preparation.

Inputs are deterministic 4 MiB strong-repetition, mixed-region, and random
byte generators plus existing frozen CCA fixtures only.  Input labels are for
evidence and never reach CIX route selection.  Every encoded archive is
decoded in a fresh process and SHA-256 checked before its receipt is sealed.

| dimension | values | scheduling |
| --- | --- | --- |
| containers | CIXG1, CIXG2 | independent CIX blocks only |
| effort | fast, default, best | report search cost separately |
| worker count | 1, 2, 4, 8, 12, 16, 20 | CIX currently caps `--threads` at 20 although 24 logical CPUs are visible |
| block maximum | 16 KiB, 64 KiB, 1 MiB | bounded streaming input/output |
| memory budget | 256 MiB, 512 MiB | includes workers and reorder slots |

The complete Cartesian product is intentionally not dispatched as one wave.
The execution queue first sweeps workers at 64 KiB/512 MiB, then block sizes
at 1/4/20 workers, then memory at the observed knee.  This distinguishes a
worker-scaling curve from parameter interactions and bounds local resource
use.  Each cell uses AB/BA release order and at least three repetitions.

## Separate dependent-stream controls

CIXM6 has persistent history/models and the CLI rejects parallel independent
block controls for it.  It is measured separately at one worker with the same
input/block/memory probes.  The audit records its serial throughput and size;
it never resets history or converts it to independent blocks merely to improve
CPU occupancy.

## Existing execution audit

`src/parallel.rs` already provides a bounded ordered pipeline: capacity counts
submitted inputs and out-of-order completed results, workers are persistent,
and `BTreeMap` preserves output order.  It is not sufficient evidence that
decode scales.  No decoder parallelization will be added unless profiling
shows a serial independent-CIXG decode bottleneck and this protocol measures a
bounded ordered decoder pipeline against serial decoding, including footer SHA,
backpressure, memory admission, cancellation and corrupt-input behavior.

Current static inventory: the Rust worker pipeline is the only native worker
pool; native external codec wrappers are currently treated as single-threaded
unless an experiment records otherwise.  A scaling receipt will record all
threads visible in `/proc/<pid>/task` and any backend-specific controls.

## Promotion rule

An implementation change requires a frozen-artifact matched result, fresh
owning and cross decode, unchanged complete bytes where the route is
deterministic, explicit RSS and size comparison, and a clean reserved epoch.
No source change is authorized by this prepared plan.
