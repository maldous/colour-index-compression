# Exact colex-rank transition probe

## Scope and controls

This is a fixed-route implementation probe, not a corpus result. It compares
the release-LTO binary from `15426f310` with the colex candidate on the same
synthetic bytes. Both use `taskset -c 18`, `--format cixm6`, `--threads 1`, a
fixed block size, and `/usr/bin/time -f '%e %U %M'`. No selector, route,
container, history, or block-boundary policy changed.

The candidate comprises `0e8685ecc` (shared exact helper) and `cf00a9f6c`
(adaptive transition, rank integration and this evidence). The weak and absent
input SHA-256 values are respectively
`c118d69043dda0fb0c66a330cefb2a3dd89fb6ad9ebc37135afe75ec3291949f` and
`de2f256064a0af797747c2b97505dc0b9f3df0de4f489eac731c23ae9ca9cc31`.

The strong input alternates zero and one bytes. The weak input is a 64 KiB
zero block with two nonzero bytes at widely separated positions. The absent
input is a 64 KiB zero block. Inputs are synthetic and have no filename or
corpus based dispatch. Raw command output is retained outside Git in
`/tmp/cix-colex-bench/`.

## Initial strong result

For the 2 KiB strong input, five baseline runs were wall `0.13, 0.12, 0.12,
0.12, 0.13` seconds and CPU `0.11, 0.11, 0.11, 0.11, 0.12` seconds, with 6400
KiB peak RSS. The first recurrence implementation measured 0.03 seconds wall
and 0.02 seconds CPU in all five runs, with 6144--6400 KiB RSS. Both produced
25-byte archives with SHA-256
`473f2e408bf91e6b035a6e4deb3292e76f3f01749b98dec50ef37f3c32ad41a0`.

The pre-change 64 KiB dense input did not complete inside 120 seconds; the
first recurrence build completed in 1.76 seconds wall, 1.75 seconds CPU and
9100 KiB RSS. This is a pathological control rather than a general throughput
claim.

The final adaptive build measured three weak-input CPU times of `0.57, 0.58,
0.59` seconds against baseline `0.58, 0.59, 0.58`; its peak RSS was
9000--9024 KiB against 8912--8916 KiB. Complete weak archives were identical
(SHA-256 `48d50720aff54719151864c197bcbb6f0a3aff91b767cbb4150aa9ac8293bbe7`).
For the absent input, baseline CPU was `0.55, 0.55, 0.56` seconds and candidate
CPU was `0.55, 0.55, 0.55`; complete archives were identical (SHA-256
`d08b1c17b1fc0dd4c77993626025dc93a1f3f1a0df8760396c3432c41570cc92`).
Wall time varied with host I/O for these sub-second CPU runs, so these controls
establish no material regression rather than a throughput win.

## Exact transition rule

For a transition from `C(position, width)` to
`C(next_position, width + 1)`, the implementation recomputes directly when
`min(width + 1, next_position - width - 1)` is no greater than the number of
recurrence steps (`next_position - position + 1`). Otherwise it advances the
coefficient one exact binomial recurrence at a time. Both alternatives use
`BigUint`; the direct path protects sparse long gaps while the recurrence
removes dense-rank recomputation. Every path polls the candidate limit on
entry and at most every 256 loop steps.

The same helper now serves CIXG1 `rank.rs` colex and composition headers. A
forced-CIXG1 2 KiB control produced identical complete archives before and
after (SHA-256 `a6f0560ce897c3d3a42e3c771d79b3ab75e544fedb08fff1a664a5d4b1c39e2d`),
and each generation decoded correctly in the other binary.

## Reproduction

```sh
taskset -c 18 cix --format cixm6 --threads 1 --block-size 2KiB -k -f \
  -o out.cix alternating-2k.bin
uncix -c out.cix | sha256sum
```

Run the pre-change and candidate binaries with this identical command and
compare complete archive hashes before comparing timing.
