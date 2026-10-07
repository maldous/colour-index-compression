# Independent evidence review: paid record exceptions v1

Review date: 2026-10-03. This is a read-only review of the retained main batch
and its later mechanical boundary supplement. No codec, test or compression job
was rerun for this review.

## Conclusion

The retained evidence supports a bounded experimental result: REX1 exactly
restored all declared inputs, its independently recomputed physical fields
matched the source, and its paid exception representation beat the closest
dictionary control on four fixed noisy synthetic rows. It did not win every
row, and it is not production, streaming or natural-corpus qualification.

No result-integrity blocker was found in the completed artifacts. Final sealing
must still bind the evidence directory and correct the frozen plan's stale
identity and overbroad oracle wording through a historical amendment. Those are
documentation and provenance blockers for a final qualification claim, not
codec failures.

## Main batch identity and counts

- Frozen experiment: `paid-record-exceptions-v1`, freeze SHA-256
  `29991a2251f03e22a04f54cb92b9edaca89d8f12d70c3064b0706bc3af38055e`.
- REX source and retained executed copy:
  `c5924baf9701e8d1114ef46e735722ca752f03dd78223b1ae4e9fd5f1ab56b67`.
- RHC source and retained executed copy:
  `7b1471360c878456d247babde137e85aa6767b8c8e5b3c10a7aea168a1832f07`.
- `results.json`:
  `561cbee1fc1114f57b30f34689325e00a26695bc4c1459719e97af3c188f1847`.
- `malformed.json`:
  `8b7305fb4ebd829ce17008482cd0f977a90b7e3a0eca4667cfd4db40c5cc87cc`.
- Initial work binding:
  `ed1fb16623bb01c1da08b3dcb492d816d1a6bee1bec0456ec030c72334cab3b6`.
- Generated input receipt:
  `6e2477d2f3bf16d41f91b2df97bc9b49f5fe7ab9131fca836e6e9cddc72e455b`.

The nine rows contain **67 newly encoded archives**:

- seven native REX/RHC archives across the three reused-input rows; and
- ten archives for each of the six new rows: REX, histogram, uniform,
  exact-only, record dictionary, four standard compressors and CIX BEST.

Another 21 archive receipts are explicitly reused from the earlier frozen
record experiment: exact-only plus six references on each of three rows. They
are not counted as new encodes or new timings. The eight malformed archives are
also excluded from the 67 successes.

Every one of the 67 new archives has an exit-zero encode, an exit-zero fresh
decoder process, a retained restored file, and a restored SHA-256 equal to the
input SHA-256. All 134 corresponding GNU-time files report exit zero. The
initial artifact binding covers all 150 files present in the work tree at the
end of the main batch; every size and digest matches.

## Independent accounting coverage

The independent Python oracle covers 25 new native archives: all nine REX
archives and the eight histogram plus eight uniform RHC archives that were
applicable. It reconstructs each table or dictionary from source bytes,
recomputes bad positions, colex map rank, dense or histogram payload rank,
literal bytes, bit widths, byte rounding and complete archive size. All 25
complete-byte identities hold.

The oracle does not parse the six new exact-only archives, six new record
dictionary archives, standard compressor archives or CIX archives. Those have
fresh archive-only restoration in this packet. Their implementations or prior
packets may have separate oracle evidence, but that must not be described as a
per-archive independent oracle in this run.

All six generated model-retention gates are true. The development rows selected
`b=6`, `M=8` and `e=0/1/16`; the held rows selected `b=8`, `M=30` and
`e=0/1/16`. This establishes that the input-derived portfolio rediscovered the
predeclared relationship without receiving fixture labels or generator
parameters.

## Physical results

