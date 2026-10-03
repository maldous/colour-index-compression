# Word palette v2

Status: prepared only. No compilation, test, benchmark, or measurement has run.

WPV2 is a separate buffered experiment at
`rust/cix-native/experiments/word-palette-v2/main.rs`. It is not in Cargo and
does not change a production selector, CIXG1, CIXM6, or any existing experiment.

For a chosen fixed width of 2, 4, or 8 bytes, `palette` reads little-endian
unsigned words, counts exact bit patterns, and serializes the 16 most frequent
words. Equal counts sort by unsigned word value. Each word emits a five-bit
index 0–15; index 16 carries an escaped raw word. The remaining 0–7 bytes are
stored as the raw tail. This preserves every bit pattern, including floating
NaNs and `u64::MAX`, without interpreting numbers as floats.

The outer `WPV2` archive stores backend ID, original length, instruction
length, payload length, and a CRC-32 over every instruction and payload byte.
Instructions include variant, width, dictionary cardinality, word count, index
stream length, exception count, and tail length. The decoder reconstructs from
the archive and supplied `uncix` only. It never receives the input, palette
search, model, or encoder state.

Both `identity` and `palette` always perform one CIXG1 FAST encode with the
fixed `benchmark-work/ptt5-fixed-8439/final/{cix,uncix}` pair. A raw fallback
is fully framed and reported separately. The matched decision column is
`complete_cixg1_bytes`, which includes WPV2 framing, instructions, the complete
nested CIXG1 archive, and all backend overhead. The representation is never
pruned before that nested encode because a larger intermediate can still give a
smaller final CIXG1 archive.

The pre-execution scope is six rows: strong, weak, and absent fixtures at
width 8, each with one identity control and one palette trial. Each row is
measured once; there are no averages. This is a finite fixed scope, not a
Cartesian sweep. GNU `time -v` records one native encode and one native decode
per row. Root must first grant a scheduler lease and bind the immutable binaries.

Example after that lease:

```sh
/tmp/wpv2 generate strong /tmp/wpv2-strong.bin
/tmp/wpv2 encode identity 8 /tmp/wpv2-strong.bin /tmp/identity.wpv2 /tmp/identity.json benchmark-work/ptt5-fixed-8439/final/cix benchmark-work/ptt5-fixed-8439/final/uncix
/tmp/wpv2 encode palette 8 /tmp/wpv2-strong.bin /tmp/palette.wpv2 /tmp/palette.json benchmark-work/ptt5-fixed-8439/final/cix benchmark-work/ptt5-fixed-8439/final/uncix
```

The driver persists a `*.wpv2.cixg1` outer native candidate before selecting a
saved archive between CIXG1 and raw. It launches a fresh `wpv2 decode` process
for that native candidate on every row, including when raw wins selection, then
separately fresh-decodes the selected archive. The report records both statuses.
Each decode validates the outer source length against `width × word_count +
tail` before extracting any words; native decoded output has an exact file-size
limit and is checked by metadata before it is read.
