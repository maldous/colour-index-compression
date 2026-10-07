# Bounded PPM-expert mixer portfolio

CIXR5 preserves every candidate from CIXR3 (rounded Q2 and extended Q3,
bank widths 0 and 2) and adds Q5 at the same bank widths. The block size
remains 65,536 bytes. Selection compares complete nested bytes; raw remains
available. The outer magic has the same length, so complete output cannot
grow relative to R3 for the same input. The decoder dispatches on the stored
nested magic and checks length and CRC.

Before starting the 29-member prerequisite gate, five generated inputs passed
independent Python decoding and complete-size nonregression against R3:
empty, one byte, 1,024 periodic bytes, 66,000 random bytes crossing the block
boundary, and 8,192 seven-symbol bytes. Truncation and appended-byte damage
were rejected for every case. Input randomness used fixed seeds 51 and 31.

The gate runs locally with three workers and records source/binary identities,
physical artifacts, SHA-256 hashes and complete Python decode verification.
This is not a Silesia result. The separate larger-input Q5 diagnostic remains
in progress; its first full member (Alice) verified Q3 41,738 bytes, Q5 40,812,
and P2 41,209. No existing live Silesia source was changed.
