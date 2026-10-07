# X-ray PAQ pixel-plane checkpoint

The `paq_image_planes.py` experiment exposes the detected 16-bit X-ray raster
as two self-describing 8-bit PGM grayscale streams.  It transmits the original
metadata, raster bounds, split count, source length and CRC inside `CIXB\x23`;
the decoder reconstructs the original bytes without a source file or saved
prediction trace.

## Completed regional evidence

At PAQ8px v215 `-4`, the three 64-row bands in
`results/leaderboard/paq-image-planes-regions-20260929/complete.json` all
round-trip exactly.  The control is the original band bytes with the ordinary
PAQ path; it is deliberately not manufactured as a PGM image.  A four-bit low
plane is the only tested split with a net improvement over that raw control:

| Raster row | Unsplit | 4-bit split | Delta |
| --- | ---: | ---: | ---: |
| 0 | 120,042 B | 119,890 B | -152 B |
| 918 | 128,623 B | 127,531 B | -1,092 B |
| 1,836 | 112,321 B | 112,512 B | +191 B |
| **Total** | **360,986 B** | **359,933 B** | **-1,053 B** |

Six- and eight-bit splits lost on all three aggregate comparisons.  The gain
therefore includes the effect of presenting the two planes as PGM grayscale
images to PAQ's image model, as well as the split itself.  This is a regional
signal only.  It is not a Silesia member result and does not alter portfolio
26.

## Interrupted full trial

`results/leaderboard/paq-image-planes-full4-20260929/0-0/` contains an
interrupted attempt at the complete X-ray input.  It has no stored frame,
completion record or decoder verification, and must be treated as incomplete.
The attempt was not restarted at this checkpoint because the frozen evidence
baseline owns the shared local measurement lock.  Preserve this directory and
the completed regional frames as an audit trail.

## Completed full gate

The bounded exclusive-lock full-member gate completed on 29 September using
PAQ8px v215 `-4`, the four-bit split and the alternate 2,230-pixel raster
orientation.  Its 3,561,735-byte `CIXB\x23` frame restored all 8,474,240 input
bytes with the original SHA-256.  Encoding took 142.289 seconds and decoding
took 141.702 seconds; peak child RSS was 626,944 KiB.  The stored frame hash is
`29d73460de8498473a9c973df5515109cc198deea3befc3f860ff9ae4c441f1b`.

It is **30,307 bytes larger** than portfolio 26's selected 3,531,428-byte X-ray
frame, so it is rejected from the portfolio.  This resolves the regional
signal: at this tested PAQ level, the self-contained PGM-plane representation
does not pay on the complete member.  Preserve the full frame and result as
negative evidence.  It does not rule out a separately justified test with a
different predictor/configuration; it does rule out projecting the regional
v215 `-4` saving into the score.
