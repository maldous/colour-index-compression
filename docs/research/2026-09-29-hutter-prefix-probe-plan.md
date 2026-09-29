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
  --output results/hutter/paq-v215-10l-prefix8m --cpu <allowed-cpu>
```

This will establish a costed text-path baseline, not a Hutter score, eligibility
claim, ranking, or estimate for full enwik9.
