# Six-bridge header-context v3 review

## Independent read-back

`header-context-v3` completed as `PROBE_COMPLETED_NOT_QUALIFICATION`. The
result indexed exactly six CIX-owned bridge headers as CXX files and ran the
CXX sensor. The scanner log records six indexed files, `Sensor CXX [cxx]`, and
an analysis-successful upload. No Cppcheck run is recorded.

The result's three capture references reproduce the completed capture bytes:

| Bound input | SHA-256 | Read-back |
| --- | --- | --- |
| `context.json` | `651b19…8712d832a` | matched |
| `receipt.json` | `534f1f…0b1e8e793c` | matched |
| `include-mappings.json` | `931181…c2b8b36314` | matched |

The scan identity record also binds those three files, all twelve retained raw
macro/verbose outputs, the six current headers, the current probe/repair and
compiler-context tools, the pinned plugin, and the relevant retained JXL
receipt/database. The six current header hashes match the entries in the
scanned context. Each entry records one per-file normalization:
`__attribute__(...)` is replaced with an empty analyzer preprocessor value
only after validating that the header has its own one GNU default-visibility
API macro. The capture record states `abi_or_layout_claim: none` for every
entry.

The capture's raw macro and verbose outputs are present for JXL, spatial,
PAQ v215, PAQ v216, PAQ joint-discount, and PAQ store-state. The v3 context
uses separate include-root mappings for each bridge; their container paths are
distinct by bridge and passed through the scanner's read-only mount mechanism.

## Measured result

| Header group | Scan-v3 parser recovery | v3 parser recovery |
| --- | ---: | ---: |
| JXL | 13 | 0 |
| Spatial | 10 | 0 |
| PAQ v215 | 4 | 0 |
| PAQ v216 | 4 | 0 |
| PAQ joint-discount | 4 | 0 |
| PAQ store-state | 4 | 0 |
| **Total** | **39** | **0** |

All 98 remaining findings were retained: 81 `cxx:UndocumentedApi`, 7
`cxx:ClassName`, 6 `cxx:FileHeader`, and 4 `cxx:TooManyParameters`. The result
therefore removes the specific parser-recovery analysis gap for these six
headers. It does not remove, waive, or classify the remaining findings.

## Scope and metadata correction

The top-level result field `normalize_gnu_visibility: false` is accurate only
for the legacy single-header command-line flag. In this six-header mode,
per-file visibility normalization was active through the completed capture;
the six context entries and compiled per-file database rows contain it. Taken
alone, the top-level boolean is therefore ambiguous and could be read as
claiming that no normalization occurred.

The minimal follow-up is a result-only metadata correction in the probe tool:
when `--bridge-context-directory` is used, emit an explicit field such as
`normalization_mode: "captured_per_file_gnu_visibility"` and list the six
header paths. Keep the legacy `normalize_gnu_visibility` boolean unchanged for
single-header compatibility. This changes evidence clarity only; it must not
change source, header contents, analyzer rules, or the capture inputs.

This probe is not an ABI, layout, API-consumer, compiler-build, or runtime
qualification. It establishes that this pinned analyzer parses the exact six
captured header contexts once their verified GNU visibility extension is
represented as the one bounded analyzer-side macro normalization.
