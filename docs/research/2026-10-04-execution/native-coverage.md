# Native retained-port coverage and historical dispatch contract

**Status: source inventory refreshed 2026-10-05.** This is not a full-route
qualification or portfolio receipt. It reads the current 41-module Python
reference tree and current native tree, and records only the narrow
`address_relations` foundation-v12/v13 test evidence cited below. It does not
reopen a benchmark or claim a current portfolio result.

The decisive observation is architectural: `rust/cix-native/src/full_engine`
contains several real reversible implementations. `mixed.rs` and `regions.rs`
now also provide a compiled CIXH1 carrier and input-derived region discovery.
However, the inspected native selector, generic archive decoder, and portfolio
code still do not call a full-engine specialist catalogue. A module can
therefore be *library-only* without being an available CIX route. Every route
below remains unqualified as an ordinary CLI route.

## Wire boundary

`CIXB1` is an ASCII generic portfolio container. It is not the same format as
the binary historical specialist prefixes `CIXB\x03`, `CIXB\x0b`, `CIXB\x0c`,
`CIXB\x13`, `CIXB\x1d`, `CIXB\x1e`, `CIXB\x1f`, and `CIXB\x20`. Generic
`CIXG1`, `CIXG2`, `CIXM5`, `CIXM6`, `CIXF1`, and `CIXZ1` likewise remain
separate from the binary historical `CIXG\x01`, `CIXD\x01`, and related
specialist envelopes. Dispatch must identify exact bytes before choosing an
inverse; it must never infer a family merely from a printable prefix.

The complete machine-readable module and wire map is
[native-coverage.json](native-coverage.json). Status words mean:

- **library-only**: native reversible functions exist but no admitted top-level
  selection or decode edge reaches them.
- **partial-unwired**: source has part of the route, but lacks a required
  transform, provider stack, envelope, or dispatch edge.
- **declared-but-unlinked**: native source explicitly rejects the transform.
- **absent**: no native equivalent was found in this inventory.

## Actual native coverage by reference module

| Reference module(s) | Current native evidence | Status | Missing dispatch requirement |
|---|---|---|---|
| `backends.py` | `paq_bridge.rs`, `paq_supervisor.rs`; `CIXP\x01` ids 1 and 2 are represented by `full_engine/containers.rs` | partial-unwired | Catalog and decoder must bind v215/v216 workers; joint-discount and store-state remain distinct, non-`CIXP` variants. |
| `engine.py`, `model.py`, `specialized.py` | No native `catalog` or selector module | absent | Input-derived candidate registry, selection, and frame dispatch. |
| `heterogeneous.py` | `mixed.rs::encode_with/decode_with` implements the CIXH1 carrier | library-only | Catalog selection and top-level CIXH1 decode dispatch. |
| `regions.py` | `regions.rs::structured_regions/regions/boundaries` implements bounded input-derived discovery | library-only | Catalog selection and carrier binding. |
| `chemical_db.py`, `sdf_geometry.py`, `sdf_hydrogen.py` | `graph_residuals.rs`, `structured_frames.rs` implement transforms/envelope callbacks | library-only | Bind `CIXG\x01`/`CIXQ\x01` to PAQ and catalog/decode. |
| `mysql_record_constraints.py`, `mysql_fixed_columns.py` | `record_ordering.rs` implements matching transforms and `CIXD\x01`/`CIXD\x02` frame functions | library-only | Bind backend, admission, and top-level decode. |
| `mysql_remaining_counts.py` | Arithmetic helpers and record primitives only | partial-unwired | Exact remaining-count CIXD route and its backend/catalog/decode. |
| `ordered_subset.py`, `multinomial.py`, `framing.py` | `arithmetic.rs` provides range/rank/checksum primitives | library-only | Consumer route must prove exact payload layout. |
| `ecoff_constraints.py`, `ecoff_fields.py`, `ecoff_got.py`, `ecoff_pointer_deltas.py` | `address_relations.rs` implements reversible transforms and CIXB frame helpers | library-only | Backend callback binding plus native specialist dispatch. |
| `ecoff_section_pointers.py`, `ecoff_pdata.py`, `ecoff_pdata_symbols.py`, `ecoff_symbol_loads.py` | `address_relations.rs` has active internal `ECSP1`, `ECPD1`, `ECPD2`, and `ECSL1` chains | library-only | Exact nested PAQ/Brotli/store-state backend stacks, public route binding, catalog, and top-level decode. |
| `ecoff_call_entries.py` | No native equivalent found | absent | Transform, inverse, fixture and dispatch. |
| `ecoff_relocated_pointers.py` | Candidate parsing exists privately in `address_relations.rs`; no public transform/frame route | partial-unwired | Exact transform/inverse and framing. |
| `executable.py` | Frame constructors/parsers for `CIXB\x03`, `\x0b`, `\x0c`, `\x13`, `\x1d` | partial-unwired | Exact native backend stacks, catalogue/top-level dispatch, and still-unported call-entry/relocated-pointer route coverage; do not advertise frame recognition as decode support. |
| `grid_backend.py`, `grid_conditional.py`, `grid_context.py`, `grid_feedback.py`, `grid_grouped.py`, `grid_interval.py`, `image_grid.py`, `record_float_grid.py` | `strided_values.rs` is a bounded WCS-grid route only | absent | Each exact reference transform/frame plus catalog and decoder. |
| `multiscale_volume.py`, `spatial_image_codec.py`, `volume_image_codec.py` | `volume_lifting.rs` and `jxl_provider.rs` provide generic backend-injected frames | library-only | Pinned native JXL provider, route admission and archive dispatch. |
| `cli.py`, `__init__.py`, `legacy/__init__.py` | Native CLI/generic decoder exists | partial-unwired | Route table must expose all completed specialist encoders/decoders under the ordinary executable. |

