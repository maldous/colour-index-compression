# Conditional grid raw-transform completion

`rust/cix-native/src/full_engine/conditional_values.rs` ports the raw `SGCC2`
transform beneath historical `CIXB\x21` (CIXB21). It is not registered as a
CLI route and does not include PAQ framing or backend dispatch.

The implemented parity path is `context=3`, `coding=0`: exact-coordinate
groups, paid frequency-ordered correction palette/IDs, correction feedback,
and the complete paid `grid_interval.encode_integers(policy=2, block=4096)`
selector required by that raw stream. The inverse validates raw magic, context,
coding, record count, every packed field, integer representation and trailing
bytes before reconstructing the existing bounded SAGR1 grid representation.

Its direct parents are retained `record_float_grid` mode 1 (provided by the
native `strided_values` transform), `grid_feedback`, and `grid_interval`.
The implementation duplicates only their raw parsing/selector primitives so
the public SAGR module need not expose internal palette state.

Only raw transform qualification is supplied here. Contexts 0–2 and codings
1–2 are intentionally rejected rather than approximated. CIXB21's PAQ
payload, complete envelope resource accounting, decoder backend selection and
route admission remain full-engine work. The synthetic fixture has repeated
signed coordinates and a nonzero one-ULP correction event; it is not corpus
or performance evidence.
