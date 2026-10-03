# Release 0.1 benchmark inputs and comparison records

This inventory freezes the source inputs for the final release-build measurement. It contains complete local originals only. It deliberately excludes prior archives, build outputs, resumed partial files, transformed streams, and all small research slices.

| Set | Complete inputs | Original bytes | Reporting rule |
| --- | ---: | ---: | --- |
| Canterbury | 11 | 2,810,784 | Aggregate and per-member |
| Calgary canonical | 14 | 3,122,304 | Aggregate and per-member |
| Calgary legacy extras | 4 | 111,871 | Per-member only; excluded from canonical aggregate |
| Canterbury Artificial | 4 | 300,001 | Per-member only |
| Silesia | 12 | 211,938,580 | Aggregate and per-member |
| FCBench ready subset | 25 | 15,049,858,080 | Per-member and domain subtotal |
| Compression Golf training JSONL | 1 | 200,727,388 | Per-input only; nonqualifying |
| Baseline complete inputs | 5 | 2,200,001,548 | Per-input only |
| Stored primary SRA | 1 | 242,333,315 | Per-input stored SRA bytes only |
| Squash fixtures | 4 | 1,046,168 | Per-fixture only |
| Domain-transfer primary inputs | 9 | 2,254,701 | Per-input only; one declared Adult subset |

The largest complete local primary asset is `miranda3d_f32` at 4,294,967,296 bytes. The FCBench manifest has 25 verified READY inputs, seven unavailable database inputs, and one size-mismatched input. Benchmark only the verified set.

Twenty-one files formerly grouped as “baseline source artifacts” are excluded as acquisition containers, tool archives, or duplicates of canonical local inputs. This includes the 26.8 GB downloaded Wikipedia bzip2 stream, `enwik8.zip`, `enwik9.zip`, and `text8.zip`; none has a declared extracted raw-dataset identity in this release inventory. `ERR7091247.sra` alone is retained as a valid stored scientific primary input. Its comparison is strictly against the stored SRA bytes, not extracted FASTQ data.

The complete canonical 1,000,000,000-byte `enwik9` and 100,000,000-byte `enwik8` are present in `cix-baseline-data/inputs`; their locally computed MD5 values match the publisher’s identities. The 6,425-byte Hutter smoke copies are not substitutes. Four full Squash fixtures (`fireworks.jpeg`, `geo.protodata`, `paper-100k.pdf`, and `urls.10K`) are included individually.

The domain-transfer audit also contains nine unique, directly usable primary assets: two complete NOAA monthly water-level CSV responses, three canonical PubChem SDF response batches, an uncompressed NIfTI example, one locally installed ELF binary, a World Bank CSV, and a declared 2,048-row UCI Adult subset. Acquisition containers and redundant PubChem component/inspection files are excluded. These inputs are reported only per input; no result can stand for the full Adult collection, all PubChem, NOAA generally, or a platform-independent ELF corpus.

`local-assets.json` supplies the canonical paths, membership, byte counts, exclusion rules, and the status selector for FCBench. `public-records.json` supplies the external-comparison boundary. Both are inputs to the release benchmark report, not benchmark results.

## Measurement contract

For every eligible input, run the exact release build independently in FAST, DEFAULT, and BEST modes. Each row must record original bytes, compressed bytes, compressed/original percentage, encode wall and CPU time, decode wall and CPU time, peak resident memory or the exact measurement qualification, and SHA-256 proof of fresh restoration. Archive bytes include all CIX framing and metadata.

Do not borrow timing, memory, or sizes from research binaries or previous corpus runs. A failed, timed-out, resource-limited, or unverified mode remains explicit rather than becoming a zero or an estimated value. The report should distinguish archive bytes from ideal-information results and should never aggregate unrelated corpora.

The verified current public archive-byte record in this inventory is Silesia: `paq8px_v217 -12L`, 27,682,006 bytes across the 12 individually compressed official members, as listed by [Matt Mahoney’s Silesia benchmark](https://mattmahoney.net/dc/silesia.html) with a page record date of 29 September 2026. The record includes no directly comparable timing or memory value. The Hutter Prize lists `fx2-cmix-T` at 100,424,672 bytes for `enwik9`, but that is a self-extracting total of compressor plus archive and is not comparable to an ordinary CIX archive. Its final listed `enwik8` entry gives both 15,242,496 archive bytes and 15,284,944 total bytes; the same distinction applies. Canterbury and Calgary have official historical result material but no maintained current complete-byte leader verified here. The Artificial corpus is intentionally not an aggregate competition. FCBench’s publication is an important method reference but has no verified public archive-byte leader for this local 25-file subset.

## Distribution boundary

None of these input bytes, derived archives, source-checkout copies, or benchmark logs belong in the public source distribution. The release repository should contain only the benchmark recipe and any compact, reproducible result tables that do not redistribute corpus data. The FCBench README makes its data available through its listed sources but does not establish a data redistribution licence in the local project record; retain links and provenance rather than copying its inputs. The Compression Golf source repository is MIT-licensed, but that alone does not grant publication of third-party event data beyond its source terms. Corpus licences and publisher terms must remain attached to each acquisition source.
