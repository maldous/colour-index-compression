# Conditional composition finite mechanism screen

Current native rank library from release 6ac05f8e9; three deterministic 16 KiB controls, four configurations each, one encode and one fresh archive-only decoder process each. No averages.

| Control | Global complete bytes | Context order1/bits4 | Context order2/bits8 | Raw |
|---|---:|---:|---:|---:|
| strong | 4302 | 2106 | 64 | 16414 |
| weak | 4302 | 4160 | 85 | 16414 |
| absent | 16659 | 16669 | 17456 | 16414 |

All 12 archives exact-restored with fresh native rank decoding. Experimental CIXCTX1 envelope, lengths, CRC, context parameters, active bucket IDs, partition lengths, histograms and rank/arithmetic termination are charged. Header mutation and truncation reject controls passed. This is an experimental format and library mechanism screen, not a production CLI archive or production-selection gain.

The strong and weak synthetic generators deliberately expose deterministic two-byte-context successors. Global histogram coding cannot capture this ordering; causal conditional partitions can. Absent random input expands under both context configurations and selects raw if choosing the minimum complete bytes. These effects do not come from BWT: no BWT transform is used.

CPU8/quota1, 1GiB memory/no swap/64MiB temporary caps are live read back. Native time/RSS for each invocation is retained; sub-centisecond GNU-time values must not support fine-grained throughput claims. Sampled cgroup high water is a lower bound. Build progress throughput is nominal scheduler metadata, not encoder throughput. Input source bytes were generated and hash-bound before measured configurations.

A template path error occurred before any lease/build/native execution and was corrected in the preflight freeze. Sealed native rlib and direct BigUint dependencies are hash-bound in freeze.json; no production code or Cargo manifest changed. Current cix compression/decode binaries are not used for this experimental outer frame. The decoder is a fresh process sharing the same rank library, not an independently implemented mathematical decoder.

CCA development replication and held-out qualification remain open before any production promotion. This screen closes only the declared synthetic context-partition cell, not prediction calibration, joint count coding or structural stream coding.

Independent review verified current retained driver/binary/library/runner and
archive/restored hashes. Global uses16 separate1024-byte tiles, while context
lanes span the16KiB control; attribute the gain to context-derived partitioning
plus lane histograms, not to a matched-information probability/coder change.
Encode regenerates the frozen deterministic fixture from CASE rather than
reading the generated input file; fresh restoration hashes equal the prebound
bytes. Malformed controls reject at outer header/CRC and do not qualify
CRC-valid malformed native payloads. The preflight asserted driver/runner hashes
but did not assert every frozen library hash before execution; retained hashes
were checked after execution and match. This is a provenance hardening gap,
not pre-dispatch proof. No rerun is required for this mechanism screen.
