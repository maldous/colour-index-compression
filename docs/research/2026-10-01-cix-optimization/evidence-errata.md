# Evidence errata

## Dickens dynamic-queue v3 manifest block-size field

The immutable manifest at `runs/zpaq-dickens-v3-dynamic-queue/manifest.json`
and its copied run identity declare `configuration.block_size_bytes: 32768`.
The frozen `encode_command` does not pass `--block-size`; at source commit
`986bbe80eee1daff7ff77739be821a2ede109c37`, BEST defaults to 65,536 bytes
(`MAX_BLOCK`). The recorded 3,506,980-byte archive and its SHA-256 were
produced by the command as written, so their physical result is preserved, but
the manifest's exact-settings field is false.

Do not use this manifest as a 32 KiB matched control or compare it as one.
For descriptive interpretation, the actual setting is the command's implicit
65,536-byte default; this agrees with the result narrative, but the manifest
remains immutable and visibly incorrect. Any reuse requires a new manifest
with explicit `--block-size 65536`, a fresh run identity, and archive/decode
verification.

Found during adversarial manifest audit on 2026-10-01. No input or result was
modified and no new benchmark was run for this erratum.
