# Track A feedback accounting erratum

The archived physical frames and the reported `physical_bytes` values are
correct. Their displayed component breakdowns omitted the variable-length field
that stores arithmetic payload bit length. This is framing, not payload. No
compressed artifact, SHA-256, comparison or conclusion changes.

The current encoder reports that field inside `framing_bytes` and exposes it as
`payload_bit_length_varint_bytes`; a test now asserts that component totals equal
physical bytes. The frozen historical source snapshots remain unchanged.

| receipt | affected rows | omitted bytes per row |
| --- | ---: | ---: |
| `track-a-feedback-first-receipt.json` | 8 | 3 |
| `track-a-feedback-holdout-receipt.json` | 4 | 3 |
| `track-a-feedback-1mib-receipt.json` | 2 | 4 |
| `track-a-feedback-8mib-receipt.json` | 2 | 4 |

To reconstruct a corrected historical row, add the listed omitted amount to its
old `framing_bytes`. All other component fields and `physical_bytes` remain
unchanged. The 64 KiB development and holdout differences remain respectively
unchanged because both matched methods incurred the same 3-byte field. The 1 MiB
and 8 MiB differences likewise remain unchanged because both methods incurred
the same 4-byte field.
