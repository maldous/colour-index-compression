# Exact bounded PPM/mixer block portfolio

CIXT1 preserves the bounded PPM policy: 256 KiB top-level blocks, 64 KiB prior
history, orders 3/5/7 and raw fallback. Each block additionally competes with a
complete rounded-mixer CIXR2 representation (64 KiB mixer subblocks). Candidate
choice uses physical bytes including selectors and nested framing. The new
five-byte magic has the same size as CIXP2; unchanged PPM choices retain identical
payload sizes and varint overhead. Since decoded history is input-derived,
choice does not alter future PPM candidates. Thus this exact portfolio cannot
increase physical size over bounded PPM at the same block size.

The decoder handles all three modes, nested length validation, exact block
lengths, stream checksum and trailing-byte rejection. Five focused tests passed
in 3.81 seconds, including an explicit winning-mixer branch, round trips,
physical nonregression against PPM, truncation and trailing bytes. A complete
29-member prerequisite run is active with four local workers, frozen source and
binary hashes, and independent Python decoding before each result is recorded.
No new Silesia rank is claimed. Canonical CIX and its active cohort are unchanged.
