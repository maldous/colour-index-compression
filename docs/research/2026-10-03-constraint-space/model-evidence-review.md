# Independent evidence review: bounded model descriptions v2

**Review type:** retained evidence and artifact read-back only; no codec,
compression, build, or corpus job was run.  
**Results SHA-256:**
`ba3dbffa7a0f1e06ffca686990b7cb005c20468d794dd212a146ec7963c4f372`  
**Artifact binding SHA-256:**
`89edc7c402e460d8abc67ffb69ef8923c5980fb845ceac2fd1d9cfc1decd2ef1`  
**Malformed-results SHA-256:**
`08466eb5410259ae1d3c2fec933a7d434323f5eaaf83002aca7f7886459ee349`  
**Input freeze SHA-256:**
`a9722e57d63ad3707543d431ee93c4f97e5337a88b3931b1a0087a233b1754d9`  
**Execution freeze SHA-256:**
`9c4f85b9dc48c0e734a7660afafac0ff152d692e352ff6352a3b4a3b0679c6a4`

## Verdict

The retained v2 evidence is internally consistent and has no correctness or
resource-receipt blocker. Independent read-back reproduced every declared
artifact size and hash, every MSL1/MDC1 CRC and physical length, every local
truth set and dense rank integer, every selected size, and every restored
source hash. The source/build/freeze chain resolves to the reviewed v2 source.

The result is negative for the proposed metadata-sharing advantage. Shared
mask references save bytes against the deliberately naive four-byte Flat atom
records on the two new families, but Packed Flat erases that gain: Shared is
one byte larger for both two-atom cases and ties for both three-atom cases. No
selected archive uses Shared.

The four synthetic complete-size wins are real within the frozen comparison,
but they arise from the stronger paid structural state space and its shorter
dense rank. They are not a gain from selector sharing and do not establish a
new model-description theory. The discovery evidence is limited to the fixed
primitive bank and these small synthetic/fixed cases.

## Identity and execution binding

The current source and retained executed copy are byte-identical at SHA-256
`8258d42130bd37a062ae908e3e1de6328d08ed6042cf105786cc31e421d071cd`.
The BDD helper is byte-identical at
`ba90d538f872e6899483d65f5dffc14ab1e1b9cd59c424e9861038dfaa35172a`,
and the MDC helper at
`c9b20f208b77914a265e29da0f43835c0cdef205106c69726689136621a177cc`.
The freeze's runner, generator, schedule, BigUint/traits libraries, standard
codec executables, production CIX binary and native library hashes all matched
the files read during review.

The built experimental binaries recorded by the artifact ledger are:

| Binary | SHA-256 |
|---|---|
| `models` | `dfef63aa91c882566bc2dd98108f81e42305f3f593813c7decf1c25df04f3af2` |
| `mdc` | `0aa707e442e70f68abd7599d4b43d51fa420d5bf03508fb09265d3fbf51d9502` |

The initial v1 stopped at the compiler before fixture or codec execution. Its
failed packet is retained. V2's explicit RLE tuple type fixes that compiler
inference failure without changing the wire. V2 has its own frozen identity.

All 599 artifact-ledger entries exist and independently match both recorded
size and SHA-256. The ledger also binds both built binaries. The 30 reference
records imported for the five earlier cases were not rerun: their archive and
restoration hashes occur in the separately frozen prior artifact ledger, and
their restored hashes equal the current source hashes. The distinction between
those reused records and the 20 newly executed reference archives is preserved.

## Exact counts and reconstruction

The completed packet contains 12 rows: five earlier structured cases, four new
synthetic structured cases, and three Raw applicability controls.

| Evidence class | Verified | Other status |
|---|---:|---:|
| Prescribed candidate frames | 87 | 21 explicitly inapplicable structural routes |
| Automatic discovery frames | 12 | 0 |
| MDC metadata-control frames | 54 | 0 |
| Newly executed complete input references | 20 | 0 |
| Reused prior reference records | 30 | 0 |
| Malformed frames | 0 accepted | 9 rejected |

Thus the accurate new successful-archive count is `87 + 12 + 54 + 20 = 173`.
The 30 imported reference records must not be added to that execution count.

For every verified prescribed frame, independent parsing confirmed:

* MSL1 magic/version/kind, exact source/model lengths and CRC-32;
* Raw literal bytes or the structural `19 + model + rank` size formula;
* the exact ascending member table for Subset, Bitset, RLE, BDD, Flat, Packed
  Flat and Shared;
* `rank_bits = bit_length(M^r - 1)` with arbitrary-size integer arithmetic;
* the complete source sequence's independently recomputed mixed-radix rank;
* byte-identical Auto output to the first minimum-size candidate in declared
  tie order; and
* a retained fresh restoration whose SHA-256 equals the frozen input.

All structural descriptions of a row have the same rank-byte count:
768/943/384/672/1090 bytes for the five earlier rows and
1152/1280/960/1120 bytes for the four new rows. This supports same-state-space
model-description comparisons. It does not give one representation a hidden
rank advantage.

The nine malformed semantic/framing cases all exit one and leave no output:
truncation, CRC corruption, unknown kind, invalid model length, atom-count
overflow, invalid mask, a BDD self-cycle, nonzero Bitset high padding, and an
invalid Shared scope reference. Their retained stderr identifies the intended
rejection class.

## Discovery evidence

