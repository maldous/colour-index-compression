# Bounded generic mixer prerequisite trial

CIXR1 uses fixed 64 KiB blocks, exact physical selection between raw bytes and
CIXQ1 global/four-context eta=6 mixers, total-length framing and a CRC32. Every
selected nested frame contains its own decoding metadata. No external history
or source labels enter prediction. Native encoding uses the qualified exact
integer implementation; independent Python decoding verifies each complete
member before its result is saved. Hashes identify the input, all codec sources,
the native binary, and complete physical frame.

Before the corpus trial: four manual round trips (including a block boundary)
and twelve damaged-frame rejections passed. Four focused pytest tests also
passed in 8.05 seconds, covering mixed data across the real 64 KiB boundary and
truncation, corruption and trailing bytes. The full 29-member prerequisite run
is active under four bounded local worker processes. No Silesia claim or new
rank is made until that gate and a subsequent complete trial pass.
