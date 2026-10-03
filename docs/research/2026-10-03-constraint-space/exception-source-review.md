# Independent review: paid record exceptions and matched histogram control

Review date: 2026-10-03. This review is limited to the isolated experimental
sources and the frozen pre-execution packet. It does not qualify a production
codec or supply performance evidence.

## Reviewed identities

- `record_exceptions.rs`: SHA-256
  `c5924baf9701e8d1114ef46e735722ca752f03dd78223b1ae4e9fd5f1ab56b67`.
- `record_histogram.rs`: SHA-256
  `7b1471360c878456d247babde137e85aa6767b8c8e5b3c10a7aea168a1832f07`.
- The retained `executed-record_exceptions.rs` and
  `executed-record_histogram.rs` copies are byte identical to those sources.
- `freeze.json`: SHA-256
  `29991a2251f03e22a04f54cb92b9edaca89d8f12d70c3064b0706bc3af38055e`.
  At review time, the current plan, fixture generator, runner, independent
  oracle and scheduler each matched the digest recorded in that freeze.

## Source conclusion

No source correctness blocker was found for the declared bounded experiment.
The REX1 source is approved for this experimental screen. The RHC1 source is
approved as a matched learned-dictionary histogram/uniform control. This source
approval is separate from execution and evidence qualification.

REX1 pays a 31-byte header and four-byte CRC. Its five structural-model bytes
are the width, two-byte equality mask, count mode and count parameter; the
remaining 30 framing bytes are also charged. The exception map, good-record
rank and exception literals are separately byte aligned. The map space is
exactly `C(r,e)`, the good-record space is exactly `M^(r-e)`, and every bad
record contributes exactly `b` literal bits. Colexicographic subset rank and
unrank are inverses on the accepted range. Good-record mixed-radix rank and
reverse unrank preserve record order. Exception values are reconstructed in
ascending exceptional-position order and rejected if they belong to the
declared good table.

The new `final_cost` path computes the same three cardinality widths and the
same fixed framing as materialisation. It skips a model only when its exact
complete byte length cannot strictly beat the incumbent. A materialised winner
is checked against that computed length. This is exact cost pruning; it does
not omit a possible strict winner or change the existing strict-tie policy.

RHC1 stores the complete sorted observed word dictionary. Histogram mode also
stores every positive usage count; uniform mode uses the identical dictionary
without that histogram. Its multinomial recurrence, lexicographic histogram
rank/unrank and base-K uniform rank/unrank are exact. Decode rebuilds the
candidate from its output and requires byte equality with the archive, which
enforces dictionary use, counts, padding and the canonical wire form. Forced
width selects the specified eligible structural candidate and has no Raw
fallback, so the two controls can be compared with the same width and observed
dictionary.

Both decoders authenticate the complete pre-CRC archive and enforce source,
archive, width, dictionary, count, field-length, rank-range and padding bounds
before returning output. Reads use `take(cap + 1)`. The declared limits bound
the record count, table size, dictionary size, BigUint rank width and output
allocation. The REX search bank is deterministically derived from input bytes,
has no input name or hash route, and is truncated to 40 model pairs per width.

## Earlier blockers resolved before freeze

- The `counts_modes` spelling error that prevented compilation was corrected.
- Fixtures now serialize binary symbol bytes, so structural routes are actually
  eligible.
- Development and held-out exception fixtures now start in the intended
  half-count plus first-pair-equality family and flip the first symbol of the
  declared distinct records.
- The histogram control accepts an explicit width and the runner uses the REX
  selected width for both histogram and uniform controls.
- Empty structural tables are skipped, Raw width zero is handled, and source
  and build directories are created by the frozen orchestration.

## Qualification blockers and scope limits

1. **Frozen-plan identity correction required.** `PLAN.md` lines 5-6 still
   identify obsolete source SHA
   `692e54070cda8f5049408d3bd4cff48d3a25766987a0f670363930144ffcbe4b`.
   The authoritative freeze correctly binds the executed REX source as
   `c5924baf...`. Preserve the frozen file and record a post-freeze amendment;
   do not silently rewrite pre-execution history.

2. **Frozen-plan bound wording correction required.** `PLAN.md` line 8 says
   `r=1536` and the full `b2..12` range implies at most 16 KiB. At `b=12`, the
   source would be 18,432 bytes and would exceed the 16,384-byte source cap.
   The actual new fixtures use `b=6` and `b=8` (9,216 and 12,288 bytes), so this
   does not invalidate those cells. A result report must state the actual grid
   and avoid the false general bound.

3. **Control-description precision required.** Forcing RHC1 to the selected REX
   width gives histogram and uniform RHC1 the same observed dictionary as each
   other. It does not give them the same model support as the REX equality/count
   table. Results should call this a width-matched learned-dictionary control,
   not identical support across REX and RHC.

4. The malformed runner constructs one out-of-range payload rank by encoding
   `M^(r-e)` into the canonical payload byte count. This is valid only when that
   integer fits the allocated bytes. The frozen fixture chosen at runtime is
   expected to meet that condition, but the constructor is not generic. The
   evidence is qualified only if the completed receipt contains this malformed
   rejection; a constructor overflow is a failed harness run.

