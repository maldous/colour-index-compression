# ERC1 exact equality/count intersection: measured checkpoint

## Verdict

Two frozen synthetic cases meet the user's strict interaction test against all
six declared, qualified controls. The eight-position development input wins
12 complete bytes; the ten-position held-out input wins59. The six-position
inputs tie the direct dictionary; the four-position input loses4bytes.

This is a useful **engineering combination of established enumerative coding**,
not evidence of a new compression theory. The winning advantage over the
closest direct model is entirely cheaper model metadata, not a better rank
payload or a violation of arithmetic-coding limits. The prototype is isolated,
limited to16KiB inputs, and not a production/streaming CIX change.

## Four complete archive costs

`L0` is the smallest freshly verified archive among the learned-record dictionary
RDIC, zstd1.5.5 -19/thread1, xz5.4.5 -9e/thread1, bzip2 1.0.8 -9,
gzip1.12 -n -9, and frozen native CIX `d3a2cd416` BEST/thread1/1536MiB.
This is the declared control set, not a global optimum over every compressor.
Every figure includes complete headers, model, rank padding and checksum.

| Frozen input | Bytes in | L0 | LE | LC | LEC | min(LE,LC)-LEC | L0-LEC | Strict emergence |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| dev-six | 12288 | 792 | 1304 | 1131 | 792 | 339 | 0 | no |
| dev-eight | 12288 | 979 | 1368 | 1201 | 967 | 234 | 12 | yes |
| dev-four | 12288 | 404 | 792 | 1017 | 408 | 384 | -4 | no |
| held-six | 10752 | 696 | 1144 | 993 | 696 | 297 | 0 | no |
| held-ten | 12800 | 1173 | 1464 | 1301 | 1114 | 187 | 59 | yes |

All five strong cases' L0 winner is RDIC. Both emergence wins use the same
selected width in E/C/EC, so these are also matched-width ablations. The
four-position E-only winner instead chooses width2; it is a portfolio cost,
not a matched-width interaction measurement. All selected labels are retained
in `results.json`.

| Negative/control input | L0 method | L0 bytes | ERC Auto bytes | Auto excess |
|---|---|---:|---:|---:|
| weak-six | record_dictionary | 1049 | 12312 | 11263 |
| absent | zstd19 | 12302 | 12312 | 10 |
| empty | zstd19 | 13 | 24 | 11 |

The weak input breaks a small fraction of record rules. The exact global rule
then becomes unavailable and Auto uses Raw, losing11,263bytes to RDIC. Absent
opportunity costs10extra bytes relative to zstd; empty costs11. The prototype
therefore does **not** qualify as a replacement for the mature production
selector. Unsupported forced routes are explicit, not silently substituted.
All such failures have the expected `no applicable candidate` diagnostic.

## Exact mechanism and automatic discovery

The generic encoder scans divisors2..12, discovers adjacent equalities true in
every aligned record, and independently tests fixed per-record symbol counts.
It does not receive fixture width, mask, count, name, identity or generator
parameters. Two observed byte values are stored; arbitrary bytes retain Raw.
The same frozen grammar runs development and held-out cases without tuning.
For each admitted candidate the archive stores all reconstruction labels.

For a local table of M valid records and r records, COUNT=M^r. The dense rank
is a base-M integer over the ascending local table; inverse remainders recover
records in reverse order. BigUint preserves full precision. Local enumeration
is at most4096record values, not whole-stream enumeration. The finite width
cap is central to tractability; it is not arbitrary constraint closure.

## Where the bits were saved: exact proposition

Suppose every member of a size-M admissible vocabulary within U=2^b possible
records is observed, and both methods choose that width. The sequence rank is
identical under ERC intersection and the direct dictionary. Let

    P = ceil(bit_length(M^r - 1) / 8)
    Q = ceil(bit_length(binomial(U,M) - 1) / 8)

Then, with these actual complete formats,

    LEC = 24 + P
    LD  = 19 + Q + P
    LD - LEC = Q - 5.

**Proof:** both ascending vocabularies define the same ordered set and M-ary
sequence. ERC pays24framing/model bytes; RDIC pays19plus its separately
byte-aligned combinadic dictionary rank of widthQ. Subtraction gives the
claim. This elementary accounting result is established two-part coding,
not a new entropy theorem.

