# ERC1 automatically discovered equality/count intersection — freeze v1

Hypothesis: a compact local equality rule combined with a fixed per-record
composition can reduce complete size relative to either model alone, possibly
beating strong established controls. This is a finite-state/enumerative
integration experiment, not a new coding principle. Direct dictionary and
same-information coder controls are required before attributing any practical
win to a new capability.

The encoder scans all widths2..12 dividing the input length. For each width
it discovers adjacent positional equalities true in every record and checks
whether every record has the same count of the larger of two observed symbols.
No width, equality mask, count, alphabet or selected route is supplied from
fixture names. Any other alphabet keeps the arbitrary-byte raw fallback.
Candidate sets and tie order are frozen before observing results.

Each record's admissible set is enumerated exactly, at most4096 binary record values. With
local size M and r records, global COUNT is M^r, and mixed-radix rank/unrank
uses arbitrary-precision integers. The whole solution space is never enumerated.
This proves practical tractability for the explicitly bounded record family,
not closure for arbitrary constraints.

ERC1 has a fixed20-byte header plus4-byte CRC: magic/version/mode/source
length/record width/equality mask/count/two symbols/rank-bit width. It stores
the exact integer rank in big-endian bytes with validated zero high padding.
Raw stores source bytes. E uses equality only, C counts only, EC both. All
fields are physically paid in every mode; this common header is not claimed
as optimal framing. The decoder does no model search.

Frozen generator defines three development, two held-out and three
weak/absent/empty controls in `fixtures.py`. Seeds, relationships, byte-value
pairs and sizes are fixed before any development execution. A separate leased
preparation phase writes input bytes outside Git and seals their hashes before
any compression. The source/grammar is unchanged for held-out runs.

Emit raw/E/C/EC/auto physical archives and fresh decoder restorations for every
applicable mode. Unsupported forced models are reported explicitly; auto
retains raw. Independently check local cardinality and every selected rank
with the Python integer oracle, not a Python codec. Discovery and internal
round-trip checking are included in experimental encoding time.

L0 is the smallest verified output among zstd19/thread1, xz9e/thread1,
bzip2-9, gzip-n-9, frozen native Rust CIX BEST/thread1/memory1536MiB,
and the direct learned-record dictionary control RDIC. The conventional-only
minimum is also retained separately. RDIC pays a combinadic dictionary rank
and mixed-radix record sequence, plus its complete19-byte framing.
Keep all results, not just the smallest. Exact versions/hashes are recorded;
all decode in a fresh process. Complete formats are compared directly; original
filename and framing conventions in references are disclosed, not subtracted.
This is a declared reference set, not an exhaustive global codec optimum.

Report `Ginteraction=min(LE,LC)-LEC`, `LE+LC-LEC-L0`, and `Delta=L0-LEC`.
The strict emergence test is `LE>=L0 && LC>=L0 && LEC<L0`. E, C and EC
each optimise their allowed dimension over the same frozen width range;
record selected widths so a cost result is not confused with a matched fixed
model ablation. No gain against the control is claimed if it is unqualified.

One physical CPU8/quota1, at most2GiB cgroup memory, swap0,64MiB active
temporary allowance; root holds the existing shared WaveScheduler lock.
Encode/decode subprocess timeout120s, overall batch1800s. Threaded controls
use one thread. One observation per cell, no averages. Stop on verification
failure, not a temporary size threshold. No full corpus, acquisition, Actions
or production integration. Strong-control/direct-model gaps keep the six-gate
status open even if an initial size win appears.
