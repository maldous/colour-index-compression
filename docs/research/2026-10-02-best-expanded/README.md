# Expanded Rust BEST qualification

This evidence family qualifies a new native Rust artifact after its expanded
automatic BEST selector is ready. It is separate from the frozen d667 catalog:
no result from the older source is reused. The plan first evaluates the 33
complete Canterbury/Calgary/Artificial gate inputs, then the 17 remaining
catalog inputs, giving 50 exact-restoration BEST-only cells.

Each cell uses the ordinary automatic interface:

```sh
cix --best --verbose -o candidate.cix source.bin
uncix -o restored.bin candidate.cix
```

There is no route, backend, format, transform, history, block-size or thread
override. The release metadata must declare a 2 GiB (2,147,483,648 byte)
ordinary BEST working-memory default; the enclosing process is given a 3 GB
decimal RSS envelope for that work plus runtime overhead. The selector must
report its candidate and representation decisions on stderr; complete
archive bytes include all CIX framing and metadata.

Preparation freezes artifact metadata, hashes every executable and declared
native build library, records the source revision and dirty diff hash, then
writes immutable manifests. It does not build, acquire inputs or run a cell.
The queue uses the shared four-core WaveScheduler and waits while the current
Hutter controller holds its reservation. It requests no GPU. The bounded runner's systemd
`ExecMainStatus` can be stale for short failures, so each encoder/decoder
command writes an explicit child exit-status file; results lacking two zero
records are unqualified even if the supervisor said success.

Use after the new artifact has been built and frozen:

```sh
python3 benchmarks/cix_best_expanded_qualification.py prepare \
  --id native-best-EXACTREV-v1 --artifacts benchmark-work/NEW/final
python3 benchmarks/cix_best_expanded_qualification.py queue --id native-best-EXACTREV-v1
python3 benchmarks/cix_best_expanded_qualification.py collect --id native-best-EXACTREV-v1
```

The queue is intentionally not started by preparation. It records failures,
resource limits and selector logs; it does not substitute a smaller search or
different backend after an outcome.
