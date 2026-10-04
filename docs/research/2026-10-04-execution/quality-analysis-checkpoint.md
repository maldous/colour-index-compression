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
The follow-up `header-context-v2` isolated the GNU visibility extension. With
one explicit per-file analyzer normalization, the unchanged header's parser
recoveries fell from 13 to zero; all 62 remaining findings were retained.
The pinned grammar supports C linkage, so changing `extern "C"` was unnecessary.
This qualifies that narrow analyzer configuration, not the header's API,
ABI or complete product quality. The expanded helper suite passed 46 CXX and
three native-tool checks in `sonar-tool-tests-v13`, together with planning-graph
validation and formatting of the current CLI file.

The six outstanding first-party Cppcheck configuration gaps were then checked
with their actual compiler preprocessing commands in
`jobs/cppcheck-adapter-context-v2`. All six projections completed with no
syntax, internal, unknown-macro or preprocessor-error diagnostics. Compiler
execution used a read-only filesystem except for the admitted projection
directory, with output and evidence limits. The old kernel dependency-output
operand was removed from both preprocessing and analyzer commands. Existing
source findings remain for review; this is not a zero-findings result.

Three userspace overlay inputs are bound to retained source hashes and compiler
receipts. The older kernel build did not record individual hashes for its
forced headers and staged profile source. Those inputs have a separate,
explicit new-analysis freeze, followed by successful preprocessing and
before/after checks; they are not retroactively certified as historical build
inputs. The two adapter projections using the C API read the retained installed
SDK headers, as recorded by their source markers, rather than the public-header
documentation edits occurring in the development tree.

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

The six-bridge follow-up `header-context-v3` indexed all six intended headers with independent captured compiler contexts. Parser recovery fell from 39 to zero. It retained 98 other findings, including 81 API-documentation findings. The recorded per-file GNU visibility normalization remains analyzer-only; the legacy top-level flag refers only to the unused single-header option, as explained in `reviews/six-bridge-header-context-v3-review.md`. No final quality, ABI, or platform acceptance follows from this result.

`include-context-check-v1` validated rebasing on 43 retained adapter compilation records: 138 include directories and nine forced files resolve to the recorded host identities through 17 read-only mount roots. The corrected helper resolves relative operands against each compiler working directory and follows their actual symlink targets. This is a mapping check, not a new Sonar scan or proof that every nested external header resolves. `sonar-tool-tests-v14` passed 54 CXX and three native helper tests, planning validation and current CLI formatting.
