# BEST baseline profiling hypothesis

Source inspection of pre-refactor `99f4f731991aeaf495fe3346a553afdcd107926b`
identified this automatic named-file candidate path:

`portfolio_auto::select -> main::encode_m6 -> rank::encode_context_type_classes
(order=2, bucket_bits=10) -> composition_rank -> colex_rank -> choose`.

The old `choose` recomputes arbitrary-precision binomial products/divisions
for dense cuts without polling the enclosing trial deadline. One ten-bit
context partition can create around 1,024 cuts. This is a source-grounded
hypothesis for the one-core, low-memory multi-minute baseline searches; it
is not a new captured CPU profile. Preserved `064a56456` evidence already
measured the old dense 64 KiB kernel exceeding 120 seconds versus a checked
recurrence taking 1.76 seconds with identical fixed-route archives.

The first live v2 BEST baseline fields.c observation completed in 274.50 s
with a 2,764-byte complete archive and successful own/cross restoration. It
is one observation, not the five-repeat matched conclusion. Its result is
`2026-10-03-matched-bd2-v2/runs/1f9e1bab95bc09a7eedaf4fe/result.json`.

After the matched wave, profile one completed fixture under identical
`--best --threads 4`, input hash, four physical cores, page-aligned
2,899,996,672-byte memory cap and zero swap. Freeze pre-refactor cix hash
`0a2731722d197083558d13210ca828316fe1bcd1f9a1d372d1d92d8502f55a7e`
and current cix hash
`02f2d6a437663341ee62233a2d8911af69249464fddad65855ecfdf27d1569dc`.

Capture isolated perf stat and then a callgraph, retaining lost samples,
archive bytes/hash and fresh own/cross decoding. Test the above call path
as attribution rather than inferring it from a route label. Forced-context
controls follow the automatic-path profile. No profiler attaches to the
current timed wave. Deadline/candidate changes that affect automatic output
must be reported separately from fixed-route implementation speedups.
