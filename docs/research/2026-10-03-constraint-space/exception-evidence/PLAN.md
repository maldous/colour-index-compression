# Exception evidence grid

Pre-execution frozen plan. Root owns scheduling, freeze bindings and result sealing. This
is a fixed maximum-nine-cell screen using native exception encode/decode and
the wire format supplied by `model_wire_native` (current source SHA
`692e54070cda8f5049408d3bd4cff48d3a25766987a0f670363930144ffcbe4b`).

Inputs use `r=1536` records and `b2..12 (new grids b6/b8)`, so source bytes are at most 16 KiB.
Reuse existing weak-six and clean dev-six only after their hashes are bound.
New fixtures are b6 seed401 and held-out b8 seed403. For each applicable new
fixture, draw uniformly from half-count + first-pair-equality words, then flip the first symbol of exactly `e=0,1,16` records at deterministic distinct positions;
an existing original absent control may be reused. No alignment, map or rule
is selected from fixture identity by the encoder.

Each cell records complete ERC+RDIC bytes, exact map integers/positions,
uniform and nonuniform histogram controls, raw fallback, and strongest sealed
CIXD3 BEST reference. It additionally records pinned zstd-19, xz-9e,
bzip2-9 and gzip-9 archives as external references. One observation per cell;
the complete batch wall budget is 720 s. Root dispatches only through the
global WaveScheduler.

Each archive is parsed after encoding, decoded in a fresh process, SHA-256
checked, and checked by an independent small truth-set/rank oracle. Malformed
cases are invalid map, invalid rank, invalid exception length, and CRC error;
all must reject. GNU time CPU/RSS receipts, command/source/binary hashes and
archive sizes are written atomically per cell.

The source decoder receives no generator rule. Original word bytes are mapped
through the stored two-byte alphabet: each exceptional b-byte record costs b
bits, not8b. REX1 fixed header+CRC35B (5model+30other), map/payload/exception
fields separately byte aligned. Histograms are forced at the selected REX
width to ensure the same learned support in both usage modes. External
dictionary/residual explanation is the ordinary zstd LZ+entropy control, not
a new dictionary route. Matched combinadic-dictionary escape wire is not
implemented in this screen and remains a coverage gap.

Before execution root corrected an unused-vector spelling error, removed
inconsistent source SHA notes in favour of freeze.json, and added exact final
wire-size scoring before member rank construction. Impossible empty local
models are skipped. This is certified complete-size pruning: the cardinality
widths and paid fields determine exact output length. Decoder never repeats
discovery. Observed selected width/e are reported separately from generator
parameters, with a retained-generator-model gate; mismatches are not renamed
as successful robustness evidence.