| Row | REX | Histogram | Uniform | RDIC | Exact-only | Finding |
|---|---:|---:|---:|---:|---:|---|
| development b6 e0 | 611 | 623 | 611 | 600 | 600 | REX loses 11 bytes to the clean controls |
| development b6 e1 | 614 | 628 | 646 | 633 | 1080 | REX wins by 14 bytes over the best listed matched noisy control |
| development b6 e16 | 633 | 664 | 800 | 697 | 9240 | REX wins by 31 bytes over histogram and 64 over RDIC |
| held b8 e0 | 978 | 1064 | 1022 | 979 | 967 | exact-only wins; REX carries 11 extra bytes |
| held b8 e1 | 980 | 1069 | 1033 | 988 | 12312 | REX wins by 8 bytes over RDIC |
| held b8 e16 | 1000 | 1127 | 1147 | 1082 | 12312 | REX wins by 82 bytes over RDIC |

The earlier clean `dev-six` row similarly has REX 803 versus exact-only/RDIC
792, an 11-byte loss. On `weak-six`, REX 932 beats RDIC 1049 but loses seven
bytes to the paid histogram control at 925. On `absent`, REX selects its raw
frame at 12,323 bytes while the smallest listed control is zstd at 12,302.

These results distinguish the mechanism from framing: the clean rows expose an
11-byte REX framing disadvantage against the prior exact control; exception
maps and literals become useful on the four noisy synthetic rows; and the
histogram route remains stronger on the older weak fixture. There is no
universal representation win and no natural-data evidence here.

## Malformed coverage

Eight cases exit 1 and leave no decoded output: truncated archive, CRC flip,
`e > r`, invalid map field, invalid payload field, inconsistent exception
length, out-of-range mask and zero histogram count. The non-CRC mutations were
resealed so their semantic checks were reached. The truncation case is detected
through its now-invalid CRC; it is not a separately resealed valid-CRC
truncation. The invalid map and payload values are rejected at rank-padding or
range validation as applicable.

This set is useful but not exhaustive. It does not dynamically exercise every
source-reviewed guard, including all noncanonical dictionary and exception
membership variants. Claims should say eight targeted rejects rather than
complete malformed-input qualification.

## Resource receipts

The main comparison child exited zero after 242.66 seconds. Its actual receipt
records CPU 8, `cpu.max=100000 100000`, 2,147,483,648-byte memory maximum,
zero swap allowance and the transient cgroup path. GNU time reports 108,136
KiB maximum RSS and zero swaps. The scheduler's 123,297,792-byte sampled cgroup
high-water value is explicitly a lower bound. Both compiler invocations and
the fixture phase have separate exit-zero child, cgroup, affinity and time
receipts under the same declared CPU/memory/swap limits.

The codecs read complete bounded files with `take(cap + 1)` and allocate bounded
outputs and rank state. This evidence does not demonstrate streaming behavior,
incremental memory use or inputs above the 16 KiB source cap.

## Mechanical boundary supplement

The supplement is separate verification-only evidence. Its test crate is
exactly the retained REX source, one newline and the frozen test tail. The test
binary was built once and produced seven forced-model archives: empty Raw,
`e=0`, all exceptional, first exceptional, last exceptional, and the adjacent
`r=2048,e=269/270` byte-boundary cases. The native test passed once. It did not
rerun the portfolio encoder or alter the experiment source.

The first verifier attempt correctly remains a failure. The test's relative
path was resolved under the scheduler work directory, producing the retained
nested `benchmark-work/record-exceptions/supplement` path; verifier v1 looked in
the non-nested path and found zero rows. Its source is preserved as
`supplement-verify-v1.py` and matches the v1 freeze's original digest.

Verifier v2 changed only that verification path, used a new freeze, and exited
zero without rebuilding or rerunning the native test. It fresh-decoded all
seven retained archives with the main REX decoder and independently recomputed
their ranks and complete sizes. All seven source, archive and restored digests
match `supplement-results.json` SHA-256
`b8d038408ebbbf9c839ebf50eba1202545f584cbbd2b71e232f039787127bd46`.
The complete sizes are 35, 41, 47, 43, 43, 1048 and 1049 bytes for empty,
e0, e-all, e-first, e-last, e269 and e270 respectively.

