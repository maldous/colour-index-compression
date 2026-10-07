# Census-target paragraph readback audit

**Verified negative result:** the paid paragraph-16384 representation produced a **166,476-byte** complete archive, **7,680 bytes (4.836%) larger** than the matched raw-PAQ control at **158,796 bytes**. Both independently restored the exact 4 MiB source SHA-256 through the native archive-only decode boundary.

The frozen source is enwik9 offset 520,093,696, length 4,194,304, SHA-256 `4654a742afe2e96d7963851983d6c023ed8f9aa4a4a037f3d32cbe4f2197b083`. It is a structurally selected, targeted-real census/body-family region. It is neither a probabilistic representative sample nor an untouched holdout.

| Candidate | Complete bytes | PAQ payload | Delta vs raw | Archive-only readback |
| --- | ---: | ---: | ---: | --- |
| Raw original-byte PAQ | 158,796 | 158,732 | 0 B | exact SHA-256 |
| Paragraph-16384 | 166,476 | 166,412 | +7,680 B | exact SHA-256 |

Both used the same pinned PAQ v216 binary SHA-256 `4fd7b3e768917a665ee4b91c6df3af1d22f540f7ff5beefe7fec689a8db182cc`, `-4 -simd AVX2`, `candidate.source.bin`, empty predictor state, and 29-byte `CIXWUNT1` header plus 35-byte fixed metadata. The only configuration difference was representation mode.

Paragraph’s 2,473,631-byte pre-PAQ frame has fully paid accounting: 10 B framing, 120 B rules, 26,317 B dictionary, and 2,447,184 B ordered descriptor. The descriptor includes 6,737 member references, every hole and every literal fallback. Those bytes are compressed inside the PAQ payload and are not counted a second time outside it.

| Measured resource field | Raw | Paragraph |
| --- | ---: | ---: |
| Encode wall time | 377.398 s | 364.904 s |
| Decode wall time | 376.778 s | 366.907 s |
| Encode sampled cgroup high-water | 511,393,792 B | 850,337,792 B |
| Decode sampled cgroup high-water | 504,983,552 B | 822,243,328 B |

The cgroup values are sampled lower bounds, not true process peak RSS. The timings arose on separate pinned core lanes and are not a general speed ranking.

This rejects this paragraph configuration for this target. It does not reject the separate line-boundary hypothesis, which has its own frozen cell and must complete with its own physical archive and readback evidence. No full-enwik9, Hutter score, package-size, or Prize-eligibility claim follows.

Evidence: [machine-readable audit](census-readback-audit.json), [raw receipt](runs/units-b2c44e27547dae66f8a879f7/803ec09cc0c8fc28e3920d352e44effcafa924f49dcf1f04212fdbcfcd99ebf8/receipt.json), [paragraph receipt](runs/units-fbe31e95ef72db0bc181a57b/5ee5193b34eb980c254bf720fcb5f33b09f94044ab1dff85490f513912e792d7/receipt.json).
