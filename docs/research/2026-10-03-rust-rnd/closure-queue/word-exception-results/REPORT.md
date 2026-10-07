# Word-level dictionary/exception finite screen

18 exact rows: strong/weak/absent 8KiB, widths2/4, identity or input-derived dictionary8/16, current6ac CIXG1 FAST backend. One observation per configuration. No averages.

| Control | Width | Identity complete | Dictionary8 complete | Dictionary16 complete |
|---|---:|---:|---:|---:|
| strong | 2 | 273 | 302 | 301 |
| strong | 4 | 273 | 291 | 267 |
| weak | 2 | 1365 | 1419 | 1428 |
| weak | 4 | 1365 | 1401 | 1440 |
| absent | 2 | 8356 | 8561 | 8638 |
| absent | 4 | 8356 | 8491 | 8534 |

The best palette result saves6B on strong width4/dictionary16 versus the same fully framed identity (273→267B). All other strong palettes and every weak/absent palette lose. Absent identity chooses framed raw8261B rather than8356B native. Palette results are experimental representation effects, not production/model/backend wins. Complete CIXG1 frame comparisons above include every dictionary, index, raw exception, tail, instruction, envelope and CRC byte.

All native and selected WEC2 archives restored in fresh archive-only processes; hashes and assertions in the retained batch driver bind the source and archives. Native encoding and decode timing/RSS per row are retained. These sub-centisecond child times include polling/process setup and do not establish a throughput gain. Actual CPU8/quota1/768MiB/no swap readbacks are retained; active runs use2MiB temporary cap, build uses32MiB. Sampled cgroup peaks are lower bounds.

This synthetic screen does not integrate WEC2 into production or establish a plain-CIX improvement: wrapper overhead must be compared against ordinary CIX, then frozen CCA and held-out replication is required. No production selector/Cargo edits or corpus baseline reruns. The dictionary is derived from source byte frequencies, with deterministic ordering; no pretrained dictionary. Word boundaries are explicit experimental width settings, not filename routing.

Independent review: the strong width4/dict16 nested payload is198B versus
204B original native CIXG1. WEC2 complete267B therefore loses63B to the
deployable plain-native204B control: this is a production negative. Do not
promote the6B same-wrapper saving. No malformed-WEC2 checks were run;
header fields lie outside this experimental CRC and padding canonicality is
not enforced. Those remain explicit experimental qualification gaps. The
executing schedule did not assert all preparedfreeze/source/runner hashes
beforelaunch; retained hashes were independently checked and match.
