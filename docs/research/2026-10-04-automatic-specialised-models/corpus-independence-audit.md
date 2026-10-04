# Corpus-independence audit of historical portfolio predicates

## Scope

Read-only audit of the historical Portfolio 26 fresh-input predicates.  It asks
whether a predicate can be evaluated from the supplied bytes and disclosed
runtime limits, rather than whether its historical selected file happened to
pass it.  No input was read and no candidate was run.

The production requirement is: arbitrary bytes enter the same command; a
validated parser may add a specialist, and failure or ineligibility must leave
generic candidates available.  No filename, path, corpus identity, known hash,
or **benchmark-specific** offset/length may control the ordinary path.  Standard
schema offsets and lengths read from the supplied bytes, and declared
input-size/resource limits, are legitimate when bounded and decoder-reproducible.

## Findings

| Predicate / source anchor | Classification | Finding | Required remediation |
| --- | --- | --- | --- |
| v26 fresh ELF gate, `competitive_joint_discount_v26.py:56-79` | **Needs strengthening** | `data[:4] == ELF` is byte-local and does not use corpus data, but it is only a file signature, not proof that mode-2 parsing is supported. | Replace with a bounded ELF structural validator used by the transform. If invalid or unsupported, record the omitted specialist and continue. Remove the cache branch entirely from runtime: lines 60-68 contain Mozilla's exact SHA-256 and stored-frame lookup. |
| PAQ tiers, `competitive_small_paq.py:18-21`, `competitive_medium_paq.py:14-17`, `competitive_intermediate_paq.py:15-19`, `competitive_large_paq.py:14-17` | **Allowed resource policy, empirically uncalibrated** | 12/24/48 MiB boundaries are input-size/compute caps, not corpus identifiers. They nevertheless originate in benchmark portfolio staging and create discontinuous candidate availability. | Make the profile resource budget explicit and freeze it before qualification. Treat tier values as runtime policy, not format recognition; account for a candidate skipped by budget. Consider a single cost-estimate admission function rather than historical buckets. |
| LSTM, `competitive_prediction_v24.py:21-22` | **Benchmark-shaped policy** | The 24–48 MiB range and database/chemical exclusions are not LSTM schema invariants. The exclusions can prevent a generic model from competing on otherwise valid specialist input. | Replace with a declared model-memory/time admission and permit the generic tier to run independently of specialist recognition when resources permit. The model's own input requirements must be validated separately. |
| Fixed-star grid, `competitive_codec.py:99-104` | **Supported external subset; parser hardening required** | The seven signed integers match the SAO TDC/WCSTools header (`star0`, `star1`, `nstars`, `stnum`, `mprop`, `nmag`, `nbent`). WCSTools' binary reader documents a 28-byte header for the retained subset: no ID (`stnum=0`), 18 base bytes + `2*abs(nmag)` magnitudes + 8 bytes proper motion. The portfolio condition `abs(magnitudes)==1`, `width==28`, `numbering==0`, `motion==1` is therefore a narrow byte-derived schema subset, rather than an unexplained Silesia signature. It still has no magic/checksum at this entry point and arbitrary bytes can imitate it. | Retain as an automatic specialist only behind a bounded, endian-explicit parser that checks signed count/ranges, full record extent and successful inverse. Candidate construction errors must be nonfatal omissions. Store the selected layout/version in the frame and test malformed/near-match inputs. |
| Grid feedback interval blocks, `competitive_grid_refresh.py:20-28` | **Empirical tuning** | Modes and 4096/1024/256/64 block sizes are a finite historical grid, not required by the record layout. | Define FAST/DEFAULT/BEST candidate limits from stated cost bounds; do not embed the exact historical grid as a claim of format necessity. Freeze values before qualification. |
| Database recognition, `competitive_database_portfolio.py:11-14` | **Partial schema invariant; unsafe fallback** | Header byte, split result, column width and density are data-derived. The `split` call is unguarded: hostile arbitrary bytes beginning with 1 or 3 can raise and prevent generic fallback. The 4096-byte inspection bound is legitimate if documented as a bounded recognizer, but is not proof of a complete file schema. | Catch all parser/overflow/format failures at the specialist boundary and downgrade to ineligible. Validate full structural consistency before transform. Record `recognizer_invalid` separately from no-match. |
| Chemical gate, `competitive_chemical.py:18-23` | **Bounded schema check, incomplete** | The first-MiB separator bound is a valid cost cap; `geometry.layout` is a schema parser. The 1 MiB value is not a universal SDF rule and may exclude valid late-header layouts. | State it as profile detection budget, add overflow/line/count limits, and ensure parser failures are nonfatal. Schema-defined offsets/lengths remain valid; benchmark-specific offsets or known layout lengths do not. |
| Hydrogen gate, `competitive_hydrogen.py:57-63` | **Valid reuse of chemical recognition, subject to above** | It has no additional corpus condition, but inherits chemical false positives/negatives. | Use an explicit hydrogen-capability result from the validated chemical parse rather than repeat a weak Boolean gate. |
| Image / volume discovery, `spatial_image_codec.py:15-35`; candidate loop `competitive_codec.py:263-268` | **Mixed** | DICOM tag scan and 240-byte raster equation are byte-derived. The raster layout is explicitly described as observed in Silesia x-ray (`spatial_image_codec.py:3-5`), so it is an unproven layout hypothesis rather than an established general image standard. That does not make the reversible, paid candidate intrinsically corpus-bound. Axis alternatives and volume modes are representations, not recognition evidence. | Retain DICOM after bounded, overflow-safe tag validation. Seek provenance and add strict validation for the 240-byte layout; meanwhile it may be a bounded, automatic reversible-layout candidate if it carries full inverse information, charges the entire frame, and declines safely on invalid data. Admit volume only after the selected image region validates dimensions and memory estimate. |
| Executable locator families, examples `ecoff_got.py:52-80`, `ecoff_relocated_pointers.py:14-38`, `ecoff_section_pointers.py:16-44` | **Schema-derived but parser-hardening required** | Predicates parse object headers, sections, relocations and symbols; they use supplied bytes rather than corpus names. Their assumptions are ECOFF/ABI-specific and rely on nested offsets/lengths. | Isolate a total, bounded object parser that validates magic, endianness, section-table extent, relocations, alignment and integer arithmetic before any specialist. Unsupported ABI/object files must decline. Each locator must return a reasoned capability result, never throw through the portfolio. |
| Base spatial/volume candidate set, `competitive_codec.py:141-163`, `263-276` | **Valid selection mechanics; unbounded candidate work risk** | Strict complete-size comparison is independent. Each recognised region receives several codecs/modes; multiple crafted regions can multiply work. | Cap recognised regions and candidate count per profile, reserve aggregate memory/temp space, and report omitted candidates. The cap must be generic and frozen, never file-name keyed. |

