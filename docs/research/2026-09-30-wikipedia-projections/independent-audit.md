# Independent audit — frozen projection path

**Format audit passed; all six completed real projections are large, size-rejected and reconstruction-unverified losses.** No encoding or decoding was repeated for this audit.

The frozen adapter (`f9b5ffd`) stores raw and projected lengths in `CIXPROJ1`, then passes the complete projection frame to CIXV1 mode 5 and lossless JPEG XL effort 9. It pays 29 bytes of outer header and 37 bytes of fixed metadata. The CIXV1 frame pays dimensions, CRC, metadata and JXL payload. P1/P3 pay their BWT primary index; P3 pays all eight wavelet zero counts; all recipes pay plane padding through their exact framed length and raster extent.

The code has no portfolio selector, detector, external dictionary, trained state, or PAQ invocation. P2’s 257 recency lists initialize locally per frame. The frozen runtime/source hashes match the freeze manifest; completed receipts ran the runtime integrity check on both encode and archive-only decode.

| Fixed 4 MiB input | Recipe | Complete CIXPROJ1 bytes | Delta vs verified raw PAQ | Decode status |
| --- | --- | ---: | ---: | --- |
| Offset 0; PAQ control 799,638 B | P1 — BWT + MTF planes | 2,216,487 | +1,416,849 | size-rejected, reconstruction unverified |
| Offset 0; PAQ control 799,638 B | P2 — causal rank planes | 3,346,456 | +2,546,818 | size-rejected, reconstruction unverified |
| Offset 0; PAQ control 799,638 B | P3 — BWT + wavelet planes | 2,223,524 | +1,423,886 | size-rejected, reconstruction unverified |
| Offset 400,000,000; PAQ control 720,368 B | P1 — BWT + MTF planes | 2,135,528 | +1,415,160 | size-rejected, reconstruction unverified |
| Offset 400,000,000; PAQ control 720,368 B | P2 — causal rank planes | 3,328,507 | +2,608,139 | size-rejected, reconstruction unverified |
| Offset 400,000,000; PAQ control 720,368 B | P3 — BWT + wavelet planes | 2,140,617 | +1,420,249 | size-rejected, reconstruction unverified |

The size gate had already rehashed the matching PAQ control and verified its archive-only restoration. Each projection archive was independently rehashed here and its header/inner physical-size conservation checked. The candidates are reconstruction-unverified because decoding was deliberately skipped after the physical size gate; none can be treated as a win.

The three synthetic recipes did complete independent archive-only SHA-256 restoration on the 37,253-byte deterministic fixture: P1 2,519 B, P2 17,091 B and P3 3,750 B. This validates the current adapter’s round-trip path; it is not a real-data compression result.

The initial audit cutoff preceded the offset-400 MiB terminals; this amendment covers them using the same frozen source and no reruns. Holdout and larger scaling cells remain absent. No full-enwik9, Hutter package, score or eligibility claim follows.

Detailed machine evidence: [independent-audit.json](independent-audit.json).
