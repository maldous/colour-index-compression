# Paragraph/unit readback audit

**Status: PASS WITH LIMITATIONS.** The completed small unit archives are self-contained and independently rehashed, but both 4 MiB census-target cells were still running when this audit was made. This is not a compression-result report for that target.

The representation writes a versioned frame containing the mode, original length, exact rule bytes, the full skeleton dictionary, ordered descriptors, every replacement hole, and every literal exception. Decoding starts from the PAQ-restored frame only. It does not consult the source XML, a Wikipedia corpus, a sidecar dictionary, or an encoder-created index.

Every complete archive has the paid outer layout `29-byte header + 35-byte fixed metadata + PAQ payload`. The frame's rules, dictionary, descriptor, family ordering, hole counts, hole bytes, and literal fallback are inside that PAQ payload; they are paid once, never added again as an estimate.

| Synthetic fixture, 37,253 bytes | Complete archive | Delta vs matched original | Readback |
| --- | ---: | ---: | --- |
| Original-byte PAQ | 350 B | 0 B | exact SHA-256 |
| Paragraph-16384 units | 465 B | +115 B | exact SHA-256 |
| Line-4096 units | 464 B | +114 B | exact SHA-256 |

The two unit frames were physically accounted before PAQ as follows: paragraph `9 B framing + 120 B rules + 842 B dictionary + 5,017 B descriptor = 5,988 B`; line `9 + 123 + 843 + 4,977 = 5,952 B`. Descriptor costs include unit order/references, holes and literal material.

All three native receipts record an independent archive-only decode, with the original source and materialized input unavailable to the decoder. This audit independently rehashed every completed archive and restored output. The fixture hash is `dece3fc9570a1ff1288f2259bb004d013959170c0c387dedd28db66fd4c1ad26`.

The frozen real target is offset 520,093,696, length 4,194,304, SHA-256 `4654a742afe2e96d7963851983d6c023ed8f9aa4a4a037f3d32cbe4f2197b083`; this audit independently rehashed the source range. Its raw control and paragraph candidate use the same pinned PAQ v216 binary (`4fd7…182cc`), `-4 -simd AVX2`, `candidate.source.bin`, empty reset state, and equal outer framing. They remain running, so no target size or readback claim is made here.

The transform’s `<text...>...</text>` and line/blank-line recognition is an encoder-side, reversible structure representation. It has literal fallback for incomplete, irregular, and unselected bytes. A result on this selected census-rich region would be targeted-real evidence only; it would not establish representative performance, holdout performance, full-enwik9 gain, a Hutter score, or Prize eligibility.

Raw evidence: [JSON audit](paragraph-readback-audit.json), [original receipt](runs/units-1cfc4625a9ee0230f8f3c9d2/3036a22ad5c4be3f82fc801bee470577715687b806263b0d2e53f207e00d4bfb/receipt.json), [paragraph receipt](runs/units-25c257ba270e84f8fac09318/711fc892bc53a9a94f3146d6d2dad7fd072153fe82ce41ceb7bb2afe091d1a5a/receipt.json), and [line receipt](runs/units-2b71b307364060779ef691f0/a1a0b8c1bbbf4e7e1f8a36300c927ae3ec467a01a969e1e06c58d688d0e359af/receipt.json).
