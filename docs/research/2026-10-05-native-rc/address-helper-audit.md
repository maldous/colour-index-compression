# ECOFF call-entry and relocated-pointer helper audit

The historical executable dispatcher imports only `ecoff_got`,
`ecoff_pointer_deltas`, `ecoff_section_pointers`, and
`ecoff_pdata_symbols`.  Its executable wire identities are `CIXB\x03`,
`CIXB\x0b`, `CIXB\x0c`, `CIXB\x1d`, and `CIXB\x13`.  It has no
`CIXB` frame which selects either `ecoff_call_entries` or
`ecoff_relocated_pointers` directly.

`ecoff_relocated_pointers` has the standalone raw trailer `ECRP1`.  It is the
immediate candidate-locator dependency of the supported `ECRD1` pointer-delta
raw transform, carried by `CIXB\x0b`.  Native
`relocated_pointer_candidates` is that locator: it parses `.rel.dyn`, limits
locations to `.rdata`, `.data`, and `.sdata`, derives transmitted-symbol
alphabets and shared definitions, then suppresses overlapping words.  The
result feeds `pointer_delta_process`, which writes and restores `ECRD1`.
There is deliberately no duplicate native `ECRP1` raw transform because it is
not independently reachable through an executable frame.

`ecoff_call_entries` has standalone raw trailer `ECBR2`.  It is used only for
the arithmetic choice codec in `ecoff_section_pointers` models 4 and 5.
Retained native SectionPointers uses historical mode 4, whose reference choice
codec is `ecoff_pointer_deltas.encode_choices`; its raw identity is `ECSP1`
under `CIXB\x0c` and `CIXB\x1d`.  Models 4 and 5 in the call-entry helper are
used only by inactive SectionPointers model 6.  No supported native frame can
emit or decode `ECBR2`.

`generate_ecoff_relation_fixture.py` now asks the reference `ECRD1` transform
for mode 5 on the same synthetic relocation-bearing ECOFF object.  It asserts
at least one mapped pointer and one compact residual, verifies the reference
inverse, and emits `pointer_delta_mode5_hex` for the native byte-parity test.
The frozen v5 receipt records one mapped pointer, one exact prediction, and a
one-byte residual.  Its raw bytes are checked in as
`rust/cix-native/tests/fixtures/address_relations/pointer_delta_mode5.raw` and
the native test checks both exact `ECRD1` bytes and inverse restoration.  The
generator invokes raw transforms only; it does not run a compression backend.
