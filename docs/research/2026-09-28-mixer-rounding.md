# Symmetric signed learning updates

The incumbent integer mixer floors every signed learning delta. This produces
a systematic downward quantization bias. The separate CIXQ2 experiment rounds
learning deltas symmetrically to the nearest integer (ties away from zero),
while retaining the original exact probability calculation and predictors.

All six 64 KiB prefix frames match the Python reference byte-for-byte and decode
exactly. These are complete diagnostic frames, not corpus scores. The experiment
also passed 36 initial randomized native/Python and round-trip comparisons.
Four-context learning improved Alice 23125 → 20034 and kennedy 6441 → 5299 bytes.
The accompanying JSON contains every result and controls. This supports a new
bounded prerequisite gate; it does not establish a Silesia improvement. The
current frozen floor-rounded mixer trial is retained as the paired baseline.
