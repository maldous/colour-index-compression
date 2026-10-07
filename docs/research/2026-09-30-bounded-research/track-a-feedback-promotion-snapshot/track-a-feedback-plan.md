# Track A — paid composition-feedback predictor screen

Predeclared before execution.  The causal predictor routes each successor byte
by the high nibble of its preceding byte and range-codes it with a Laplace
adaptive byte model.  The feedback predictor receives the same causal context,
but first transmits every sparse context successor-count vector and then range
codes using the decoder's evolving exact remaining counts.

This is explicitly not a CIX-rank comparison.  Both residuals use the same
arithmetic implementation; any change must be attributed to the paid count
information, not enumerative rank coding.  Physical metadata includes all 16
256-bit active masks and every positive count, as well as framing, first literal
and checksum.

The screen uses a deterministic synthetic repeat/edit stream plus the same three
64 KiB enwik9 development ranges: offsets 0, 100,000,000 and 400,000,000.  It
does not read the holdouts at 700,000,000 or 850,000,000.  No warm-up is used.
The hard tree wall limit is 300 seconds, CPU is logical 2, RAM is 2 GiB, swap is
zero and temporary disk is 1 GiB.  Promotion requires feedback at least 0.5%
smaller on two development regions plus independent decoder SHA checks.  Any
other outcome rejects this version and preserves the receipt.