Discovery was invoked with only input and output paths. It evaluated 376
complete candidates across the 12 rows. Independent checks confirmed the
reported candidate count from the aligned widths, selected width against the
archive header, selected atoms against the archive's decoded truth table, and
the selected sequence rank against the source.

All nine binary structured rows recover exactly the corresponding prescribed
truth set. All three empty/mono/nonbinary controls select Raw with width zero,
no atoms and candidate count one. The discovery archive alone reconstructs the
source in a fresh process. Some discovered formulas are semantically tighter
but equivalent to the supplied formula, such as odd parity plus count at most
three instead of odd parity plus count at most four.

The retained result records the winning width, atoms, representation, size and
candidate count. It does not retain per-width formulas or sizes for discarded
candidates. Accordingly it proves the winner and complete search execution in
combination with the frozen source/transcript; it is not a per-candidate search
ledger or evidence of primitive synthesis beyond the fixed bank.

## Model-description and input controls

The paid model-byte comparison is:

| Family | Flat | Packed Flat | Shared | Sharing conclusion |
|---|---:|---:|---:|---|
| two-way development | 9 | 7 | 8 | Shared saves 1 vs Flat, loses 1 vs Packed |
| two-way held-out | 9 | 7 | 8 | Shared saves 1 vs Flat, loses 1 vs Packed |
| three-way development | 13 | 10 | 10 | Shared saves 3 vs Flat, ties Packed |
| three-way held-out | 13 | 10 | 10 | Shared saves 3 vs Flat, ties Packed |

On the five earlier rows Shared is also larger than Packed Flat by three or
four model bytes. Selection chooses Subset twice, Bitset once and Packed Flat
six times across the nine structured rows; the controls choose Raw.

Every MDC1 control has a valid outer CRC and exact physical size
`31 + compressed_model + original_rank`. Its embedded MSL header and inner CRC
match the original, the retained extracted bytes match the compressed model,
the decompressed model matches the native model, reconstruction is byte-equal
to the original MSL archive, and the final source restore matches. All 54 are
larger than the selected native MSL1 archive. This says that these tiny models
do not repay these particular wrapper/codec costs; it does not generalize to
larger model metadata.

The new complete results and smallest declared input controls are:

| Case | Complete bytes | Best declared control | Control bytes | Saved bytes |
|---|---:|---|---:|---:|
| upper-parity development | 1178 | CIX BEST | 1441 | 263 |
| upper-parity held-out | 1306 | CIX BEST | 1539 | 233 |
| three-way development | 989 | CIX BEST | 1370 | 381 |
| three-way held-out | 1149 | CIX BEST | 1554 | 405 |

These sources were generated from the tested structural relationships. The
complete wins show that the paid state-space restriction is useful on those
frozen synthetic families. They do not show transfer to unrelated or real
data, and comparison with a descriptor of the same state space isolates only
model bytes, not the value of the stronger model itself.

## Timing and resource scope

For Discovery, `discovery_ns` contains alphabet inspection, width scans,
primitive inference and exact redundancy removal. `portfolioencode_ns` starts
after that work and contains Raw plus all seven complete structural archive
constructions for every eligible width and selection. The JSON's `rank_ns` is
the same coarse portfolio interval. Selected wire/model/cardinality/symbol-rank
fields describe only the winner and are already inside the portfolio interval;
they cannot be summed with it or presented as the total search cost.

Across the nine structured rows, `discovery_ns` ranges from 54,336 to 381,851
ns, while the full portfolio ranges from 6,362,400 to 1,050,886,509 ns. The
four new discovery subprocess wall observations are
1.0680/0.03174/1.0667/0.03171 seconds. The large difference reflects discarded
candidate work and one-shot process costs; there is one observation per cell
and no speed or scaling conclusion is supported.

All four scheduled phases report child/supervisor exit zero, CPU8 affinity,
`cpu.max=100000 100000`, `memory.max=2147483648` and `memory.swap.max=0` from
their actual transient cgroups. The comparison phase records 330.412 s wall,
329.411 s cgroup CPU, GNU maximum RSS 108,228 KiB, sampled cgroup high-water
131,076,096 bytes, and monitored temporary peak 11,754,345 bytes. The sampled
cgroup figure is explicitly a polling lower bound, not the true peak; the
enforced 2 GiB ceiling and zero-swap setting are the defensible resource facts.
Evidence logs were outside the monitored active-work directory as declared.

## Corrections and remaining limits

No source or measurement rerun is required. Before sealing the narrative:

1. `None beats the selected raw model` should say `selected native MSL1
   archive` or `selected uncompressed-model MSL1 archive`; Raw is a distinct
   route and did not win the nine structured rows.
2. The 173 archives were restored with fresh corresponding decoder processes.
   The 20 input controls use their own zstd/xz/bzip2/gzip/CIX decoders; only the
   MSL candidates/discovery/MDC reconstruction end in the model decoder.
3. `summary.csv` currently has an entirely blank `unrank_ns` column. Remove it,
   label it unavailable, or populate it from the retained discovery decoder
   stderr before presenting the table as complete timing data.
4. A final checksum manifest or immutable repository commit must bind the
   derived report, summary and this review. This is a packaging step, not a
   gap in the executed archive evidence.

With those narrative/table corrections and final seal, the v2 packet supports
the bounded exactness, negative sharing result, and synthetic structural wins
stated above. It does not support production integration, general discovery,
novel-theory, unrelated-held-out, or statistical performance claims.