The six-, eight-, and ten-position cases have respectively M=8,30,112.
Their paid dictionary-rank fields are5,17,64bytes, yielding exactly0,12,59
bytes of difference. Their ideal volume interaction per record is respectively
log2(1.25), log2(7/6), and log2(9/8). This is a separate statistic from the
complete-size gain. Joint constraints reduce the state space beyond either
one; compared with a direct code for that *same* joint set, their saving here
is solely its shorter description.

Uniform completion-probability arithmetic coding can describe the same set
at the same ideal rank cost. This experiment therefore cannot establish a
capability unavailable to probabilistic/enumerative models. It demonstrates
why singleton-only selection can miss a useful paid model combination.
See `../record-interaction-theorem.md` for exact repetition thresholds and
prior-art boundaries; its propositions are not presented as novel theorems.

## Qualification and measurements

* 79physical archives: fresh-process decode and exact source SHA-256 match.
* Independent Python integer oracle verifies each selected structured ERC rank
  and RDIC dictionary/sequence rank, without acting as a reference codec.
* A separate complete tiny oracle constructs all104ERC E/C/EC ranks and all24
  RDIC dictionary/sequence combinations and verifies fresh Rust decoding.
* One overfull300-word control verifies RDIC skips an inadmissible dictionary
  while preserving earlier candidates/Raw: 3600inputbytes →455archivebytes.
* Six malformed inputs reject with nonzero status and no output, including
  four correctly resealed semantic mutations. This is not exhaustive fuzzing.
* One observation per cell. Experimental encoding includes discovery, rejected
  trials and internal verification; controls do not share that internal verify.
  Fresh decoding is timed separately. No speed ranking is claimed.

The batch used CPU8, one-core quota, 2GiB memory ceiling, zero swap and64MiB
active temporary ceiling through the existing global WaveScheduler lease.
Batch elapsed360.48s, cgroup CPU359.95s. GNU aggregate maximum RSS119,004KiB;
sampled cgroup high-water135,585,792bytes is a lower bound, not a precise peak.
Observed peak work-directory footprint10,500,749bytes includes both compiled
binaries, inputs, archives and restores. Tiny-oracle work stays under that same
bounded directory. Source/input freezing and builds are separate paid phases.

Per-command CPU/RSS and observed fresh-process call wall times are in
`measurements.json`; raw GNU time logs and hardware/toolchain/version capture
are retained. Many tiny operations are below GNU time's0.01second resolution;
no precise kernel throughput claim is made. Portable rustc1.98.1 `-O`, frozen
num-bigint/num-traits artifacts, and measured codec executable hashes are recorded. Compiler and orchestration
versions/commands are captured; their executables are not all hash-bound.
Aggregate build/generation/batch receipts intentionally have no invented
`processed_bytes` throughput denominator.

## Six-condition assessment

1. **Pass for this bounded family:** two different rule families discovered.
2. **Pass:** paid exact joint representation, raw fallback, stored labels.
3. **Pass at tested scale only:** exact COUNT/RANK/UNRANK within16KiB bound.
4. **Pass within stated checks:** fresh decode, independent tiny all-rank oracle,
   selected full-file rank oracle and six malformed cases.
5. **Pass on two inputs relative to the declared six-control set:**12/59B;
   not a universal or strongest-possible-compressor claim.
6. **Pass for this synthetic family:** frozen b8 discovery win replicates at
   held-out b10 with changed seed, length and byte alphabet. Held-out b6 ties.

These passes establish a narrow qualified mechanism, **not novel theory**,
real-data effectiveness, unrestricted constraints, scalable streaming or
production readiness. No codec/specialized-data integration has occurred.
The prior-art problem remains: finite-state constrained enumeration already
supports these sets, and a suitably compact direct model can reproduce them.

## Next theoretical question

Can automatic discovery find compact *interacting* descriptions whose useful
factors are not individually profitable, while certified factor width keeps
exact prefix counting practical? Equality/count records answer a small known
case. The unresolved contribution would need to improve discovery/compilation
or tractability with a precise distinction from knowledge compilation and
constraint acquisition, then survive direct-model controls on held-out inputs.
Broader constraint families, exception support and streaming remain unqualified;
ordinary CIX optimization stays paused.

## Reproduction

Use `schedule.py` only in a fresh experiment directory/identity: do not overwrite
immutable receipts. Build source and dependency hashes are in `freeze.json`;
inputs come from the frozen synthetic generator, with hashes sealed before
compression. `supplement_schedule.py` binds the measured binaries and tiny
oracle independently in `supplement-freeze.json`. Input/archive bytes remain
outside Git; `artifact-binding.json` records their identities.
