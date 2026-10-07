# Native Rust CIX BEST, 20-thread catalog qualification

This plan is prepared after the user authorized one serial `--best --threads
20` evaluation per cached official catalog input. It freezes 33 CCA gate
inputs followed by 17 remaining catalog inputs. The controller must be started
under `taskset -c 8-31` and must find twenty distinct physical CPUs; the plan
does not run on the current narrower affinity.

Each cell has a 3 GB RSS and 1 GB temporary-space budget with no swap and no
GPU. This retains the normal 2 GiB BEST working policy plus runtime headroom;
the shared serial scheduler remains capped at 12 GB RSS and 4 GB temporary
space, leaving the user-authorized 4 GB Sonar server and 1 GB scanner capacity.
It runs fresh native archive-only decoding and retains GNU Time output,
explicit child statuses, typed candidate coverage and per-input durable result
records. Preparation does not build or benchmark.

```sh
taskset -c 8-31 python3 benchmarks/cix_best20_catalog.py prepare \
  --id native-best20-REV-v1 --artifacts benchmark-work/ARTIFACT/final
```
