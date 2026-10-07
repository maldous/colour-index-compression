# Shipping-source naming audit

Scope: read-only review of `rust/cix-native` shipping candidates. This is a
naming review under the user’s explicit naming instruction; it is not a final export allowlist.

## Current full-engine names

The current first-party names are appropriate process/mathematical names and
should be retained:

| Current file | Assessment | Reason |
| --- | --- | --- |
| `src/full_engine/structured_frames.rs` | retain | describes framed structural representations; it does not promise a chemical-only product. |
| `record_ordering.rs` | retain | describes count/rank coding and record ordering, not a database brand or corpus. |
| `address_relations.rs` | retain | describes address/relocation relations; better than `executable` as a route name. |
| `strided_values.rs` | retain | describes value stride/record operations; WCSTools remains an explicit supported-format identifier in code/comments. |
| `volume_lifting.rs` | retain | describes reversible volume/image lifting without making image content a selection claim. |
| `arithmetic.rs`, `graph_residuals.rs` | retain | conventional mathematical/process terms. |

Existing strings such as `chemical`, `executable`, `image`, `grid`, `ECOFF`,
`ELF`, `TAR`, `WCSTools`, `PAQ`, `CIXB`, and `CIXG` should remain where they are
historic wire identifiers, documented standard-format names, compatibility
errors, or third-party provenance. Renaming those would obscure interoperability.

## Other first-party shipping candidates

`src/{adaptive,bitplane,bounded_reader,bsc_ffi,bwt_legacy,chain,combinatorics,
core,expertmix,external,fast_lz,fixedmix,gstream,histogram,huffman,legacy_lz,
limits,numeric,paq_bridge,parallel,portfolio_auto,ppm,rank,record_periodic,
resources,selection,sparse_runs,stateful,stdout_writer,streaming_backend,
transform,wavelet,zpaq_context}.rs` use mechanism-oriented names. No corpus,
benchmark-member, or domain-inference rename is recommended.

`codecs/paq/{v215,v216,joint_discount,store_state}/` and `vendor/` preserve
external identities and must not be renamed. `FORMAT-CIXB1.md`, `FORMAT-CIXZ1.md`
and standard container labels are interoperability names, not product inference.

## Allowlist distinction

The current tree contains `experiments/`, `benches/`, `examples/`, `src/bin/`,
and `target/`. They are preserved development/research material and are not
proof that they belong in a future shipping export. A future export must use an
explicit allowlist rooted in Cargo production declarations, required codec
bridges, manuals, package metadata, tests selected for release validation,
licenses/notices, and format compatibility documents. It must exclude research
experiments, benchmarks, generated `target/`, fixtures/audit binaries, datasets,
results, and historical evidence without renaming or deleting the source tree.

No current first-party file name encodes Silesia, Canterbury, Calgary, Mozilla,
Dickens, or another evaluation corpus identity.