## Historical portfolio26: highest-priority missing paths

The historical baseline is evidence only, but it establishes which paths must
be accounted for before the native RC can represent the prior 12-member
portfolio. It records five generic v216 members, plus these specialist
families:

1. **PAQ v215/v216 bridge and supervised native dispatch.** Required by the
   generic PAQ winners and by the chemical/database paths. The recorded
   Dickens v215 `-9L` improvement also depends on it. `CIXP\x01` only assigns
   v215 and v216; it must not be reused for joint-discount or store-state.
2. **Executable joint-discount/filtered chain.** The historical Mozilla route
   needs `CIXB\x1d`, the now-active section-pointer chain, its exact PAQ mode,
   and a bounded native decoder. The `ECSL1`/`ECPD1`/`ECPD2` chain has narrow
   foundation evidence, but no native catalogue or nested
   PAQ/Brotli/store-state route stack has been wired, so frame helpers alone
   cannot restore a finished archive.
3. **Volume/JXL and multiscale.** Current volume code is backend-injected,
   while no native catalogue opens the pinned provider or emits/recognizes the
   route. The recorded multiscale comparison needs the envelope retained even
   though it did not show a new payload gain.
4. **Chemical and database.** The core transforms exist, but neither can be
   selected or decoded from an ordinary native archive. The historical NCI and
   OSDB routes depend on those missing edges.
5. **Grouped-grid and LSTM/prediction.** No corresponding native
   implementations were found. They are needed to account for the historical
   SAO and Webster winners; the recorded `-12L` Webster comparison remains
   resource-excluded under the stated 12 GB bound.
6. **Heterogeneous carrier.** `mixed.rs` now provides a native CIXH1 carrier
   and `regions.rs` provides discovery, but no catalogue/selector or top-level
   decoder wires them into the ordinary CLI. This remains distinct from
   whole-file portfolio selection.

## Narrow tested-module evidence

Foundation-v12 recorded the nontrivial active/ambiguous relation coverage;
foundation-v13 records the corrected malformed-case pass, an offline check/build,
and 11 passing `full_engine::address_relations` tests. That narrow scope includes frozen ECOFF
relation vectors, active and ambiguous symbol-load cases, section-pointer and
pdata-symbol reversibility, and malformed GOT/pointer metadata rejection. It
does **not** test a provider-backed CIXB archive, catalog selection, mixed
carrier routing, or ordinary CLI dispatch. The source remains the authority for
the coverage table; the test receipt narrows confidence only for that module.

## Required dispatch shape

A completed native route needs all of these edges:

```mermaid
flowchart LR
  A[Input bytes] --> B[Bounded input-derived admission]
  B --> C[Candidate registry and resource reservation]
  C --> D[Exact transform plus named native provider]
  D --> E[Paid frame and route ID]
  E --> F[Top-level native archive decoder]
  F --> G[Bounded provider plus exact inverse]
  G --> H[Checksum and original bytes]
```

The current source supplies portions of D/E for several families, but not the
complete path. Each retained route needs focused source-to-frame parity where
applicable, fresh native encoding, separately started archive-only native
restoration, malformed/limit cases, resource accounting, and proof that no
Python process, PATH lookup, or undeclared backend is involved.