## Explicitly forbidden historical leakage

`competitive_joint_discount_v26.py:60-68` contains an exact Mozilla hash and
loads `results/leaderboard/.../stream.cixb`.  All `cache`/`qualify` branches
through the portfolio similarly use historical input hashes, result folders,
stored frames, and source certificates.  They are valid evidence checkers but
must be excluded from runtime dependencies and package data.  The same applies
to `competitive_codec` cached PAQ/legacy parameters at lines 141-162 and
254-276.

## External schema provenance

Checked 2026-10-04, without corpus acquisition:

* [WCSTools `wcscat.h`, lines 68–85](https://raw.githubusercontent.com/olebole/wcstools/master/libwcs/wcscat.h)
  defines the seven SAO TDC catalogue header fields.
* [WCSTools `binread.c`, lines 985–1050](https://raw.githubusercontent.com/olebole/wcstools/master/libwcs/binread.c)
  describes the 28-byte subset and its field-dependent record accounting.

This supports the fixed-star layout predicate's provenance. It does not prove
that every matching byte string is a valid catalogue, so the bounded parser and
inverse checks above remain required. An OpenZL illustrative schema was not
used as parsing authority because its `STNUM` condition conflicts with the
retained `stnum=0` subset. The 240-byte raster layout remains unresolved.

## Mixed-region implication

The historical codec can identify subregions for image candidates, but the
portfolio competition remains whole-input: `spatial.encode_region` builds a
complete frame whose metadata LZMA-compresses the surrounding prefix and suffix.
It is not a general mixed-
region container.  A future mixed-region runtime must give every region a
stored type/length/checksum and a decoder-visible boundary, charge all
descriptors, and compare its complete archive against whole-input candidates.
It must not select regions from empirical Silesia offsets or saved segment maps.

## Unresolved questions for the integration plan

1. Which exact ABI/object formats are supported by each ECOFF parser, and what
   maximum metadata/section/relocation counts fit profile resource limits?
2. Is the 240-byte raster path a documented external format with a sufficient
   validity signature, or solely a historical x-ray layout?  It should not be
   advertised as general image recognition until resolved.
3. What deterministic cost estimator replaces PAQ and LSTM historical size
   buckets while keeping FAST/DEFAULT/BEST bounded?
4. Which candidate errors are recoverable parse/no-benefit omissions versus
   runtime/dependency failures that should fail an explicit requested route?
5. How will a unified decoder registry prevent magic collisions and ensure the
   specialist selected on an arbitrary input is independently decodable?

## Required preflight assertions

* Search runtime modules and package data for `results/`, `benchmark-work/`,
  `complete.json`, known Silesia hashes/names, and cache parameters; none may
  be reachable from ordinary encoding. Standard parser offsets/lengths supplied
  by the input and declared resource ceilings remain allowed.
* Fuzz or adversarially test each recognizer with truncated, malformed and
  look-alike byte strings; generic fallback must still encode/decode.
* Test valid recognised inputs after rename and at different lengths where the
  schema permits, then test stored specialist archive decoding in a new process.
* Freeze caps and profile budgets before the one authorised Silesia pass.
