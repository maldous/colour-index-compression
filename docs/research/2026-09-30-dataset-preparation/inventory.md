# Acquisition Inventory

Prepared 2026-09-30. These are source-data acquisition and verification
results only; no new compression job ran.

| Opportunity | Status | Verified public inputs | Local path | Missing / limitation |
|---|---|---:|---|---|
| Silesia | READY | 12 / 12 files, 211,938,580 bytes | `/home/user/src/colour-index-compression/benchmark-work/silesia` | None. Existing lzbench-compatible corpus was reused after matching every publisher MD5. |
| FCBench | PARTIAL | 25 / 33 declared raw layouts, 14,335,914,864 bytes | `/home/user/cix-datasets/originals/fcbench` | Seven official database Drive IDs currently reject public-link retrieval. `nyc_taxi2015_f64` is retained but its 713,943,216 bytes do not match the declared 713,711,376-byte layout. |
| Raw Astronomical Image Challenge | BLOCKED | 0 public image files | `/home/user/cix-datasets/archives/rai-challenge.html` | The official training URL returned HTTP 404; evaluation files are withheld by the challenge. No substitute is used. |
| Compression Golf | PARTIAL | 1 supplied training archive plus 1 extracted JSONL, 25,955,328 / 200,727,388 bytes | `/home/user/cix-datasets/archives/compression-golf-data.json.gz`, `/home/user/cix-datasets/originals/compression-golf/data.json` | No official evaluation asset appeared at pinned commit `b1a5218a6730984f0b52bc293cff12925e2c5e2a`. |
| Global Data Compression Competition | BLOCKED | 0 public task inputs | `/home/user/cix-datasets` | Fourth edition public samples are described as VM-distributed. No direct URL could be resolved from the reachable rules source; private scoring data are not public, and safe VM retention/extraction does not fit the current space reserve. |

The external dataset store occupies 18,027,189,430 bytes at this checkpoint.
The reused Silesia tree occupies another 211,938,580 bytes and is deliberately
not copied. The completed raw FCBench objects keep their source dtype, shape,
byte order and file organization exactly as published. Details, hashes and
source IDs are in `dataset-manifest.json`.

## Access and layout notes

- **FCBench:** source commit `aba31b51959e16b78b1ad1c06757248e31a00362`.
  FCBench publishes Google Drive IDs, types, shapes and expected raw sizes; it
  does not provide a per-object cryptographic checksum in that definition.
  Every locally complete source object has a calculated SHA-256 in the
  manifest. The project repository did not state a separate data licence in
  the acquired source tree.
- **RAI:** the specified layout is unsigned 16-bit big-endian image samples;
  dimensions are challenge-specific command-line parameters. There are no
  available image bytes to validate under the current official link.
- **Compression Golf:** repository source is MIT-licensed. The preserved JSONL
  has 1,000,000 records. The compressed supplied archive and extracted stream
  both have SHA-256 values in the manifest; `gzip -t` passed.
- **GDCC:** status refers to the 4th edition, closed 2025-04-15. The three
  covered public-sample task families are Parquet recompression, AI checkpoint
  matrices and JPEG recompression. This inventory does not claim access to
  private evaluation material.
