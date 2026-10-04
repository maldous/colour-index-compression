# Current C/C++ quality evidence

The fresh scan indexed all 1,420 intended files across seven separate projects.
Its complete reports are retained in `sonar-preparation/scan-v3`. This is not a
clean-source result. The scanner process completed, but issue-level parser
recoveries and several Cppcheck configuration failures remain.

| Scope | Indexed files | Findings | Parser recoveries | Cppcheck configuration errors |
|---|---:|---:|---:|---:|
| CIX adapters | 55 | 766 | 26 | 6 |
| CIX core | 21 | 612 | 39 | 0 |
| Native dependencies | 29 | 4,735 | 1,960 | 1 |
| PAQ joint-discount | 331 | 4,486 | 829 | 1 |
| PAQ store-state | 328 | 4,426 | 826 | 1 |
| PAQ v215 | 328 | 4,381 | 825 | 1 |
| PAQ v216 | 328 | 4,424 | 825 | 1 |

`qualification-review.json` explicitly records these gaps beside the original
producer result. The original completion classification omitted the CXX
parser-recovery rule and some configuration errors. The repaired gate now
detects those categories; `sonar-tool-tests-v9` passed its 25 CXX and three
native-tool tests plus planning-graph validation. Neither an empty default
Sonar quality gate nor successful indexing establishes clean analysis.

The earlier five GIO/7-Zip parsing failures were resolved through their actual
compiler preprocessor commands, retaining source maps and recording the small
analyzer-copy normalization. The integrated five-file check passed without
fatal configuration diagnostics. Remaining GStreamer, Blosc2, kernel,
SquashFS, and dependency contexts require their own recorded compiler inputs.
Public-header parser recoveries still need investigation; they are not yet
proven to be unavoidable parser limitations.

The official CXX compilation-database interface supports per-file compiler
macros and include directories, including compiler-derived context for files
without an ordinary compilation command. That provides a documented next
probe without guessing platform macros or altering vendor source.
See the [CXX compiler-context documentation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Compilers).

The first measured header-context probe is now complete. The successful JXL
C++17 compiler invocation supplied 462 macros and eight include roots, captured
from empty input to avoid importing header guards. Applying this recorded
context to the unchanged public JXL header left all 13 parser recoveries in
place. `header-context-v1` is a preserved negative result, not qualification.
The first reported failure is at the C-linkage opening; the parser context and
its handling of the following export declarations still require diagnosis.
The current helper suite passed 30 CXX and three native-tool checks in
`sonar-tool-tests-v10`, together with planning-graph validation.

The server now has a read-only root, bounded mounts for every declared writable
volume and `/tmp`, no Docker log driver, and bounded startup/log capture.
Retained evidence is admitted before writing, with space reserved for a final
failure receipt. The actual scan reserved 3,935,105,024 bytes against the shared
4,000,000,000-byte temporary limit. The successful registration probe is
`probe-v12`; the preceding refused reservation and failed startup are retained.
The independent resource review found no remaining blocker in this revised
boundary. This is a reservation proof, not a measured compression-memory result.

The scan predates the separately qualified JXL drain extraction. Consequently,
it must not be relabelled as final-source qualification after that change.
Final source export, native-language Sonar, platform/package qualification,
and RC51 acceptance remain open. Benchmarking and publication remain held.
