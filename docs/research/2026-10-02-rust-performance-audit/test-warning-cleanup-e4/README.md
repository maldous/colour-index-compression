# Test and benchmark warning cleanup

Base `e4e9a10ab`; source hashes and raw receipt hashes are in `manifest.json`. Byte strings, borrowed singleton slices, finite repeat iterators and environment predicates preserve fixture contents and benchmark distributions. Independently reviewed.

The final suite passed 17 targeted decoder-memory, oracle and parallel-CLI tests; the final Criterion smoke passed encode and decode. Direct Rust 1.98.1, 1 GiB memory limit and zero swap were read back. Final process affinity was CPU 8; the broader cgroup cpuset was 0–31. Peak readbacks include any cached compilation and are not per-child RSS. No throughput benefit is claimed.

Earlier failed attempts are retained: `test-cleanup.log` reports compile exit 101 from a redundant reference introduced with byte-string conversion; corrected source removes the reference at the three affected callsites. `test-cleanup-corrected.log` is an authentication failure launching a system service. Neither is a passing test result. Successful corrected and final receipts are separate. Scripts contain exact cargo commands; launches used systemd with User=user, CPUAffinity=8, MemoryMax=1G, MemorySwapMax=0. No input corpus or source selection changed.
