# Final performance carry-forward

**Scope.** This is a read-only source and artifact inventory for the release review. It identifies optimizations already present in the distribution tree; it does not claim a new measurement or extrapolate a speed percentage. The entries are retained because the source implements the stated work, not because they were all exercised by one benchmark.

## Frozen artifact identity

| item | location | SHA-256 | metadata |
| --- | --- | --- | --- |
| encoder | `/home/user/src/cix-0.1-artifacts/final/bin/cix` | `09434a7f34b62691d0e187a22bd1b77fbb48a4b7f3f7d3ceea3857ca4e8b16a2` | x86-64 ELF; GNU build ID `b7f2977efd4086b836ac520507566683d8e46188` |
| decoder | `/home/user/src/cix-0.1-artifacts/final/bin/uncix` | `51d08e1d297920032dabb40599e92fa6c640c13d2e72c5e77b6b281a0e1f58eb` | x86-64 ELF; GNU build ID `902d8bf3259b49ea330d3bbaf1bf7aabe5a95feb` |
| native library | `/home/user/src/cix-0.1-artifacts/final/bin/libcix_native.so` | `862be208c30edcfe88c1111114a6aeeb05c06c84bd373c8c90c0448dc1d35012` | exports `cix_squash_splice`; no multinomial Python ABI |

The source anchors below refer to `/home/user/src/cix-0.1-distribution/src`. Its selected file hashes are recorded in the companion JSON.

## Carried-forward changes

| change | evidence anchor | implemented effect and boundary |
| --- | --- | --- |
| Count-range rank avoidance | `rank.rs:267-284` | `encode_count_range` builds the identical type-class header directly and encodes the range sequence. It avoids constructing a canonical arbitrary-precision rank that this mode would discard. |
| Colex and cardinality reuse | `combinatorics.rs:1-7,31-36`; `rank.rs:446-464,559-579` | Increasing colex inputs advance adjacent binomial coefficients. Canonical rank consumes the already computed cardinality, while the large-tile remaining-count mode avoids cardinality and rank-width work it does not serialize. Unordered colex input deliberately retains the definition fallback. |
| Fixed-mix stretch table | `fixedmix.rs:59-72,590-604,611-635,637-675` | The immutable 4,096-entry stretch table is initialized once per process and shared by encoder/decoder calls. Per-stream model state remains local. |
| PPM borrowed context lookup and eligible scan | `ppm.rs:31-72,425-451` | The fixed PPM encoder obtains context counts by borrowed map lookup and scans eligible symbols into aggregates plus the source interval, avoiding a temporary eligible-symbol vector for that hot path. General PPM paths still use `eligible` where a vector is required. |
| Bounded reader | `bounded_reader.rs:1-5,18-37,60-70` | Whole-input candidates use a single-pass bounded reader. The overflow probe is stack-backed, so a rejected source is not retained as `max + 1` bytes. |
| Ordered streaming and backpressure | `parallel.rs:1-8,154-157,227-230`; `gstream.rs:292-316` | Submitted blocks and out-of-order completed results consume bounded pipeline slots. The writer drains ready output and waits for capacity before reading ahead. |
| Per-encode transformed-byte cache | `chain.rs:82-104,1234-1314,1321-1389`; `cli.rs:2727-2742` | M6 chain trials can retain a bounded exact materialization for duplicate transformed bytes within one encode. Cache admission accounts for retained buffers; a zero allowance keeps uncached behavior. |
| M6 T1 histogram avoidance | `cli.rs:2279-2313,2315-2322,2832-2839` | `m6_fill_block` uses the timed reader directly. Histogram construction remains in `fill_candidate_block`, where candidate selection needs it, and is no longer paid by the M6 fill path. |
| Exact append-only competitive cap | `portfolio_auto.rs:34-37,173-228,449-453,511-515,620-626` | Whole-archive native CIXG/M6 trials receive a snapshot incumbent length. Because the archive writer is append-only, an emitted prefix longer than that incumbent cannot win the stable strict-size policy and is omitted with an explicit reason. Equality is still materialized and compared. The admission cap remains separate. |

## Legacy Python closure and acceleration

`cix/multinomial.py` is the authoritative legacy Python implementation. It is pure Python and imports only `hashlib`, `math`, `struct`, and `zlib` from the standard library (plus `dataclasses` and `typing`). Its SHA-256 is `c778e1abb15fc869f2d740ccb1cdb518940f92d0caad7bda71342903cf215729`. It supplies the exact multinomial/cardinality, Fenwick, arithmetic-coding and varint helpers required by the legacy modules that import it.

The optional accelerator is `benchmarks/fast_runtime.py` (SHA-256 `ab1ad4dbe21cdbcbf15f07ead8d4a256d892c988f8da4313e6187f3127192d73`). `enable()` imports **gmpy2** and replaces `math.comb` with `int(gmpy2.comb(...))`; optional bounded memoization then wraps pure functions. Any legacy extraction that invokes this helper therefore needs the Python `gmpy2` package and its platform native dependencies. Without it, execution uses the exact Python `math.comb` reference path.

There is no multinomial `.so`, `ctypes`, or `cffi` binding in the legacy Python codec. The frozen `libcix_native.so` cannot substitute for it: its only exported public symbol is `cix_squash_splice`. Adding a Rust/Python bridge would be new compatibility work and needs byte-for-byte legacy-frame evidence.

For closures that include BWT or LZ, `pydivsufsort` is a separate optional native dependency: `cix/bwt.py:23-51` uses it for BWT and otherwise falls back to a slow Python suffix sort; `cix/lz.py:196-198` uses its LPF helper when available. It is not a multinomial accelerator.

## Carry-forward decision

Keep the listed changes in the distribution source. For specialised legacy closure extraction, carry `cix/multinomial.py` and, where the selected closure called `fast_runtime.enable()`, provision `gmpy2`; add `pydivsufsort` only for BWT/LZ closure paths. Do not list `libcix_native.so` as a multinomial Python dependency.

