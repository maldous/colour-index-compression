# D28 ERR7091247 source investigation

Updated 29 September 2026, 10:29 UTC. This is source-identification work, not a
new compressor configuration or a completed baseline measurement.

The NNLCB website names accession ERR7091247 in FASTQ form and gives
1,926,041,160 bytes. Paper Table 3 additionally gives an alphabet of 32 byte
values. The source links do not supply a prepared-stream hash or an export
command. These published properties are retained without alteration.

| Authoritative representation | Decompressed bytes | Distinct byte values | Result |
| --- | ---: | ---: | --- |
| ENA FASTQ derivative | 1,837,915,117 | See inventory | Published length differs |
| Original submitted FASTQ | 1,805,158,053 | See inventory | Published length differs |
| Current NCBI run-browser FASTQ export | 1,926,041,160 | 31 | Length matches; simplified quality scores differ |
| Default fastq-dump 3.4.1 of normalized full-quality SRA | 1,926,041,160 | 32 | Both published properties match; stronger candidate |

NCBI documents that normalized SRA preserves full quality scores, whereas SRA
Lite provides simplified per-read scores. The toolkit defaults to normalized
SRA. [Official format documentation](https://www.ncbi.nlm.nih.gov/sra/docs/sra-data-formats/).
An immutable local copy is under `sources/ncbi-sra-data-formats.html`.

The normalized SRA source is a pinned public S3 object version, dated January
2022. Its 242,333,315 bytes have SHA-256
`2fe9f63183a778019cf341f511544227cdbc738b690e72fdfc55b8e847430800`.
The official SRA Toolkit 3.4.1 download was checked against its published MD5
and is also pinned by SHA-256. The exact default invocation ran without network
access, with no header template, read filtering, alphabet remapping or content
options. It exported all 8,467,042 spots. No source bytes were invented or
adjusted to achieve a matching length.

Resulting FASTQ SHA-256:
`d2b1baa824dc387a306de2b7d3b5ed0cf48e5a4e060b233ec70057c3f3099f2a`.
Its empirical byte entropy is 3.857312401051319 bits/byte. This calculation is
not the paper's 5.000 bits value, which numerically equals log2(32); it is not a
compression measurement or a substitution for the defined NNLCB CR metric.

The candidate is now reproducible from a pinned source and versioned tool.
Matching length and alphabet alone does not certify historical byte identity.
D28 therefore remains **NOT EXACTLY REPRODUCED** in the qualification matrix.
It does not enter the frozen baseline's NNLCB aggregates or silently replace
another representation. The original frozen schedule remains unchanged.

The next finite diagnostic compares the candidate's gzip -9 size with the
published D28 GZip row, after full SHA-256 reconstruction. It is recorded only
as corroborating/contradictory source evidence. A rounded compressed-size match
would still not be a cryptographic proof of original-input identity. This
diagnostic is excluded from the controlled baseline timing tables.

Evidence:

- `raw/acquire-D28-sra.json`: exact S3 version, download command and source hashes.
- `raw/acquire-sratoolkit341.json`: tool acquisition and verification.
- `raw/prepare-D28-normalized-default.json`: command, binary hash, full output
  length/hash/histogram and completion status.
- `raw/D28-normalized-{help,version}.txt`: identified exporter interface.
- `raw/D28-normalized-{stdout,stderr}.log`: complete preparation output.
- `supplemental/prepare_sra_candidate.py`: preparation implementation.
- `supplemental/check_sra_gzip_fingerprint.py`: bounded follow-up diagnostic.

Both source preparation and diagnostic execution acquire the shared compute
lock; they cannot overlap a timed benchmark or heavy research experiment.
