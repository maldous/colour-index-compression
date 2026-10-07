# Independent static review: ERC1 record equality plus counts

**Scope:** read-only review of
`rust/cix-native/experiments/constraint-space/record_counts.rs` and the frozen
pre-execution packet in `record-evidence/`. No build, test, generator, codec or
corpus job was run. The reviewed Rust source and retained executed-source copy
are byte-identical with SHA-256
`1308d501cc253bca64a7431c1eff30cd7dfecd5ea6d3c6bbe5474d65bd6eafa0`.

## Verdict

The ERC1 source has no static correctness or resource blocker for its declared
bounded experiment. The discovered equality mask, per-record count, alphabet,
record width, source length, route and integer width are all serialized. Local
tables and global mixed-radix ranks use exact integer arithmetic. Raw remains
available for every input, while structural candidates require an observed
two-symbol source.

### Resolved preflight findings

The first reviewed scheduler passed `input_bytes=2408` to the shared bounded
runner for the build, fixture-generation and aggregate-control phases. The
runner would have recorded that supplied value as `processed_bytes` and
computed invented throughput. No such phase had a valid 2,408-byte work
quantity: the frozen fixtures total 84,992 source bytes, the build has no codec
input, and the aggregate controls process fixtures repeatedly.

This was caught before the qualified dispatch. The scheduler now passes zero
for these aggregate/non-throughput phases, so the shared runner omits processed
bytes and throughput. Its corrected SHA-256 is
`b5b179da03669b33a9491b5c7829839ac477def7158338e317aa3b41879397cd`.
The updated freeze binds that value.

The original plan also called the local enumeration “at most 4096 masks.” It
enumerates at most 4,096 binary **record values** for one stored mask. The plan
now uses that correct term. Both corrections changed only pre-execution
orchestration/documentation; the reviewed ERC1 source hash is unchanged.

## Local model and exact cardinality

For a stored record width `b`, mask bit `j` requires adjacent bits `j` and
`j+1` to be equal. `local_table` enumerates binary record values in increasing
numeric order and filters them as follows:

* E applies the stored equality mask;
* C requires exactly `h` high-symbol positions; and
* EC applies both restrictions.

The boolean expression in `local_table` implements those three cases. The
table has at most `2^12=4096` entries. Because the decoder now allows either
declared alphabet symbol to be unused by a reconstructed source, these are the
actual accepted local spaces; all-zero and all-one values are not silently
removed. This makes `M=table.len()` exact even for extreme count labels.

`observed` begins with every adjacent equality enabled and clears a bit if any
record violates it. The result is the maximal adjacent-equality mask true in
every aligned record. It separately returns a count only when every record has
the same number of the stored larger symbol. Record phase is fixed at source
offset zero and record width is stored, so no alignment label is hidden.

For the stated six-bit example, a mask equating the first pair leaves five
free bits, so `M_E=32`. Count three gives `M_C=choose(6,3)=20`. Applying both
allows either an equal zero pair plus three ones among the remaining four, or
an equal one pair plus one further one, giving `M_EC=4+4=8`. The positive
cardinality interaction is real. It does not by itself establish a complete
archive or practical win.

Each of `r=n/b` records is independently selected from the same ordered local
table, so the exact global cardinality is `M^r`. The encoder builds

```text
rank = (((digit_0 * M + digit_1) * M + digit_2) ...),
```

making the first record the most significant digit. The decoder extracts
remainders while filling records from `r-1` down to zero, which is the exact
inverse ordering. Remainders are below 4096, so taking the first little-endian
`u32` digit is safe. The Python runner independently rebuilds the ascending
table and the same positional integer from source bytes; it does not call the
Rust rank routine.

The rank width is the bit length of `M^r-1`, exactly
`ceil(log2(M^r))`, with zero bits for a singleton space. The body stores that
integer in `ceil(width/8)` big-endian bytes and validates zero high padding and
`rank < M^r`. No machine-width conversion is used for the global rank.

## Format and complete cost

The fixed layout is correctly counted:

```text
magic 4 + version 1 + mode 1 + source length 4 + record width 1
+ equality mask 2 + count 1 + symbols 2 + rank width 4 = 20 bytes
+ body + CRC-32 4
```

Complete sizes are therefore `24+n` for Raw and
`24+ceil(rank_width/8)` for E, C and EC. The CRC covers the complete header and
body. Body-length validation rejects trailing or truncated payload after a
correctly resealed header. Raw requires zero structural metadata and an exact
`8n` width. All modes physically reserve every header slot, so no parameter is
free.

