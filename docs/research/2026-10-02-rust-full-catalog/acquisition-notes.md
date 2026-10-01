# Squash fixture acquisition extension

This record exists because the user explicitly authorized acquisition of four
previously missing Squash catalog fixtures on 2026-10-02. It is a narrow
extension, not a reopening of the closed generic-pipeline acquisition program.
Earlier frozen manifests remain unchanged.

The four files were fetched from the primary Google Snappy `testdata/` tree at
the resolved `1.1.3` commit `efb39e81b8b66b757ec900db33657c47b4750740`.
Each received byte length, Git blob SHA-1 and SHA-256 matches the pinned tree
record. The downloaded files and captured HTTP response headers are stored in
the ignored `benchmark-work/squash-fixtures/` area. Snappy's upstream
`COPYING` blob is `bd0e5971dbf09bd6b3213ea7248383d10f26dea2`; see upstream
for its BSD-style license text.

Existing `enwik8` was not acquired again. The current user authorized only a
read-back: the retained ZIP hashes to the inventory's frozen SHA-256, its sole
`enwik8` member has CRC-32 `81838409` and 100,000,000 uncompressed bytes, and
streaming that member produces the SHA-256 of the existing raw input. No ZIP
member was extracted into a new file.

No enwik9, no additional dataset, and no compression, decompression, build,
test, benchmark, workflow or Site operation was performed for this extension.
