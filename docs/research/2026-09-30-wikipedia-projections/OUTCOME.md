# Projection batch v1 outcome

All six complete real-data archives exceed their verified, matched original-byte PAQ controls. They are size-rejected and **unverified**: no real-region decode was run after the permitted size gate. All three synthetic complete archives independently decoded exactly. Nothing is promoted.

Frozen implementation commit: `f9b5ffd` (full source/build hashes in every manifest and snapshot). Freeze SHA-256: `d1cc81c737fd72748b797777e5177f181b8804b6dacfadde5bf1fb7844f802b1`. No CIX or backend change occurred between recipes.

| Input | Recipe | PAQ complete bytes | Candidate complete bytes | Delta | Encode s | Memory lower bound, bytes |
|---|---|---:|---:|---:|---:|---:|
| 0 + 4,194,304 | p1 | 799,638 | 2,216,487 | +1,416,849 | 12.489 | 221,409,280 |
| 0 + 4,194,304 | p3 | 799,638 | 2,223,524 | +1,423,886 | 13.790 | 226,095,104 |
| 0 + 4,194,304 | p2 | 799,638 | 3,346,456 | +2,546,818 | 14.711 | 214,478,848 |
| 400000000 + 4,194,304 | p1 | 720,368 | 2,135,528 | +1,415,160 | 12.044 | 221,224,960 |
| 400000000 + 4,194,304 | p3 | 720,368 | 2,140,617 | +1,420,249 | 13.646 | 226,115,584 |
| 400000000 + 4,194,304 | p2 | 720,368 | 3,328,507 | +2,608,139 | 14.673 | 214,552,576 |

Sizes include the projection representation, the 29-byte header, 37-byte metadata, CIXV1 framing, dimensions, checksum, LZMA metadata and JXL payload. CIXV1 mode 5 / lossless JXL effort 9 is the actual path. PAQ is a separate unchanged size control; no fallback or portfolio selector was used.

The memory figures are sampled cgroup high-water lower bounds, not peak process RSS. Each job was limited to one CPU, decimal 3 GB RAM and 1 GB temporary space, without swap, for 300 seconds total. The two-lane dispatcher stayed below the shared four-core/12 GB/4 GB ceiling. Cached PAQ timings were not rerun and are not a matched timing comparison.

The synthetic fixture is 37,253 bytes; its original-byte PAQ archive is 350 bytes. The complete P1/P2/P3 archives are respectively 2,519/17,091/3,750 bytes. Every synthetic archive restored the exact SHA-256 independently. Its older control has two fewer outer-framing bytes, explicitly preserved rather than normalized away.

The separate equal-composition locality diagnostic (120 versus 20,204 bytes) confirms that the selected pipeline responds to arrangement. It does not contradict these Wikipedia losses or establish an advantage over PAQ.

Decision: retain all P1–P3 v1 recipes as negative configurations on these two development inputs. Their observed complete-size order is P1, P3, P2 on both regions. This is not a verified compression ranking, because real-region decoding was skipped. Do not promote these configurations to holdouts or larger inputs.

The next queued research priority is P4, BWT with deterministically delimited context-region tiles, under the same CIX/backend/control policy. It has **not been implemented or run**. A future recipe must pay its boundaries, ordering and tiling instructions, preserve all bytes, use a new immutable projection identity, and explain the representation change. P5/P6 remain untested. This negative batch does not reject all BWT, predictor-rank or projection designs.

No current result establishes a full-enwik9 archive, package size, Hutter score or Prize eligibility. Historical Silesia and bounded count-feedback wins remain separate in [retained-wins.md](retained-wins.md).

Raw sizes, command times, receipt paths, full hashes and costs: [projection-report.json](projection-report.json). The live per-candidate table is [projection-report.md](projection-report.md).
