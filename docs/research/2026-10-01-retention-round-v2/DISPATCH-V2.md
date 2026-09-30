# Retention v2 orchestration correction

The first v2 wave completed 11 verified cells and one expected mixer route
timeout. The frozen harness then stopped before another wave because its
failure-classification glob matched `*.stderr.log` but not the nested file named
exactly `stderr.log`, where the actual `TIME_BUDGET` marker was retained.

`benchmarks/retention_dispatch.py` is an orchestration-only continuation
wrapper. SHA-256:

`5437c6c9ec5d419feef413a1bbaa871f65709c3db2b05549ab2645275cc5397d`

It imports the frozen harness, scans both stderr naming forms, requires an
actual timeout marker in retained log content or an explicit cgroup resource
stop reason, and then invokes the existing run loop. A referenced path alone is
not a budget marker. `WORKER_EXIT` alone remains unexpected.

The wrapper changes no manifest, experiment identity, input, build snapshot,
codec, resource budget, encode/decode command or selected archive. The existing
WaveScheduler excludes all claimed cells, so the first 12 are not retried.

Continuation command:

```sh
.venv/bin/python -m benchmarks.retention_dispatch \
  --authorization docs/research/2026-10-01-retention-round-v2/authorization.json \
  --stage forced-hybrid \
  --stage original-controls \
  --stage adaptive \
  --stage replication-forced-hybrid \
  --stage replication-original-controls \
  --stage replication-adaptive
```
