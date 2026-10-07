# Complete floor-rounded bounded mixer prerequisite result

All 29 complete artifacts match their input identities, physical sizes/hashes,
and successful independent Python round-trip records, with one frozen policy.
The comparison portfolio here is original CIX + bounded PPM + larger-window CIX;
it intentionally does not represent the separate unbounded whole-input PPM
experiment. Exact full-stream selection gives:

- Canterbury: 477,343 → 477,343 bytes.
- Calgary: 798,488 → 794,116 bytes (4,372 saved on geo).

Standalone mixer totals are 592,299 and 1,004,407 bytes respectively. Thus it is
a complementary representation, not a replacement. The complete result JSON
retains all 29 rows, including individual Artificial results. This report checks
prior complete decoding records and artifact identities; it does not claim a
second fresh decode of all files. No Silesia result is inferred.

The separate CIXR2 symmetric-rounding variant passed three framing round trips,
including mixed data across a 64 KiB boundary, and rejected nine damaged frames.
Its native/Python equivalence evidence is recorded separately. A new 29-member
prerequisite trial is running with the same block size and context-bank choices.
