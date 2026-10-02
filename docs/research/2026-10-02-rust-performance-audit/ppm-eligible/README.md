# Fixed PPM eligible scan

## Scope

`rust/cix-native/src/ppm.rs` replaces the temporary eligible-symbol vector in
`encode_fixed_from_state` only.  It makes one symbol-ordered scan for mass,
eligible count, singleton count, and the source interval; an escaped context
is scanned again solely to mark the same eligible symbols excluded.  The SEE
encoder and all decoder paths retain `eligible` unchanged.

The control is `9214e2f8b`; the candidate has no selector, frame, model,
or decoder change.  All measurements use the fixed order-3 PPM kernel.

## Exactness

For random, strong, weak, and absent-context inputs, all 32 combinations of
escape method 0--3 and v3/v4 exclusion policy produced byte-identical
payloads.  Each candidate payload was decoded by the baseline and each
baseline payload by the candidate.  The retained identity artifacts are
outside Git at `/home/user/audit-artifacts/ppm-eligible-controlled/identity-20261002T1902Z/`.

## Controlled timing

The retained ABBA run is outside Git at
`/home/user/audit-artifacts/ppm-eligible-controlled/abba-20261002T1906Z/`.
It used 5 ABBA pairs per case, with two observations per arm per pair (20
means per arm), direct compiled benchmark execution on CPU 12, and a read-back
`memory.max=1073741824`, `memory.swap.max=0` cgroup for all 80 processes.
The originally started wrapper-only runs are preserved outside Git and are not
used here.

| case | baseline encode ns | candidate encode ns | baseline decode ns | candidate decode ns |
|---|---:|---:|---:|---:|
| random | 4,610,061 | 3,220,844 | 4,705,156 | 4,867,243 |
| strong | 423,960 | 356,951 | 444,841 | 402,372 |
| weak | 1,021,464 | 830,011 | 1,086,385 | 1,032,085 |
| absent | 2,176,346 | 1,525,467 | 2,238,996 | 2,156,156 |

Encode is lower in all four cases.  Decode does not exercise the changed
fixed-encoder helper, so the random decode variation is not attributed to this
change.  This evidence is kernel-only and does not claim a CIXG1 speedup.

## Status

The PPM unit tests passed and `rustfmt --check` passed for the changed files.
An allocator-profiler before/after run remains required before promotion from
this bounded experimental source change.
