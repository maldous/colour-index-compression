# Latent prior art: byte planes and schema-free columnar transformation

Reviewed 2026-10-03 at the user's request. This is a prior-art and control
note only; it makes no experimental claim and does not reopen an earlier
study.

## Disambiguation

The relevant CAST is Andrea Olivari's 2026 repository, **Columnar Agnostic
Structural Transformation**, rather than the unrelated NLP work named CAST
that reconstructs abstract syntax trees. Its public repository calls itself a
research proof of concept and includes both the paper and source
([repository](https://github.com/AndreaLVR/CAST),
[paper PDF](https://github.com/AndreaLVR/CAST/blob/main/paper/CAST_Paper.pdf)).
The readable Python reference confirms the method rather than merely its
abstract: it samples up to 1,000 lines to choose strict or aggressive regular
expression parsing, extracts skeletons and variables, holds variable lists per
template and field, and serializes the results with escaping
([source](https://raw.githubusercontent.com/AndreaLVR/CAST/main/py/cast.py)).
It has explicit binary/decode/collision/too-many-template passthroughs. Its
own documentation describes a research prototype, an input family weighted to
structured text, and a separate experimental random-access preview
([methods and limits](https://raw.githubusercontent.com/AndreaLVR/CAST/main/README.md)).

CAST therefore challenges any claim that automatic skeleton extraction and
column transposition are new. Its transformation is stronger and more
specialized than fixed-stride byte geometry: it parses line syntax, infers
template identity, stores skeletons once, then groups variables by
template/field before applying a backend. That is neither a generic treatment
of arbitrary bytes nor evidence that a fixed byte-stride representation has
learned syntax. A faithful comparison would need the complete CAST wire
format, parser/fallback decisions, skeleton/template identifiers, escaping,
chunking, backend, and reconstruction cost. Comparing only its transformed
payload would omit the mechanism's material side information.

## Standard byte-stream split (BSS)

Apache Parquet defines `BYTE_STREAM_SPLIT` for `FLOAT`, `DOUBLE`, `INT32`,
`INT64`, and fixed-length byte arrays. For a fixed K-byte value sequence it
scatters byte position *i* from all N values into stream *i*, concatenates the
K streams, and emits exactly K*N bytes: it is a representation change which
needs a following compressor to gain size. The specification says it carries
no length metadata inside the data page and forbids padding
([Parquet encoding specification](https://parquet.apache.org/docs/file-format/data-pages/encodings/)).

This is the closest direct challenge to stride-based byte lanes. It is mature,
standard, and needs no new-theory claim. It also has important scope limits:

* Parquet starts with supplied typed columns and fixed physical widths; BSS
  does not discover record boundaries, a schema, stride, or arbitrary fields.
* Its type admissibility excludes variable-width `BYTE_ARRAY`; it does not
  recover row syntax or select a generic per-byte geometry.
* Page and column metadata already define K and N. A schema-free archive must
  store enough representation metadata itself to reverse its chosen geometry.
* BSS alone is size preserving. The measured archive must charge the selected
  compressor, transform descriptor, framing, integrity field, and any
  selection information.

Apache Arrow's Parquet writer exposes BSS globally or for specified columns;
dictionary encoding takes precedence when both are enabled, and its
documentation also says BSS should be paired with a compression codec
([writer options](https://arrow.apache.org/docs/_modules/pyarrow/parquet/core.html)).
That is a useful warning against calling a backend gain a new byte-plane
coder.

## Lance: useful related machinery, but no established automatic-BSS result

Lance has typed Arrow arrays, layouts, encodings, page-level descriptors and
reader cache state, so it is an example of a complete columnar format rather
than a raw-byte transform. Its specification requires encoded-page layout
metadata, validates buffer/count/offset relationships, and allows existing
LZ4/Zstd wrappers for sparse buffers
([Lance encoding strategy](https://lance.org/format/file/encoding/)).

The current Lance source exposes byte-position entropy statistics: it samples
at most 64 values, counts each byte position, and documents lower positional
entropy as better BSS suitability
([statistics source](https://raw.githubusercontent.com/lance-format/lance/main/rust/lance-encoding/src/statistics.rs)).
That is a heuristic signal, not a complete-byte selector proof. More
decisively, the project's encoding-configuration issue says automatic table
statistics and a compaction re-encoding pass were a later proposed step; the
issue itself covered static selection by column name/type
([Lance issue #4302](https://github.com/lance-format/lance/issues/4302)).
I found no primary source establishing a current Lance writer which
automatically selects BSS by entropy and reports a joint, complete-byte choice
against all alternatives. It would be inaccurate to cite Lance as such a
result.

Lance still raises the appropriate comparison bar: the representation decision
is coupled to typed-column semantics, layout descriptors, codec wrappers and
reader behavior. An entropy sample cannot substitute for materializing and
measuring the complete alternatives.

## What is actually comparable here

| Setting | Faithful mechanism | What must be paid |
|---|---|---|
| Supplied typed column | Parquet-style BSS of each eligible fixed-width column | Schema/type, page/column framing, BSS encoding tag, codec and its framing, integrity and all file metadata |
| Schema-free fixed byte geometry | Declared stride K and byte offset, followed by identity or BSS-style transposition | Source length, stride/offset or equivalent mapping, lane lengths for partial rows, chosen routes/codecs, framing and integrity |
| CAST-style structural text | Parser-selected skeletons/templates plus template-local variable columns | Parser/fallback choice, skeleton registry, template IDs, separators/escaping, chunk boundaries, backend/framing and reconstruction validation |

“Per-column” in a supplied table means a declared semantic column and physical
type. “Per-column” in schema-free byte geometry only means residue class modulo
the stored stride. The latter must not be described as inferred field or schema
selection. Likewise, choosing mapping and backend jointly is a portfolio
decision; the selected mapping/codec ID must be recoverable from the archive
and the full selected archive, not an uncharged trial payload, is the result.

## Minimum faithful BSS controls

For any future bounded schema-free byte-geometry screen, the smallest
sufficient control set is:

1. **Identity + each fixed backend**: original bytes with exactly the same
   archive framing, integrity, backend settings and decoder limits.
2. **Fixed declared BSS**: for every admissible frozen K (and explicit offset
   convention), transpose all K byte positions, store K/offset and partial-row
   information, then apply the same backend. Include K=1 identity.
3. **Whole-candidate selection**: materialize each identity/BSS plus backend
   alternative and store the chosen transform and backend in the archive. Rank
   complete physical bytes, including selector/descriptor cost; do not select
   an unframed transformed payload.
4. **Heterogeneous lanes only if their route/mask is paid**: compare fixed
   all-literal BSS, fixed all-residual lanes, and the automatic per-lane choice
   with its complete mask and per-lane route metadata. A same-transform strong
   backend control is required for the chosen geometry.
5. **Supplied-column control when a real schema exists**: use the actual
   typed-column BSS path and its normal file metadata, separately from the
   schema-free byte path. Do not substitute a guessed stride for the supplied
   columnar control.

The necessary negative cases are unstructured/high-entropy input, partial
final rows, geometry with no positional redundancy, variable-width values, and
inputs for which identity or an established backend wins. These distinguish a
paid reversible representation from a hidden schema/parser/backend advantage.
