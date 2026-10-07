# Public Dataset Preparation — 2026-09-30

This directory records acquisition-only preparation for the five public
compression opportunities requested on 2026-09-30. The data themselves live
outside the repository at `/home/user/cix-datasets`; only scripts, manifests,
source definitions and documentation are versioned here.

No compression experiment is launched by these tools. Source archives are
preserved before extraction, and converted copies (if a future experiment
needs any) belong under `/home/user/cix-datasets/working`, never beside the
original byte stream.

## Sources and preservation policy

| Opportunity | Authoritative source | Local preservation policy |
|---|---|---|
| Silesia | <https://mattmahoney.net/dc/silesia.html> | Reuse the existing verified 12-file corpus. Do not duplicate it. |
| FCBench | <https://github.com/hpdps-group/FCBench> | Download the 33 raw Google Drive objects declared by the repository. Retain their declared scalar type, shape, byte order and raw organization. |
| Raw Astronomical Image Challenge | <https://pratas.github.io/rai-challenge.html> | Preserve supplied ZIP data when the official link resolves; source samples are unsigned 16-bit big-endian images. |
| Compression Golf | <https://github.com/agavra/compression-golf> | Preserve `data.json.gz` plus a separately extracted JSONL working input. |
| Global Data Compression Competition | <https://gdcc.tech/rules/> | Preserve direct public inputs when available. Do not treat private scoring inputs as public data. |

`fcbench-files.tsv` is transcribed from the official FCBench `scripts/testfiles.cfg`
and `scripts/fcb_res.py` at source commit `aba31b51959e16b78b1ad1c06757248e31a00362`.
The declared byte count is the required raw-size check; FCBench does not
publish per-object cryptographic checksums in that source. The acquisition
tool calculates SHA-256 after a raw object passes its declared byte count.

## Compression Golf reconstruction note

At source commit `b1a5218a6730984f0b52bc293cff12925e2c5e2a`, the supplied
training corpus is `data.json.gz`. The Rust harness parses JSONL records into
`EventKey { id, event_type }` and `EventValue { repo, created_at }`. For the
sorted-codec path it lexically sorts by `EventKey` before compression; other
paths receive the original sequence. Decoding is checked as reconstructed
event records against the expected sequence, so a future experiment must not
claim byte-identical restoration of the original JSON spelling or line order
unless it independently preserves those bytes.

## Manifest generation

Run `tools/build_dataset_manifest.py` from the repository root after an
acquisition batch. It verifies expected byte counts where a source provides
them, calculates SHA-256 for complete working inputs, and writes an auditable
JSON manifest outside Git by default. It does not download, transform or
compress data.
