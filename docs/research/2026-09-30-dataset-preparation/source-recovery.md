# Source Recovery Notes

All observations below were made on 2026-09-30. They are acquisition facts,
not compression results.

## Silesia — READY

The established local corpus at `benchmark-work/silesia` contains all twelve
publisher-listed original files. Each file was rechecked against the MD5 value
published on the Silesia page; SHA-256 values are emitted in the manifest.
The same corpus is the lzbench input and is referenced in place rather than
copied into `/home/user/cix-datasets`.

## FCBench — in progress

The official repository pins the 33 raw files through Google Drive IDs and
declares their types, dimensions and expected uncompressed byte counts.
`acquire_fcbench.sh` uses those IDs directly, retains raw payloads at
`/home/user/cix-datasets/originals/fcbench`, and checks the declared byte
count before a file is eligible for SHA-256 recording. It makes no endian,
float-format, layout or organization conversion.

One prior interrupted `astro_pt_f64` transfer is retained because its
1,008,685,056 bytes do not equal the published 671,088,640-byte raw size. It
is expressly excluded from READY status and must be replaced by a clean raw
download before FCBench can be called complete.

## Raw Astronomical Image Challenge — BLOCKED

The current official challenge page identifies its data as unsigned 16-bit
big-endian images and links training data to
`https://pratas.github.io/data/data2.zip`. On this date that exact official
URL returned HTTP 404. The challenge page states that test images are held
back, so they are not represented as available public evaluation data. The
page source was retained at `/home/user/cix-datasets/archives/rai-challenge.html`;
no unrelated historic ZIP or synthetic replacement is used.

## Compression Golf — PARTIAL

The pinned public repository supplies `data.json.gz`, which has been retained
unchanged and independently gzip-tested. A separately extracted JSONL file is
kept for record-oriented harness compatibility. No official evaluation asset
appeared in the pinned repository; it remains NOT_RELEASED rather than being
approximated from third-party GitHub event feeds.

## GDCC — BLOCKED

The relevant edition is the 4th Global Data Compression Competition, whose
rules cover Parquet recompression, AI checkpoint matrices and JPEG
recompression. The rules describe public examples as distributed through an
official VM, while scoring data are private. No resolvable direct input/VM
URL was available from the reachable official rules source. A reported public
VM package has a multi-tens-of-GiB footprint; retaining it and extracting a
VM with only the current free-space margin would violate the acquisition
safety reserve. No hidden scoring input or substitute sample has been added.