The later supplement binding SHA-256
`5edc0300042b1941b75dc154b8faa314c7706a943aa7c4c0f2706d1028b17ff5`
covers all 172 files then present in the work tree, including the supplement
binary and its 21 input/archive/restored files. All entries match and no work
file is omitted. Build, test, failed verifier v1 and successful verifier v2
each retain CPU 8, one-core quota, 2 GiB memory and zero-swap receipts.

## Required amendments before final seal

1. Preserve the frozen `PLAN.md` and state in the final report that its
   `692e...` source SHA is stale; `freeze.json` and the executed source bind
   `c5924baf...`.
2. Correct the plan's general size statement: `r=1536,b=12` would be 18,432
   bytes, above the 16,384-byte cap. The executed new rows are only `b=6/8`
   and are within the cap.
3. Describe RHC as width-matched and sharing its observed dictionary between
   histogram and uniform. Its support is not identical to the REX structural
   table.
4. Narrow “each archive has an independent oracle” to the 25 native REX/RHC
   archives, plus the seven separately labelled supplement archives.
5. State that generator source, seeds and grid were frozen before dispatch,
   while new physical input hashes were captured by the scheduled fixture phase
   before compression. They were not named in the pre-dispatch freeze.
6. Seal the final report, both freezes, both result files, both work bindings,
   all raw command/status/cgroup/time receipts, preserved v1 verifier source and
   this independent review in a final checksum manifest. Preserve the failed v1
   verifier as a failed verification attempt rather than counting it as a codec
   or archive failure.

## Addendum: automatic histogram control

After the review above, root ran a separately frozen automatic histogram
control. This addendum reviews retained artifacts only; it did not rerun the
control.

- `histogram-auto-freeze.json` SHA-256
  `51df39467df412dea936b26d1e07a04ac1af5e7f8d172f13f0bda29e09f9ddba`
  binds the unchanged RHC source/binary, all dependencies, the nine-row input
  packet, the control script and its scheduler. Every bound file still matches.
- `histogram-auto-results.json` SHA-256
  `155068a8300030c46ba0dc58279e37ce0927bd13e6422cba445ddb987670d649`
  contains exactly nine rows.
- `final-artifact-binding.json` SHA-256
  `66cf9399ccb8cf53c1d0489b4374c1113e9fc42dcf39027d9139190dd02cf4b6`
  covers all 190 files now present in the work tree. Every recorded size and
  digest matches, with no current work file omitted and no stale entry.

The control invokes generic `rhc encode INPUT ARCHIVE` without `--width`, so it
searches the frozen width portfolio. This is a selector/control observation,
not an additional sample of the forced-width timing. Each row has one automatic
encode and one fresh decode. All 18 child GNU-time files report exit zero; each
restored file and reported restoration hash equals its input. The independent
RHC oracle recomputes the dictionary, histogram, rank and complete bytes.

On all eight structurally eligible rows, automatic search selected the same
width and observed dictionary as the earlier forced-width control. The complete
archive bytes, SHA-256 and size are exactly equal in every case. On `absent`,
automatic search selected canonical RHC Raw at 12,307 bytes. This strengthens
the control by showing that the forced comparison did not conceal a better RHC
width; it does not create eight additional distinct representations or justify
an average across forced and automatic timings.

The automatic phase exited zero after 1.10 seconds. Its actual receipt records
CPU 8, `cpu.max=100000 100000`, 2,147,483,648-byte memory maximum and zero
swap allowance. GNU time reports 28,796 KiB maximum RSS and zero swaps; the
scheduler reports 0.775536 CPU seconds, a 27,357,184-byte sampled memory
high-water lower bound and 17,755,644 peak temporary bytes.

Across the three successful phases there are now **83 newly created and
verified archive files**: 67 main-batch archives, nine automatic histogram
archives and seven forced-model supplement archives. The 21 historical reused
receipts and eight deliberately malformed archives remain outside that total.
Independent oracle coverage is now 34 main/control archives (the original 25
plus nine automatic controls), plus the separately labelled seven supplement
archives.

The final report has been amended by root to address the review's wording and
scope findings. A repository-level evidence checksum seal remains required
after that report and this addendum reach their final bytes; the 190-entry work
binding does not itself bind documentation or raw scheduler receipts.
