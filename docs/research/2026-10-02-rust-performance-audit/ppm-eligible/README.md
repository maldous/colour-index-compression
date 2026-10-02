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

## DHAT allocation evidence

The audit-only `ppm_eligible_dhat` example is built with the existing
`audit-dhat` feature; it never participates in production binaries.  It
encodes then restores each frozen 4 KiB kernel input under CPU 12 and the same
read-back 1 GiB, swap-disabled cgroup.  `tb`/`tbk` below are DHAT total
allocated bytes/events. `sum(mb)` is a sum of allocation-point peak-live
values, not a process RSS or a global peak-live claim; the largest individual
allocation-point peak was unchanged in every case.

| case | baseline bytes/events | candidate bytes/events | baseline/candidate sum(mb) |
|---|---:|---:|---:|
| random | 36,684,671 / 108,721 | 20,377,087 / 72,432 | 3,089,535 / 3,087,487 |
| strong | 277,237 / 8,286 | 146,197 / 4,191 | 12,913 / 12,881 |
| weak | 2,189,423 / 16,212 | 1,281,423 / 10,631 | 228,911 / 226,863 |
| absent | 4,236,269 / 53,474 | 3,140,141 / 36,092 | 1,578,109 / 1,577,981 |

Raw DHAT JSON, native stdout payload receipts, and cgroup receipts are outside
Git at `/home/user/audit-artifacts/ppm-eligible-controlled/dhat-20261002T1918Z/`.

## Status

The PPM unit tests passed and `rustfmt --check` passed for the changed files.
The direct kernel evidence supports promotion review only; it does not claim a
whole-CIXG1 speedup.
