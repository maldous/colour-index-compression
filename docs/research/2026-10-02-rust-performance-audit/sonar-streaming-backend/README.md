# Streaming region helper cleanup

Independently reviewed source preserves persistent compressor references, active segment state, reset charges, model/history behavior, frame order and output handling. Immutable configuration is passed together; explicit branches preserve reset costs.

The actual runner and log cover check/build, one deterministic file-backed stream encode, fresh native restoration, exact hashes and one-byte truncation rejection. This is narrowly scoped refactor correctness. It does not establish idle-input flushing, pre-EOF output, slow-consumer backpressure, resource qualification or a throughput improvement. Earlier genuine pipe evidence remains separately qualified in the existing packets; it is not attributed to this run.
