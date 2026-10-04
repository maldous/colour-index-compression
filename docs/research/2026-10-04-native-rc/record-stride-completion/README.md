# Record and stride native completion

This implementation receipt covers two CIX-owned, byte-exact primitives.  It
does not admit either primitive to CLI selection or claim fresh compression
results.

`full_engine/record_ordering.rs` now owns the `MYCS1` record-constraint raw
transform and inverse: canonical fixed-record parsing, literal-record flags,
all nine paid columns, dictionary/count metadata, and the pre-existing
remaining-count order codec.  It also owns the `MYCC1` fixed-column refinement
and inverse.  `CIXD01` and `CIXD02` frame helpers remain callback-based; the
full engine must dispatch the declared backend and call these transforms before
either frame can be selected.

`full_engine/strided_values.rs` now owns all four `SAGR1` modes and `CIXS01`
frame primitives for the strictly recognised 28-byte WCSTools grid.  Mode zero
is the paid byte transpose.  Modes one through three retain the historical
quantized IEEE coordinate prediction, signed bit-pattern residues, palettes,
rank/type-class or range payloads, opaque bytes and scales. Header, record
count, zero tail length, transform mode, backend identifier, original length
and CRC are all paid frame data. The decoder checks extent, stream result size,
transform syntax and checksum before it returns bytes. Frame decoding treats
the supplied memory limit as a combined live-buffer cap: it reserves the
declared output plus conservative inverse working space (six output lengths
for record transforms and three for grids), and passes only the
remainder to the backend. Bounded inverses receive the declared output length
before parsing count-driven row or grid arrays. Direct raw helpers retain a
256 MiB hard output cap.

Required full-engine dispatch exports:

- `transform_mysql_record_constraints` / `inverse_mysql_record_constraints`
- `inverse_mysql_record_constraints_with_limit`
- `transform_mysql_fixed_columns` / `inverse_mysql_fixed_columns`
- `inverse_mysql_fixed_columns_with_limit`
- `encode_mysql_record_constraints` / `decode_mysql_record_constraints`
- `encode_mysql_fixed_columns` / `decode_mysql_fixed_columns`
- `transform_wcs_grid_transpose` / `inverse_wcs_grid_transpose`
- `inverse_wcs_grid_transpose_with_limit`
- `encode_wcs_grid_transpose` / `decode_wcs_grid_transpose`
- `transform_wcs_grid_numeric` / `inverse_wcs_grid_numeric`
- `encode_wcs_grid_numeric_frame` / `decode_wcs_grid`
- `inverse_wcs_grid_numeric_with_limit` / `inverse_wcs_grid_with_limit`

Focused tests are embedded beside each primitive.  Root owns the requested
focused Cargo command and qualification record.
