# Full Dickens: ordinary Rust BEST versus the frozen Python record

Two fresh repetitions of each immutable Rust binary ran locally, serially,
through the canonical WaveScheduler on physical CPUs 16–19. The command was
`cix --best --verbose -o ARCHIVE INPUT`; no route, backend, format, block,
memory, thread or external-codec override was supplied. Discovery, rejected
trials, selection and complete framing are included in encoding time and size.
Each archive was restored by a fresh archive-only Rust decoder process.

Input: 10,192,446 bytes; SHA-256
`b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.
The existing verified input was reused; no acquisition or Actions ran.

| Binary source | Complete bytes | Encode wall, mean | Decode wall, mean | Encode CPU, mean | Encode/decode peak RSS, maximum |
|---|---:|---:|---:|---:|---:|
| Old plain native BEST, `ee6b4396df760d19005c4e0800783fef58d52334` | 3,506,669 | 139.775 s | 5.165 s | 463.585 s | 148,484 / 8,148 KiB |
| Qualified automatic archive BEST, `08101079c71a07ef9f268da7058a76802c1dbde3` | **2,799,567** | 144.570 s | 0.365 s | 478.835 s | 170,604 / 19,968 KiB |
| Historical verified Python CIXB1/bzip2-9 | **2,799,567** | Not a matched timing control | Not a matched timing control | — | — |

Both corrected-BEST archives have SHA-256
`b4b0e195209b593a3cf7ee047a1addc2556c70035a3fc037b64a44ef3d45c955`:
**byte-identical to the verified Python CIX archive**, not merely the same size.
The result is the existing native-library bzip2-9 payload plus the complete
47-byte CIXB1 envelope. It is a backend/selector coverage repair, not a new
native-model gain. Compared with the old Rust client: 20.1645% fewer bytes,
3.4305% more mean encoding wall time, 14.1507× lower mean decode wall time,
and higher peak encoder/decoder memory. Host load/cache are uncontrolled;
these are local observations, not universal speed claims.

Throughput includes the full search: old/new encoding 0.06954/0.06724 MiB/s;
old/new decoding 1.88195/26.63089 MiB/s. Decode mean CPU is 5.15/0.35 s.

## Selector scope and exclusions

The native CIXG2 candidate completed 7,176 trials over 156 independent blocks
using four workers, with zero native memory/budget skips in both repetitions.
It retained its original 3,506,669-byte PPM archive. Whole-archive selection
evaluated nine complete candidates: raw fallback, native auto, and seven
admitted direct-backend configurations. Costs were:

| Complete candidate | Bytes |
|---|---:|
| gzip fast | 4,585,677 |
| gzip size | 3,854,794 |
| bzip2 size | **2,799,567** |
| XZ preset 6 | 2,831,723 |
| Zstd fast | 10,192,737 |
| Zstd level 3 | 3,667,714 |
| Brotli quality 0 | 4,408,433 |

The ordinary 512 MiB working-memory policy excluded XZ 9e (estimated additional
728,407,734 bytes) and Zstd 22 (703,556,833 bytes). Their exclusions are retained
in stderr; no alternative is silently labeled as those candidates. Automatic
CIXM6 package comparison and new q11/128 MiB dictionary settings remain
experimental. This is not an exhaustive optimization result, a corpus rank,
a Silesia qualification pass or a claim to beat ZPAQ's 2,142,935-byte archive.

## Evidence and reproduction

[Complete measured findings](measured-findings.json),
[immutable comparison summary](comparison-summary.json),
[selector read-back](selector-readback.json), and per-cell manifests/receipts
retain build/binary hashes, exact flags, cgroup budgets and GNU time outputs.
Datasets, binary build snapshots, archives and restored bytes remain outside Git.

The original v1 postprocessor expected `evaluated`/`omissions`; the actual
client emits `candidates_evaluated`/`omitted`. Its original summary conservatively
recorded the line as malformed. The corrected read-back parses the unchanged
logs; it does not alter the original measurements or restoration evidence.
The exact original harness is preserved in `harness/` and the maintained driver
now accepts both field spellings.

For a fresh comparison, copy both separately versioned `cix`/`uncix` binary
pairs and metadata under `benchmark-work/`, then run
`python3 benchmarks/cix_dickens_best_compare.py --help` and supply those paths
with a new `--experiment-prefix`, new `--area`, and `--run`. The driver is a
local measurement orchestrator; both compressors and decoders are native Rust.
The historical Python implementation is not executed.
