# First bounded Hutter text probe

The first real Wikipedia experiment is a non-qualifying 8 MiB prefix of the
canonical enwik9 byte stream. It uses local `paq8px v215` with
`-10L -forcetext -simd AVX2`: the highest documented local PAQ level below the
10 GB Hutter RAM limit (nominal 8,003 MB before the small LSTM increment).
`-11` and `-12` are excluded because their documented nominal memory exceeds the
limit. `-T` is excluded because its external dictionary/expression inputs would
need independent submission accounting and reconstruction evidence.

The runner creates an exact prefix, hashes it, retains the physical PAQ archive,
decodes to a separate file, checks matching SHA-256 values, and writes commands,
binary hash, wall/process time and peak RSS to `complete.json`. It runs one CPU
through `taskset` and makes no full-file projection. It must execute only after
the shared measurement lock is free:

```sh
flock /home/user/src/cix-evidence-baseline-20260929/evidence/baseline-20260929/raw/measurement.lock \
  .venv/bin/python -m benchmarks.hutter_text_prefix_probe \
  --output results/hutter/paq-v215-10l-prefix8m --cpu 8
```

This will establish a costed text-path baseline, not a Hutter score, eligibility
claim, ranking, or estimate for full enwik9.

## Launch correction record

The first two durable unit invocations (`c969fb45c77746a08a741d21e0c01cef`
and `d769fa61fb24434989cac6b987531761`) waited only: the old baseline service
remained active and no result directory was created. They inherited CPU 16 from
an initial affinity mask. The actual cgroup cpuset is CPUs 0–31 and CPU 8 is a
5.8 GHz performance core, whereas CPU 16 is a 4.3 GHz efficiency core. The
waiting unit is therefore replaced before computation with CPU 8. Any future
Geekbench 5 calibration must use CPU 8 as well.
