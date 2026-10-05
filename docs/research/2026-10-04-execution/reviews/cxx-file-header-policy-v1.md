# CXX file-header policy finding

The pinned CXX 2.3.0.1496 plugin includes `cxx:FileHeader`, whose own rule
help says the project must supply the expected copyright/license header.
Inspection of its `FileHeaderCheck.class` constant pool confirms
`DEFAULT_HEADER_FORMAT` is the empty string. The current CIX profile activates
all CXX/Cppcheck repository rules without supplying this parameter.

Consequently the 55 adapter `FileHeader` findings are not evidence that those
files violate an agreed CIX header template. They remain preserved as raw
findings; no rule was disabled and no clean result is inferred. Before final
quality qualification, configure an explicit CIX ownership/license-header
policy and apply it only to CIX-owned files with verified license scope.
Third-party files retain their original headers. The separate kernel adapter
must retain its GPL-2.0-only declaration.

The same plugin’s `UndocumentedApi` help requires Doxygen-style documentation
for public declarations. Ordinary prose comments may be useful but do not
satisfy this rule. The final source-cleanup pass should document actual public
APIs, ownership, failure contracts and bounds, rather than merely inserting
empty Doxygen markers. The current adapter scan has 55 such findings. Function
complexity and dense-line findings require source review independently of
these header policies.

This is a configuration/source-work prerequisite, not an issue suppression or
an accepted quality disposition. It must be reconciled with the coordinator
before RC46/RC47 closure.
