# Hutter-only current inventory — 2026-09-29

This separates available inputs and small checks from actual Hutter evidence. No
full enwik9 codec run was started.

| Item | Availability / result | Interpretation |
| --- | --- | --- |
| Canonical enwik9 | `/home/user/src/cix-baseline-data/inputs/enwik9`, 1,000,000,000 bytes, SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc` | Available input; no CIX archive or full decode result exists. |
| enwik8 | `/home/user/src/cix-baseline-data/inputs/enwik8`, 100,000,000 bytes | Available development input; no CIX result artifact exists here. |
| text8 | `/home/user/src/cix-baseline-data/inputs/text8`, 100,000,000 bytes | Available development input; no CIX result artifact exists here. |
| Draft smoke | 2,100-byte synthetic input → 61-byte archive → exact 2,100-byte restore | CLI/routing smoke only; not a text-prefix, enwik8, enwik9, or Prize score. |
| Hutter draft | 27 source files, 71,104-byte ZIP | Exact draft inventory only; not counted submission accounting and no project license/public release exists. |
| Silesia portfolio 26 | 25,481,891 bytes across 12 files | Historical only; never a proxy for enwik9 performance. |

Canonical source ZIP acquisition records are retained in frozen evidence:
enwik9.zip is 322,592,222 bytes, SHA-256
`99cdb5ac84392252d3f0912ccedd195bc95bd80cbef3b0cdf2eee4ad9a3b7a51`;
enwik8.zip is 36,445,475 bytes, SHA-256
`547994d9980ebed1288380d652999f38a14fe291a6247c157c3d33d4932534bc`;
text8.zip is 31,344,016 bytes, SHA-256
`a6640522afe85d1963ad56c05b0ede0a0c000dddc9671758a6cc09b7a38e5232`.

No existing enwik8/enwik9/text8 compression measurement was found under this
checkout's `results/` or `benchmark-work/`. Source named for enwik9
preprocessing is third-party/reference source, not local CIX performance proof.
