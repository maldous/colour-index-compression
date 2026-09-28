# Exact native PPM acceleration

The frozen CIX encoder policy is unchanged. An optional C++ implementation of
existing PPM versions 3/4/5 replaces only encoding; estimates and decoding remain
Python. Its context orders, escape laws, update exclusion, history warmup,
rescaling, 32-bit arithmetic coding, pruning bound and candidate tie order match
the existing implementation. No filename, corpus, format or language metadata
enters the native code.

Build from repository root:

```sh
g++ -std=c++17 -O3 -Wall -Wextra -Werror -fPIC -shared benchmarks/native_ppm.cpp -o results/leaderboard/native_ppm.so
OMP_NUM_THREADS=1 .venv-pypy/bin/python -m benchmarks.qualify_native_ppm
```

Qualification completed:

- 560 individual variant outputs exactly matched Python; all decoded with the
  original decoder. The public portfolios also matched for each corresponding
  input/order/history combination.
- 120 additional comparisons covered orders 2/4/5/6/7/8, 70,400-byte histories,
  both update policies, fixed and SEE escapes, and pruning limits below, at and
  above the completed output length. Every return value matched Python.
- The full accelerated PyPy/GMP suite passed 79 tests in 66.11 seconds, with the
  existing optional-extension Cython warning.
- Four complete streams matched the Python control SHA-256 and round-tripped.
  Total encode time fell from 172.38 to 118.43 seconds (about 31% lower).
  Concurrent machine load makes this diagnostic timing, not a speed ranking.

The companion qualification logs and native-stream JSON preserve these results.
The shared-library binary and C++ source hashes are recorded by the runner.

After qualification, the original Silesia manager and its 11 remaining workers
were explicitly stopped. Their existing checkpoints were preserved, all old
workers were confirmed absent, and the same output directory was resumed using:

```sh
OMP_NUM_THREADS=1 .venv/bin/python benchmarks/leaderboard_run.py \
  --python .venv-pypy/bin/python --fast-comb \
  --native-ppm results/leaderboard/native_ppm.so \
  --manifest results/silesia-manifest.json \
  --output results/leaderboard/silesia --jobs 12
```

The verified XML result was reused unchanged. New checkpoints record acceleration
history; legacy checkpoints explicitly identify prior acceleration as unrecorded
in the checkpoint. The earlier run used PyPy/GMP without native PPM, as documented
in the run logs. Mixed-runtime elapsed times must not become a speed-leaderboard
claim. Physical sizes remain eligible only after exact full-member restoration.

This accelerates measurement; it is not itself a compression-size improvement or
completion of the first-place goal.