5. The runner's timeout exception path does not create a durable per-child
   status and can reference an unassigned `cp`. This fails the batch rather
   than accepting incomplete evidence, so it is not a successful-run integrity
   defect. It limits diagnosis and resumability of a timeout. Negative output
   paths are also assumed absent on a clean run rather than unlinked before
   decode; qualification therefore depends on the retained clean invocation
   and its artifact hashes.

The synthetic screen can establish physical archive sizes and exact restoration
for these fixed rows. It cannot establish production benefit, performance on a
natural corpus, or a new general compression theory. External compressor and
CIX controls need their own restoration and resource receipts; reused controls
remain historical measurements rather than new matched timings.

## Completed execution readback

The frozen batch subsequently completed with child exit zero. This readback is
based on retained files and did not rerun a codec:

- `results.json` SHA-256
  `561cbee1fc1114f57b30f34689325e00a26695bc4c1459719e97af3c188f1847`
  contains all nine declared rows.
- `malformed.json` SHA-256
  `8b7305fb4ebd829ce17008482cd0f977a90b7e3a0eca4667cfd4db40c5cc87cc`
  contains eight rejected cases.
- `artifact-binding.json` SHA-256
  `ed1fb16623bb01c1da08b3dcb492d816d1a6bee1bec0456ec030c72334cab3b6`
  names all 150 files then present below
  `benchmark-work/record-exceptions`; every recorded size and SHA-256 matches,
  with no unlisted file in that tree.
- `input-freeze.json` SHA-256
  `6e2477d2f3bf16d41f91b2df97bc9b49f5fe7ab9131fca836e6e9cddc72e455b`
  contains all nine input records. All input files still match those receipts.

There are 67 newly encoded archives, and every one has an exit-zero encoder,
fresh-process decoder, retained restored file and restored SHA equal to its
source SHA. The 134 encode/decode GNU-time files all report exit zero. Another
21 archive records are explicitly reused from the earlier frozen record packet;
their archive hashes and sizes were checked against that packet rather than
represented as new timings. The work tree also contains the eight deliberately
malformed archives, giving 75 new `.arc` files in total.

Independent Python readback covers all 9 REX1 archives and all 16 applicable
RHC1 archives (eight histogram plus eight uniform). For those 25 archives it
recomputes the table or dictionary, exception positions, map rank, payload or
histogram rank, field widths and complete-byte identity from the source. It
does not independently parse the six new exact-only archives, six new RDIC
archives, external compressors or CIX archives; those controls have fresh exact
restoration only in this packet. Accordingly, the frozen plan's statement that
*each archive* receives the independent truth-set/rank oracle is too broad and
must be narrowed in the final report.

All six generated exception gates retained the predeclared model and selected
the expected `b` and `e`: development `b=6,e=0/1/16` used `M=8`, and held-out
`b=8,e=0/1/16` used `M=30`. The complete REX1 sizes were respectively
611/614/633 and 978/980/1000 bytes. For context, matched RDIC sizes were
600/633/697 and 979/988/1082 bytes. Thus the exception route lost the clean
development row by 11 bytes and the clean held-out row to exact-only by 11
bytes, while it beat RDIC by 19/64 bytes on development `e=1/16` and by 8/82
bytes on held-out `e=1/16`. These are fixed synthetic observations; they do not
turn the fixture family into a natural-data claim.

The malformed set covers truncation, CRC, `e > r`, map rank, payload rank,
exception length, mask metadata and zero histogram count. All eight decoder
processes exited 1, emitted an applicable error and left no output file. The
payload-rank constructor therefore happened to be representable for the chosen
seed and exercised a rejecting decoder path; its generic-constructor limitation
did not invalidate this completed run.

The compare child ran for 242.66 seconds on CPU 8. Its actual cgroup receipt is
`cpuset=8`, `cpu.max=100000 100000`, `memory.max=2147483648`,
`memory.swap.max=0`; GNU time reports 108,136 KiB maximum RSS and zero swaps.
The scheduler's sampled cgroup high-water value is 123,297,792 bytes and is
correctly labelled a lower bound. Both builds and fixture generation have their
own exit-zero child, affinity, quota, memory and no-swap receipts.

## Post-run sealing requirements

- Bind the final report, results, malformed receipts, input freeze, raw child
  receipts, source review and work-artifact manifest in a final checksum
  manifest. `artifact-binding.json` intentionally covers the work tree, not the
  evidence directory itself.
- Disclose that the deterministic generator, seeds, grid and source were frozen
  before dispatch, while the new physical input hashes were captured by the
  scheduled fixture phase immediately before compression. The packet does not
  prove that those generated byte hashes existed in the pre-dispatch freeze.
- Keep `supplement-tail.rs` outside claims for this frozen batch unless it gains
  its own source hash, execution command, resource receipt and artifact binding.
  It was not named by `freeze.json` and is not part of the 67 successful archive
  observations above.
