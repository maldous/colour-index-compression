# Histogram reuse: single-run results

Status: VERIFIED_SINGLE_SCREEN. This is an experimental metadata representation, not a production CIX format or selector update.

| Opportunity | Original complete bytes | Reuse complete bytes | Difference |
|---|---:|---:|---:|
| Identical histograms | 8,570 | 8,237 | −333 (−3.89%) |
| Eight repeated pairs | 8,568 | 8,410 | −158 (−1.84%) |
| All distinct | 8,561 | 8,603 | +42 (+0.49%) |

All eight previously frozen native coder/order archives also saved exactly 333 bytes. Each of the 11 configurations was packed and unpacked once, with byte-identical native archive reconstruction and a fresh-process archive-only decode matching its frozen input SHA. This uses the same sealed native rank implementation in a separate process; it is not an independently implemented decoder. No historical baseline encoding was rerun.

The saved bits come solely from histogram metadata. Sequence bytes, rank/range mode, arithmetic termination and original tile-length varints are unchanged. With 15 references, 375 prefix bytes are avoided; 42 bytes of tags, wrapper/count and CRC overhead give the net 333-byte win. With eight references, 200 avoided bytes minus42 give158. Without references all42 bytes are a loss. Prefix boundaries are computed with exact BigUint binomial widths; no ranks are truncated.

Six malformed cases rejected with exit1 and no output: bad envelope CRC, invalid tag, out-of-range reference, truncated body, trailing body, and reconstructed native CRC mismatch. All body mutations have a recomputed envelope CRC to reach the actual parser checks.

Measurements are single-run GNU Time observations. Pack time rounds to 0.00s at its precision; it is not zero-cost and cannot support a throughput claim. Unpack includes native rank verification. Per-row wall/CPU/RSS and raw receipts are retained. Batch elapsed inside driver was0.389s. CPU20/quota100%,768MiB/no swap,1MiB temp limit; retained run files512,733B. Actual resource readbacks and supervisor high-water are in results.json/raw.

The first setup attempt built successfully but stopped before any timed pack/unpack row: conditional-cost-v1 accounting assumes the frozen505-byte exact-rank sequence and rejects varying counts. Its source/receipts/freeze/binding/scripts remain in raw/. The amended driver adds bounded decode-source using the existing generic native decoder; v2 had separate build/run directories and no repeated row measurements.

Remaining gates: no production archive size claim, no CCA/held-out replication, no bounded-streaming integration. Current prototype is bounded to1MiB archives/1024 tiles, buffers each archive and maintains a bounded header dictionary. Its linear dictionary search may need measurement at larger tile counts. A production candidate must pay version/signalling overhead, retain raw/incumbent fallback, reject absent-opportunity expansion, and preserve decoder compatibility.
