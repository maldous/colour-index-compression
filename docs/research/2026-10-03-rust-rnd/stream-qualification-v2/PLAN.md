# Bounded stream qualification v2

Prepared only; root leases and runs the two numbered rows once each. The Python driver orchestrates supplied Rust `cix` and `uncix` executables. It does not encode or decode data itself.

| Row | Profile | Fixed flags | Lease |
| --- | --- | --- | --- |
| 1 | G1 | `--format cixg1 --threads 2 --parallelism blocks --fast --stream --flush-interval 50ms --block-size 65536B --memory 16MiB` | 2 physical cores, 256 MiB cgroup |
| 2 | M6 | `--format cixm6 --threads 1 --fast --stream --flush-interval 50ms --block-size 65536B --memory 16MiB` | 1 physical core, 256 MiB cgroup |

The source is generated once per row, incrementally, from the frozen xorshift64 seed. An independent fixed-width C generator is compiled and hashed before any codec child, then its SHA-256 is frozen and required by the driver. It is 32 MiB, larger than the 16 MiB codec memory setting. The source is pseudorandom transport data: it asserts streaming mechanics and byte preservation, and does not represent a compression opportunity or support a size claim. Writes use the declared irregular schedule and are split exactly at 1 MiB + 256 B. The producer then stays open for 250 ms. During that pause the driver requires both nonzero encoded bytes and nonzero bytes from a separate Rust decoder fed by the live archive pipe. Its decoder output is deliberately drained in 4 KiB pieces with a 2 ms delay.

After EOF, new current and frozen BD2 Rust decoder processes restore the archive and independently SHA-256 match the incremental source hash. The BD2 path is `benchmark-work/combined-bd2-validation/final/uncix` with SHA-256 `f9ec393c689c6602a3912ca74a8d83575979dcdf2cb0646ac2760f41cf80db84`. The driver also exercises empty input, truncation, a flipped middle byte, and an idle producer interruption. M6 adds the complete-archive decoder pipe with EOF deliberately held open, followed by SIGINT and, only if needed, SIGKILL process-group reap. This regression is run only after root seals the footer fix.

Every native child is launched in a separate session. The parent watchdog enforces 120 seconds and terminates its process group. The archive is at most 48 MiB; the one retained restored output is at most 32 MiB and is deleted before malformed controls. Malformed copies are made and deleted sequentially while their output is streamed, counted to 32 MiB, and discarded. The driver uses at most 64 KiB source, pipe, hashing, and malformed-copy buffers. Root must enforce 128 MiB temporary disk and record cgroup and GNU `time -v` receipts. `result.json` records the row, exact flags, source/archive/restoration hashes, binary hashes, live partial counts, and all gate booleans. No result exists until root runs the sealed driver and records its source hash.
