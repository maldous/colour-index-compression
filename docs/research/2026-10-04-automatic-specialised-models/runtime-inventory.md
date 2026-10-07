# Portfolio 26 runtime inventory

## Scope and conclusion

This is a source inspection of the fresh-input path rooted at
`benchmarks.competitive_cli` and `benchmarks.competitive_joint_discount_v26`.
It is not a benchmark run.  It separates callable encoder/decoder mechanisms
from historical certificate and cache branches.  The latter must not enter the
ordinary runtime.

`competitive_cli encode` reads only the supplied input, calls
`competitive_joint_discount_v26.encode(data)`, immediately decodes the chosen
complete frame, compares it byte-for-byte with the input, then exclusively
creates the requested output.  `decode` dispatches only from stored frame
identifiers.  The current graph nevertheless contains research-harness
dependencies and several cache branches, so it is an inventory source, not a
ship-ready runtime closure.

The historical all-12 baseline is **25,481,891 complete bytes**.  It is a
regression reference only; the recorded winners are never eligibility keys.

## Fresh encoder graph

```text
competitive_cli
  -> v26 joint-discount
  -> v25 section-constraints
  -> v24 prediction
  -> v23 grid-feedback -> v22 bounded-grid -> v21 fields
  -> large PAQ -> filtered -> procedure/symbol -> intermediate PAQ
  -> symbol-load -> section-pointer -> pointer-feedback -> relocated
  -> ECOFF -> medium PAQ -> hydrogen -> constraint-refresh -> small PAQ
  -> chemical -> fixed-database -> database -> grid-refresh
  -> competitive_codec
```

Every layer first obtains its parent's full frame, appends each eligible
candidate to the selection evidence, and replaces the incumbent only on
strictly smaller complete-frame length.  Ties retain the earlier candidate.
The base codec starts from a checksummed raw `CIXU\x01` frame.  It may add the
joint PPM/mixer, recognised image JXL/JLS/J2K regions, eligible volume modes,
fixed-star grids, and an explicitly configured PAQ candidate.

## Fresh candidates and admission predicates

| Family | Fresh admission predicate | Complete stored frame / decoder closure |
| --- | --- | --- |
| Raw | Always | `CIXU\x01`, varint length, CRC32, bytes; `competitive_codec.decode`. |
| Joint PPM/mixer | Always | `CIXT\x01`; `joint_bounded.decode` after enabling native PPM/mixer bindings. |
| Image / volume | `spatial.regions(data)` accepts a region; volume only when `height > slice_height` | Existing spatial/volume magic; their decoders and JXL/JLS/J2K native backends. |
| Fixed-star grid and feedback/interval variants | exact seven-int record header: numbering 0, motion 1, `abs(magnitudes)==1`, width 28, nonzero count, and `28+28*abs(count)==len(data)` | Grid / feedback / interval magic and corresponding record codec decoder. |
| Database | `len>=256`, first byte 1 or 3, `mysql_record_constraints.split(data[:4096])` succeeds, first column width >=4 and rows satisfy `columns[0]*10 >= rows*9` | Database / fixed-column frame magic, transform inverse, PAQ where selected. |
| Chemical geometry | separator found within first MiB and `sdf_geometry.layout` validates the preceding records | `CIXG\x01` geometry wrapper: original length + CRC + PAQ v215 payload; geometry inverse and PAQ v215 decoder. |
| Hydrogen slots | Chemical predicate | `CIXQ\x01` wrapper with original length + CRC + PAQ v215 payload; hydrogen inverse and PAQ v215 decoder. |
| PAQ v216 tiers | non-database inputs, respectively `<=12 MiB`, `(12,24] MiB`, `(24,48] MiB`, or `>48 MiB` | `CIXP\x01` replaces PAQ's six-byte header, then restores it; pinned PAQ v216 binary. |
| ECOFF / relocation / pointer / section / symbol / procedure / filters | Their validated parser predicates (`objects`, relocation candidates, pointer candidates, section pointers, symbol fields, procedure tables, then filter eligibility) | CIXB-family wrapper, transform descriptor and Brotli payload; matching `ecoff_*_probe` decoder and Brotli. |
| Fields / grouped prediction / pointer prediction | `qualified_structural_paq.eligible`; fixed-star predicate; or pointer locator candidates | Their framed magic, structural inverse, PAQ v215. |
| LSTM | `24 MiB < len <= 48 MiB` and neither database nor chemical recognition | `CIXP\x01` PAQ v215 `-9L`; pinned PAQ v215. |
| Section-constrained PAQ | `ecoff_section_pointer_probe.codec.fields(data,4)` | CIXB mode 4 wrapper, section transform inverse, PAQ v215 `-8`. |
| Joint discount | First four bytes are `0x7fELF`; no path/name/hash condition in fresh branch | `CIXB\x1d`, mode 2; joint-discount inverse and PAQ v215 `-8`. |

