# Volume forward-transfer: bounded real-data plan

This isolated experiment transfers the historic `mr` contribution, selected as
`volume-0-3-10`: region 0, original sample planes, planar lossless JPEG XL,
effort 10. It does not assert that this Silesia-specific result generalises.

The representative input is `nibabel-example4d.nii`, an uncompressed NIfTI-1
test volume from the public nibabel repository. It is the exact gzip-expanded
byte stream from the upstream `example4d.nii.gz`, including its 416-byte header
and all voxel data; neither an image crop nor a pixel-only extraction is used.
The compressed upstream source is retained beside it. The selected data type is
little-endian signed 16-bit, dimensions 128 x 96 x 24 x 2.

The first fixed comparisons are:

| Candidate | Purpose | Backend attribution |
| --- | --- | --- |
| `original` | Matched PAQ control on exact NIfTI bytes | PAQ v216 `-4 -simd AVX2` |
| `plane-stack` | Self-contained metadata + original ordered planes | Same PAQ, representation effect |
| `delta-z` | One neighbouring-slice residual predictor ablation | Same PAQ, prediction effect |
| `jxl-planar3-e10` | Inherited winning mode (not a sweep) | Native JXL only, separate backend |

`plane-stack` and `delta-z` contain their NIfTI header, all pre-/post-voxel
bytes, dimensions, frame kind, CRC and payload. PAQ receives that entire frame.
The original control receives no artificial frame. The JXL candidate is already
a complete self-contained archive and is never additionally PAQ-compressed.

No rank/order coding is forced: the historic `mr` evidence was a spatial
representation plus JXL capacity sharing, rather than proof of a CIX
enumerative-order advantage. A successful physical archive must undergo an
independent archive-only decode before it is evidence. This bounded trial does
not establish a full-corpus, Hutter, Silesia, or generic-compression result.

Initial native-JXL run (before any PAQ comparison): `jxl-planar3-e10` produced
225,932 bytes from 1,180,064 bytes and restored the canonical SHA-256 exactly.
It is useful backend evidence, but no claim about the structural representation
is made until the two matched PAQ archives have completed.
