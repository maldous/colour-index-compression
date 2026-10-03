# RSL1: frozen twelve-candidate screen

Status: VERIFIED_SINGLE_SCREEN. Existing exposed development input: Kennedy bytes0..8192, SHA970d1bcb1e252abab6a58e1cedb79d2eb03689744fa09f97d2855cdecf8b4216. No encoder dispatch uses its identity.

| Candidate | Complete RSL1 bytes |
|---|---:|
| identity | 2,487 |
| literal | 8,221 |
| transpose-4 | 3,260 |
| mod-delta-1 | 3,204 |
| mod-delta-4 | 4,056 |
| xor-1 | 3,153 |
| xor-4 | 3,692 |
| previous-stride-residual-1 | 3,204 |
| previous-stride-residual-4 | 4,056 |
| transpose-4+mod-delta-4 | 3,555 |
| mod-delta-4+transpose-4 | 3,702 |
| xor-4+transpose-4 | 3,512 |

Identity wins at2,487 bytes, including29 bytes RSL1-v2 framing/operation/CRC. Its unchanged nested CIXG1 archive is2,458 bytes. Therefore this screen establishes **no production size win**. All transforms lose on this input; do not promote them from this screen. Twelve configurations are not twelve distinct methods: previous-stride-residual is the same modular subtraction as delta, and their lag1/4 transformed hashes and archive sizes coincide. The307-program mode remains unexecuted.

All candidates restored exactly using a fresh native uncix process plus in-process inverse. Selected RSL1 got a fresh archive-only Rust driver process with native uncix and frozen original SHA equality. Four malformed selected frames (bad CRC, valid-CRC invalid opcode, body truncation and trailing body) rejected with exit1 and no output. This is fresh-process validation with existing native decoders, not an independent decoder implementation.

One single screen, no averaging. Native encode observations15.57–20.66ms include process/wrapper launch and5ms polling; native decode observations are retained in results/raw. These are not unbiased kernel throughput measurements. Whole batch including12candidate search, transforms, rejected trials, verification and malformed checks was0.303s inside driver; supervisor and GNU-time CPU/RSS are separately recorded. One CPU20 withquota100%,1GiBRAM/noswap,2MiBtemp; actual group peak20,901,888B and retainedfiles296,331B. Transform process memory is measured in parent cgroup despite older binding-row native-only RSS wording.

First build failed before any compression: two Rust compiler type/borrow errors. Original source/freeze and compiler receipts retained inraw. The corrected source SHA b2928b4f96871a196f3b956db3e7bba4dba450d24793288a1de9c326ffd7c373 compiled successfully. No candidate measurement was repeated.

Prototype remains buffered/block-only and experimental. It stores reconstruction instructions; decoding performs no search. Cache/history integration, held-out replication, CCAgate, streaming and production profile/selector changes remain pending. Next implementation-only experiment: bounded exact transformed-byte deduplication can avoid the two proven duplicate native trials while preserving complete metadata costs, candidate order, ties and selected archive bytes.
