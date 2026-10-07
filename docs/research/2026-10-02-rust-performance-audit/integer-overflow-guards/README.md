# Reject high-bit integer truncation

Rust `checked_shl` checks the shift amount, not whether shifted-out value
bits are lost. The reviewed guards reject excess terminal varint bits and
Rice/PFOR high components before shifting. Valid maximum values remain
accepted. No encoder, candidate policy, frame or format version changes.

Frozen source and command/log hashes are in `manifest.json`; raw scripts and
logs are retained. Direct toolchain tests ran on CPU8 inside a read-back
1GiB, swap-disabled cgroup. The first compile attempt misplaced the PFOR
guard in FOR and failed with exit 101; that failure is retained and excluded from passes.
The corrected overflow filter passed 18 repeated executions. Existing focused
module checks passed 20 executions; four filters had zero tests and provide
no coverage. Codec limits, decoder memory and fixedmix recurrence integration
checks passed 16 executions. Counts include repeated module inclusions and
are not unique-test counts. These are correctness checks, not performance
measurements or per-child resource qualification.

Boundary fixtures construct legal usize::MAX varints and Rice values, reject
excess terminal groups and Rice q=2 at width=usize::BITS-1, and exercise valid
u64::MAX versus overflow in a single-exception 63-bit PFOR payload. The
existing numeric, legacy-LZ, fixedmix and histogram tests retain restoration,
canonical fixtures and malformed-input checks. Thirty-two-bit arithmetic is
covered by portable test construction and review; no 32-bit binary was built.

PPM, chain/BWT and main CIXM6 guards are separate reviewed additions. The
combined optimized suite must be rerun after all changes are merged.
