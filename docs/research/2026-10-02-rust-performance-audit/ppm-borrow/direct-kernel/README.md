# Direct PPM borrowed-key kernel audit

`rust/cix-native/benches/ppm_borrow_kernel.rs` is audit-only source. It is not
registered in `Cargo.toml` and must not be added to production targets without
approval. It directly constructs fresh fixed order-3 PPM encoder and decoder
state for deterministic 4 KiB input; it has no route selection or CIXG1 frame.

The completed 2026-10-02 run is **concurrent-host screening**, not a resource
qualification: the host had globally enabled swap and an address-space limit is
not a `memory.swap.max=0` cgroup. The formerly committed executables were moved
outside Git before this patch; their retained SHA-256 values are:

* baseline measured binary: `e346940b88974ec702f85d96d1eb92cb3f055988b06e1c3b9206c227ecc2efbd`
* baseline identity binary: `b63ea04efae59553f6bfc03283d8f5e2114605cbac8746af0cb14f5e9d3c92ea`
* candidate binary: `10dc480345096491fa19a96a8a41ef8ce48f1b47b978a17260c55bf97532a086`

The screening raw files, duplicate identity runs, and invalid no-`--bench`
smoke runs are deliberately excluded. A future timing result needs at least
five paired run means under a read-back cgroup with `memory.max=1073741824`
and `memory.swap.max=0`, CPU 10/11 assignment, and 512 MiB temporary cap.
Its direct inputs must cover random, strongly repetitive, weakly repetitive,
and absent-context cases: unique-context lookup misses perform the extra
`get_mut` then insertion hash and can regress.

Timing truth retained from the excluded screening (Criterion mean, ms) is:

| CPU | baseline encode/decode | candidate encode/decode |
| --- | --- | --- |
| 10 | 4.604593 / 4.694038 | 4.434406 / 4.502332 |
| 11 | 4.354585 / 4.439318 | 4.423316 / 4.388586 |

The two-CPU arithmetic means were 4.479589 ms versus 4.428861 ms for encode
and 4.566678 ms versus 4.445459 ms for decode. This screening shows no
aggregate CPU regression, but it does not qualify timing or resource claims.
The prior DHAT allocation reduction remains an allocation-only observation.

## Controlled run 2026-10-02

The controlled artifacts are outside Git at
`/home/user/audit-artifacts/ppm-borrow-controlled/`. Each of 40 timed processes
(four cases × five counterbalanced pairs × two arms) read back
`memory.max=1073741824` and `memory.swap.max=0` in its cgroup JSON. Each has
raw Criterion samples, process CPU/wall/RSS JSON, source/binary hashes, and
cross-decoded payloads there. The separate registered measurement manifests
are outside the production Cargo workspace.

Mean nanoseconds over the five paired runs were:

| case | baseline encode/decode | candidate encode/decode |
| --- | --- | --- |
| random | 4,693,076 / 4,712,289 | 4,533,828 / 4,573,857 |
| strong | 550,808 / 562,993 | 364,871 / 376,063 |
| weak | 1,063,645 / 1,129,064 | 879,217 / 939,143 |
| absent (de Bruijn unique 3-contexts) | 2,171,378 / 2,136,420 | 2,007,264 / 1,943,723 |

The candidate was lower in all eight reported means, including the
all-unique-context miss case. These are direct fixed-order-3 kernel results;
they do not measure selector or CIXG1 performance.
