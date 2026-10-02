# Checked decoder stage refactor

Source helpers preserve CIXB1 dispatch, CIXG descriptors, frame admission, route dispatch, memory checks, checksums, output and footer behavior. Independently reviewed net source diff against d52.

The corrected actual runner uses fresh paths. Its status ledger verifies parent/candidate archive equality, reciprocal native restoration and one-byte truncation rejection (exit 2) for G1 raw, G2 raw, M6 fast and B1 bzip2. Raw generator, commands, hashes and statuses are retained. The earlier overwrite-refusal attempt is retained under `raw/invalid/` and is not validation evidence.

These tiny cases establish scoped output/error compatibility only. The corrected runner does not retain cgroup resource verification, and no timing, memory, all-route or comprehensive malformed-input claim is made.
