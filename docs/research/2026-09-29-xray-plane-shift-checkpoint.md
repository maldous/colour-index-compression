# X-ray PAQ pixel-plane checkpoint

The `paq_image_planes.py` experiment exposes the detected 16-bit X-ray raster
as two self-describing 8-bit PGM grayscale streams.  It transmits the original
metadata, raster bounds, split count, source length and CRC inside `CIXB\x23`;
the decoder reconstructs the original bytes without a source file or saved
prediction trace.

## Completed regional evidence

At PAQ8px v215 `-4`, the three 64-row bands in
`results/leaderboard/paq-image-planes-regions-20260929/complete.json` all
round-trip exactly.  A four-bit low plane is the only tested split with a net
improvement over the same PGM representation without splitting:

| Raster row | Unsplit | 4-bit split | Delta |
| --- | ---: | ---: | ---: |
| 0 | 120,042 B | 119,890 B | -152 B |
| 918 | 128,623 B | 127,531 B | -1,092 B |
| 1,836 | 112,321 B | 112,512 B | +191 B |
| **Total** | **360,986 B** | **359,933 B** | **-1,053 B** |

Six- and eight-bit splits lost on all three aggregate comparisons.  This is a
regional signal only.  It is not a Silesia member result and does not alter
portfolio 26.

## Interrupted full trial

`results/leaderboard/paq-image-planes-full4-20260929/0-0/` contains an
interrupted attempt at the complete X-ray input.  It has no stored frame,
completion record or decoder verification, and must be treated as incomplete.
The attempt was not restarted at this checkpoint because the frozen evidence
baseline owns the shared local measurement lock.  Preserve this directory and
the completed regional frames as an audit trail.

## Next safe gate

After the baseline releases the shared measurement lock, run one bounded,
exclusive-lock full X-ray `shift=4` trial.  Independently decode its stored
frame, compare its physical bytes against the selected 3,531,428-byte X-ray
portfolio member, and integrate it only if it wins.  No size is projected from
the three bands.
