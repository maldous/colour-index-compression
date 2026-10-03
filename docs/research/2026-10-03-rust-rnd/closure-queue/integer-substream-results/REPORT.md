# N6 universal integer finite screen

21 one-shot synthetic structural sequences, seven coders each; complete ISC1 header/schema/tags/count/bit lengths/tail/CRC are included. Fresh archive-only restoration passed for every row.

| Control | Varint | Gamma | Delta | Rice0 | Rice2 | Rice4 | Rice8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| strong | 888 | 564 | 556 | 1248 | 1020 | 820 | 852 |
| weak | 632 | 640 | 616 | 1342 | 1057 | 715 | 635 |
| absent | 1014 | 1269 | 1047 | 2386 | 2378 | 2369 | 2181 |

Delta saved332B strong and16B weak versus same-frame unsigned LEB128. Random retained varint: every alternative lost. Rice uses a paid raw-u64 escape when its unary form costs more than65bits, keeping allu64 values bounded and exact; maximum and zero are present in the strong fixture. The equality case keeps regular Rice. This is a universal-integer representation comparison, not a CIX corpus/model/backend or production gain. The original ISIN1 schema/tagged canonical-varint sequence is reconstructed byte-for-byte. No real LZ parse was consumed.

Fixtures were generated once and hash-checked against their predeclared hashes before codec calls. One encoding timing per row includes its built-in fresh verification decoder; a separate newly started decoder is timed once for decoding. Raw GNU-time wall/user/sys/RSS are retained; sub-centisecond time values cannot substantiate fine throughput claims. Root cgroups enforce CPU8/quota1/256MiB/no swap/64MiB active temporary including executable. The declared2MiB retained-run target is separate from build/executable storage; peak sampled cgroup is a lower bound.

CRC corruption, truncation and invalid coder controls returned nonzero without panic or restored output. This is narrow malformed coverage, not full fuzz qualification. Bit coder padding and Rice/varint canonicality are checked in the implementation.

Initial v1 compilation failed before any fixture or codec measurements (11 type/error-conversion failures). It was corrected, formatted and hash-frozen under uniquev2 before any benchmark rows. Failed raw receipt, freeze and launcher are preserved; the exact initial source was not copied before editing, so that failed source is not fully reconstructable from the packet. Executedv2 source bytes are durable in raw/. No averages, replacement codec, corpus baseline or acquisition was used.

Integration with entropy-coded real token/substreams and same-backend framing remains pending before promotion. The synthetic mechanism cell alone is complete.

Independent review verified all21archives,bit lengths/zero padding/CRC, both
restorations and42time logs; no blocking defect. Strong includes32copies of
u64::MAX receiving gamma/delta's one-bit escape instead of80-bit LEB128.
That contributes316B of the332B strong saving; it is a deliberately exposed
boundary/sentinel opportunity, not representative real-LZ evidence. Weak's
16B saving and random's losses are retained. Canonical padding/Rice/LEB checks
are source-reviewed; the three malformed executions do not test each such path.
