# CIX backend portfolio, version 1

Implementation commit: `ceb41d6442da8454c247fd3aed2b31d50c452ada`.
Frozen CIXG1 implementation remains commit `1302bd7` with its original format.
Archive-only decoding dispatches on the five-byte magic.

CIXB1 external archives start with little-endian `<5sBBII32s>` (47 bytes):
magic `CIXB1`, backend ID, profile ID, original length, payload length,
SHA-256 of reconstructed input. The payload-length field starts at offset 11.
The remainder is the exact standard codec artifact: no hidden dictionary,
per-input model, sidecar or original-source dependency. Backend IDs 1–5 are
gzip, bzip2, XZ, zstd and Brotli. Profiles 1–3 are fast, current and size.
Length/trailing-data/hash violations fail decoding. This adapter caps input at
16 MiB and decoded output at the stated input bound.

CIXG1 candidate archives have no additional wrapper. CIXG1's block route IDs,
substream coder IDs, dictionaries/counts, transform selectors, framing and
checksums stay physical. No encoder search is repeated by the decoder.
The separate optional CIXR1 experiment adds its own 37-byte prefix plus the
complete native outer stream; all 36 tested cases rejected it as larger.

Encoder and decoder interface (local environment, not a portable installer):

```sh
.venv/bin/python -m benchmarks.backend_retention_round single-encode input.bin selected.cix \
  --profile size --policy docs/research/2026-09-30-codec-profiles/policy.json \
  --receipt encode.json --attempt-directory retained-candidates
.venv/bin/python -m benchmarks.backend_retention_round single-decode selected.cix restored.bin \
  --policy docs/research/2026-09-30-codec-profiles/policy.json --receipt decode.json
```

Decode requires this identified CIX implementation, Python's standard gzip,
bz2 and lzma decoders, the pinned zstd binary when selected, and the pinned
Brotli 1.2.0 runtime when selected. Policy JSON describes installation/runtime
identities and binary location; it supplies no per-input reconstruction data.
Runtime installation paths may change only with corresponding validated policy.
Implementation/library provenance is recorded; the local wheel/binary has not
been independently rebuilt from source. The decoder installation and program
footprint are separate from per-input archive bytes. This is not Hutter package
accounting or a claim of a portable qualification package.

Maximum plans every eligible profile-specific direct reference route before
native candidates. All such direct routes completed in this round. Its global
search cap can still exclude later native trials; every outcome is retained.
Fast/current are not exhaustive. The format supports exact reference payloads,
but these are direct portfolio alternatives, not new CIXG1 substream coders.
