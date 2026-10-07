# Larger mixer diagnostic and exact native execution

All six 64 KiB mixer streams decoded exactly. Four-context weighting remains
better than global weights on these probes, but only one beats both other full
stream representations:

| 64 KiB prefix | CIX | Bounded PPM | Global mixer | Four-context mixer |
|---|---:|---:|---:|---:|
| Alice | 20125 | 19697 | 25986 | 23125 |
| kennedy | 6800 | 10336 | 7507 | 6441 |
| obj2 | 26603 | 26468 | 31797 | 27239 |

These are prefix diagnostics with full framing, not complete corpus results.
They justify a bounded mixer as a possible complementary candidate, not a
replacement for PPM. No rank is inferred.

The new native cold-start encoder uses the existing integer stretch table and
floor-division semantics, and reuses the exact arithmetic encoder. It supports
only the measured eta=6 and context widths 0/2/4. Fifty-four randomized cases,
three real 4 KiB probes, and one 70,017-byte rescaling/history-boundary case all
match Python output byte-for-byte and decode with the Python implementation.
Probe speedups are not full-corpus speed results. The canonical codec and live
Silesia run remain unchanged.