This common 24-byte frame is a valid complete comparison inside ERC1, but it is
not evidence that a tailored direct representation needs the same overhead.
In particular, the strong fixtures have a small learned record vocabulary. A
direct word/dictionary code can approach the same per-record index width and
remains a required control before attributing a result to an intersection
capability.

`auto` uses complete archive bytes and a strict-less tie rule. It considers
Raw first, then widths 2 through 12 in order, with E, C and EC order within a
width. Forced E, C and EC also choose their smallest applicable complete
archive across that width range. Selected widths must be reported because the
best E, C and EC archives need not be matched at one width. Comparing those
three portfolios is a valid complete-cost screen, but it is not the fixed-model
set-interaction identity unless their descriptions are matched.

The decoder accepts E with a zero mask and equivalent duplicate descriptions,
while the encoder only admits E/EC when it discovers a nonzero equality mask.
This preserves exact decoding and cardinality, but Auto is exhaustive only
over the encoder's declared admitted shortlist, not every syntactically
decodable ERC1 description. The result packet should retain that boundary.
A plain stored two-symbol bit stream and direct learned-word model remain
useful representation controls.

## Corruption and resource bounds

Reads use `take(cap+1)` and reject an extra byte. The archive envelope is
limited to a 20-byte header, at most 16,384 body bytes and four CRC bytes.
Decoded output is at most 16,384 bytes. Structural metadata bounds `b` to
2..12, requires nonempty exact record division, bounds the mask to `b-1` bits,
bounds `h` by `b`, and requires strictly ordered symbols. Mode-specific zeros
prevent a C archive from hiding an equality mask or an E archive from hiding a
count.

Before allocation or indexing, the decoder validates the envelope and CRC.
It enumerates at most 4,096 `u16` values, computes a cardinality with at most
16,384 bits, checks the canonical width and exact body length, and only then
materializes a 16,384-byte maximum output. Width fields have an explicit cap;
the body cap and canonical-width check prevent them from causing a large rank
allocation. Table indexing uses a remainder strictly below `M`.

The prepared malformed matrix includes truncation, CRC corruption and four
CRC-valid semantic mutations. Those cases reach envelope/integrity, record
width, mask, mode and resource-width paths. They are a bounded qualification,
not exhaustive parser fuzzing. The runner must ensure each output path is
absent before a negative decode; a fresh prepared work directory currently
provides that condition.

CRC-32 is accidental-corruption detection, not authentication. A bounded read
can still wait on an open pipe, so the external per-child and aggregate wall
limits remain part of the resource contract. Raw is a selection fallback; it
is not emitted if an external timeout kills Auto before selection completes.

## Frozen evidence review

The source, executed-source copy, runner, generator and scheduler hashes match
the corrected freeze at review time. The current runner SHA-256 is
`799e062f2a319e6efb05259658a6c709036105b6953c218bc80cb9e90671c37d`.
The freeze also binds the separately reviewed RDIC source at
`cc1cf83a91ca0c9945281187be0136ca26d7c5e49237e29b5b8b8d7d1c07dbfb`.
The explicit `rustc --extern` commands bind the two frozen dependency archives.
The reference executable and native CIX library hashes are frozen. The fixture
generator fixes all eight parameter rows before generating any input, writes
all source bytes outside Git, and the input-freeze phase is scheduled before
compression. Development and held-out rows therefore share one frozen source
and grammar.

The batch retains every applicable Raw/E/C/EC/Auto archive, invokes a fresh
Rust decoder, verifies the source hash, independently checks local cardinality
and the selected integer rank in Python, and checks archive CRC. The corrected
packet also builds and runs the separately reviewed RDIC direct learned-record
control, fresh-decodes it, and independently checks its dictionary and sequence
ranks. Conventional reference archives are freshly decoded and their losses
remain in the result. Encoding time for ERC1 and RDIC includes each encoder's
same-process internal round trip; reference encoder times do not, so timings
need that stated scope and should not be treated as a matched speed ranking.

Unsupported and unexpected failed forced modes currently share the summary
label `unsupported_or_failed`. Raw command, exit and stderr receipts permit
later distinction; the final report should make it rather than treating every
nonzero exit as expected inapplicability.

The scheduled resource envelope otherwise matches the plan: one CPU, one-core
quota, 2 GiB memory, zero swap, 64 MiB active temporary space, 120 seconds per
child and 1,800 seconds for the aggregate batch. Root holds the shared
WaveScheduler lock. The experiment remains one observation per cell.

The resolved preflight defects no longer block leased qualification. Any
positive EC result remains an isolated bounded screen. RDIC now supplies the
declared direct learned-record control, while broader dictionary,
matched-width and same-information coder controls remain open. No result would
authorize production integration or a novelty claim.
