# Exact native PPM estimates

The initial direct C++ log2 implementation failed exact-float qualification
(differences of a few IEEE bits) and was never enabled in a benchmark. The
revised implementation receives the calling Python interpreter's log2 values for
all possible bounded count totals. Context counts cannot exceed 16,384; adding
at most 256 escape mass bounds the lookup domain at 16,640. This is a generic
mathematical table, not source or corpus information. Native additions and
subtractions preserve the Python operation order; compile without fast-math.

```sh
g++ -std=c++17 -O3 -ffp-contract=off -Wall -Wextra -Werror -fPIC -shared benchmarks/native_ppm_estimates.cpp -o results/leaderboard/native_ppm_estimates.so
OMP_NUM_THREADS=1 .venv-pypy/bin/python -m benchmarks.qualify_native_estimates
```

Qualification passed 1,404 exact `float.hex()` comparisons across orders 0–8,
alphabets of size 1/7/256, cold/warmed history, zero/partial/full sample lengths,
all fixed escape laws, both update policies and the portfolio estimate. The
combined native encoder/estimator PyPy/GMP suite passed 83 tests in 51 seconds.
All four complete-stream hashes matched the previous native-encoder cohort.
Their total encoding time fell from 118.43 to 90.48 seconds. Concurrent machine
load limits this to diagnostic timing, not a speed-leaderboard claim.

After qualification, the original Silesia baseline's remaining ten workers were
stopped at recoverable checkpoints and confirmed absent. The same frozen policy
and output directory were resumed with the additional option:

```sh
--native-estimates results/leaderboard/native_ppm_estimates.so
```

XML and Reymont remain verified and were reused. New acceleration source,
wrapper and binary hashes are recorded, and checkpoint histories preserve the
runtime transitions. The standalone bounded-PPM Silesia cohort is unchanged and
uses no estimator acceleration.

The candidate rank verifier `benchmarks/ppm_bounded_position.py` rejects missing
members, different policies, altered physical artifacts and input hashes that
do not match the published corpus. Its mutation tests passed. A rank is still
unavailable until a complete cohort is verified.