The fresh `v26` route invokes `additions(data)` without `cache`; its only
runtime discriminator is the ELF magic.  The named Mozilla record appears only
in the cache branch and is prohibited in the future runtime.

## Historical selected routes to retain

The 12 historical winner labels in `historical-baseline.json` resolve to:

| Members | Historical selected complete route |
| --- | --- |
| dickens, ooffice, reymont, x-ray, xml | PAQ v216 `-8`, <=12 MiB non-database tier |
| mozilla | ELF joint-discount PAQ v215 `-8`, mode 2 |
| mr | volume mode 3 / effort 10 |
| nci | geometry hydrogen-slots PAQ v215 `-8` |
| osdb | database remaining-count PAQ v215 `-8` |
| samba | PAQ v216 `-8`, 12–24 MiB non-database tier |
| sao | grouped prediction PAQ v215 `-8` |
| webster | LSTM prediction PAQ v215 `-9L` |

The corresponding per-file byte and restoration certificates remain in
`historical-baseline.json`; they do not license any input identity lookup.

## Cache and benchmark paths excluded from runtime

The following are qualification-only and must be absent from runtime imports,
package data, and automatic selection:

* All `cache` arguments and `qualify` methods across portfolio layers.  They
  search `complete.json`/result folders by input hash and may reuse stored
  frames.
* `v26._qualified_discount` and `DISCOUNT_ROOT`: it requires the exact Mozilla
  SHA-256, certificate, stored `stream.cixb`, and dependency hashes.
* `competitive_additive`, `competitive_certified`, `competitive_successor`,
  `competitive_grid_refresh` main paths, leaderboard/result manifests, and
  historical parent-frame reuse.  They are cohort accounting, not encoding.
* `competitive_codec` `legacy_cache`, `paq_cache`, and parallel cached-candidate
  handling.  Fresh PAQ encoding remains eligible; stored PAQ byte streams do
  not.
* Probe qualification methods that use `git show`, source checksums, benchmark
  result folders, or historical decoder measurements.

## Decoder and packaging obligations

The current decoder closure is heterogeneous: `competitive_codec.decode`
dispatches base magics, while each layer intercepts its own structural magic
before delegating to its parent.  This inspection found a concrete gap:
`v26.decode` delegates directly to `v25.decode`; no inspected layer dispatches
the v26 `CIXB\\x1d` joint-discount tag, and the base codec rejects CIXB frames.
The fresh v26 joint candidate consequently has no proven current v26 decoder
path.  A maintained runtime must register every stored ID, including
`CIXB\\x1d -> paq_joint_discount_probe.decode`, in one deterministic dispatcher.
It must package the matching Python
transforms, CIXB framing, Brotli binding, PAQ v215/v216 executables or documented
replacement backend, image/volume backend dependencies, and the native PPM
bindings.  A Rust CIX decoder alone is not proven to decode the historical
CIXB-specialist streams.

For every candidate, admission must remain a validated byte-structure check;
candidate failure or unavailable optional dependency must be recorded and leave
the generic raw/native alternatives available.  Complete archive bytes,
including wrapper, descriptions, checksum, termination, and backend framing,
are the only selection metric.

## Focused checks before the single Silesia pass

1. Build a no-cache runtime import graph and assert that no runtime module
   references `results/`, `benchmark-work/`, `complete.json`, input hashes, or
   `git`.
2. For each listed frame family, test valid, malformed, renamed and extensionless
   fixtures; then encode/decode in a fresh process using only the archive.
3. Verify every historical winner has a fresh admission path and a decoder
   registration, or record an explicit dependency/implementation omission.
4. Freeze candidate order, strict tie policy, resource admission and backend
   versions before one four-core, 12 GB, 4 GB/no-swap Silesia pass.
