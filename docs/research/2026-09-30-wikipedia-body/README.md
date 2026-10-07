# Wikipedia body-line PAQ stage

Prepared only; no body compression run has started. The body transform considers
complete `<text>` bodies and newline lines 48–512 bytes. It stores its complete
rule set, skeleton dictionary, holes, member placement and all literal boundaries
inside the transformed frame. Diagnostics remain outside the archive.

The synthetic fixture contains 160 pages with repeated infobox-style lines, changing
decimal, link and URL values, plus an incomplete raw boundary. The development body
trial is a matched 4 MiB dev0 comparison against the verified original-byte PAQ control
reference `799638` bytes. Dev400M prepares an original control only; no body trial
there is authorized until that control verifies.

Dev400M (rather than the initially considered dev100M) was selected from prior
development-only representation profiling: its body frame reduced 79,471 bytes
across 29 families, compared with 41,647 bytes across 320 families at dev100M.
That selection is not a PAQ result. Its original-byte PAQ control is prepared
only; a body candidate cannot start automatically from it.

`fixtures/repeated-body-lines-160pages.bin` is deterministic fixture input:
65,339 bytes, SHA-256
`8e6e9ba642b50dbeb53ed8248d23addcac5afe48998228748c12d23f7fb5dd00`.
Regenerate it with `python benchmarks/hutter_wikipedia_body_prepare.py
docs/research/2026-09-30-wikipedia-body/fixtures/repeated-body-lines-160pages.bin`.
All manifests freeze the PAQ v216 `-4 -simd AVX2` binary hash, the
`candidate.source.bin` PAQ basename, and an archive-only independent decoder.
