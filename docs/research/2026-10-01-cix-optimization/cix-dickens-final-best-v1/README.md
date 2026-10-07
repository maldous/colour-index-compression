# Final release: fresh full Dickens restoration

Native release source: `938e88054adef5b9c33bfe2022b73fc6546074e9`.
The final source removes an unnecessary second halving of decoder admission,
after the decoder was changed to charge its buffers/native state itself.
Its regression actually encodes and restores a 64 KiB mixer frame which fits
the aggregate budget. Encoding policy and the qualified candidate registry
are unchanged.

This separately frozen WaveScheduler cell ran ordinary
`cix --best --verbose` on the same verified 10,192,446-byte Dickens input,
physical CPUs 16–19, a 1,200-second wall ceiling, 4 GB cgroup RSS ceiling,
512 MB temporary ceiling, and no swap. The CLI's ordinary working budget
remains 512 MiB, with four workers. No strategy/resource override was supplied.

Result: **2,799,567 complete bytes**, SHA-256
`b4b0e195209b593a3cf7ee047a1addc2556c70035a3fc037b64a44ef3d45c955`.
It is byte-identical to both preceding corrected-BEST runs and the verified
historical Python CIXB1/bzip2-9 archive. A fresh, archive-only native decoder
restored the exact original SHA-256
`b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.

[Summary](comparison-summary.json), [frozen manifest](manifest.json), per-run
receipts, stderr and copied GNU time measurements retain exact build/binary
identity and settings. The [paired comparison](../cix-dickens-qualified-best-v1/README.md)
is the matched timing evidence; this single final-source cell is a release
verification, not another speedup claim. Reproduce the final cell with a new
evidence area/prefix by adapting `benchmarks/cix_final_best_verify.py`; it refuses
to overwrite its existing immutable area.

No Python codec, acquisition, full corpus run, rank claim or GitHub Actions was used.
