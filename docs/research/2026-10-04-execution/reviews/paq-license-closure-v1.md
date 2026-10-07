# PAQ source and notice closure review v1

Date: 2026-10-05. This is an engineering inventory of local texts, paths, and
receipts. It makes no legal conclusion about licence interpretation or
distribution obligations.

## Finding

The selected PAQ source trees and source-identity receipts exist. They are not
currently part of the CIX source export or the staged runtime's legal payload.
The prior `UNRESOLVED` status in
`jobs/distribution-engineering-v1/selected-provider-closure.json` therefore
correctly describes release closure, but its wording should not be read as
claiming that no local PAQ source or licence declaration exists.

Each of the four local source roots has a `README.md`. Its command help says
“Free under GPL” and its licence section says the program may be redistributed
or modified under GPL version 2 or later. The source roots do **not** contain a
top-level `LICENSE`, `COPYING`, or GPL text file. This review records that text
only; it does not infer a final SPDX expression or whether a particular bundle
is sufficient.

## Selected source and identity evidence

| Variant | Local retained source root | Source receipt | README SHA-256 | Historical executable SHA-256 |
| --- | --- | --- | --- | --- |
| v215 | `benchmark-work/references/paq8px-v215/paq8px-215` | `docs/research/2026-10-04-native-rc/jobs/paq-v215-build-v1/source.json` | `211a9d3a590de44b1b1956b4dc634b28faf2f4c3d600a1d7b617105febf13fdd` | `b982f1e8307d6c38e8febc6415901fafcc2e84a14d51e0af7c5cbbe6322778e7` |
| v216 | `benchmark-work/references/paq8px-v216/paq8px-216` | `docs/research/2026-10-04-native-rc/jobs/paq-v216-qualification-v1/source.json` | `88134d8f7367e51cbccd3b70a36c113b3f8e453608350e36b5e78819360e76a6` | `4fd7b3e768917a665ee4b91c6df3af1d22f540f7ff5beefe7fec689a8db182cc` |
| joint-discount | `benchmark-work/references/paq8px-cix-joint-discount/source` | `docs/research/2026-10-04-native-rc/jobs/paq-joint-discount-qualification-v1/source.json` | `211a9d3a590de44b1b1956b4dc634b28faf2f4c3d600a1d7b617105febf13fdd` | `7f8a4605eca962cd6015839922afb2f2f7dd669d597921c216919aaf620e8b5a` |
| store-state | `benchmark-work/references/paq8px-cix-store-state/source` | `docs/research/2026-10-04-native-rc/jobs/paq-store-state-qualification-v1/source.json` | `88134d8f7367e51cbccd3b70a36c113b3f8e453608350e36b5e78819360e76a6` | `6b815f63502c515a95654df316deb30b6a050fbee1293897f4e643c54843212b` |

The four `source.json` receipts contain per-file SHA-256 maps of their
snapshots. `runtime/backend-sources.json` repeats the source paths and the four
historical **executable** hashes; those hashes are not source-tree digests.
The engineering provider manifest separately pins the selected bridge DSOs:
`645f…43757` (v215), `fc51…8fb2` (v216), `8e8b…a597`
(joint-discount), and `57bb…598b` (store-state).

## CIX-owned bridge boundary

`rust/cix-native/codecs/paq/{v215,v216,joint_discount,store_state}` contains
only CIX-owned C/C++ bridge sources and headers. Each corresponding CMake file
requires an explicit `CIX_PAQ_SOURCE_ROOT`, compiles its `src/*.cpp` plus the
listed bundled zlib sources, and says that root must be the packaged unchanged
variant. The bridge headers label the PAQ implementation unchanged and
worker-only. [PAQ-V215.md](../../../../rust/cix-native/docs/bridges/PAQ-V215.md)
states the same model for all four variants.

This establishes source/bridge separation but does not package the PAQ roots.

## Packaging state

The full-engine runtime staging CMake file installs all four PAQ bridge DSOs,
but no PAQ source or notice files. The allowlisted source exporter copies only
the CIX tree plus `LICENSE`, `THIRD_PARTY_NOTICES.txt`, and
`THIRD_PARTY_NOTICES_RUST.md`; it explicitly excludes `benchmark-work` and
`runtime`. The CIX third-party notice and Debian copyright currently cover only
vendored libzpaq/libbsc and Rust crates, not these PAQ variants.

Consequently a source tree or staged full-engine runtime that selects these
bridges has a concrete closure gap: the selected PAQ root, its per-file receipt
or immutable package identity, and the declared source notice text are not
carried through the export/staging output.

## Concrete handoff for distribution work

Do not alter upstream PAQ source. The packaging owner should add a final
dependency-closure entry for each selected variant that binds:

1. one of the exact source receipts above (or an immutable reproducible source
   package with an equivalent file manifest);
2. the selected bridge DSO SHA-256 from `selected-provider-closure.json`;
3. the source-root README attribution/licence text and any separately selected
   full licence text; and
4. an explicit export/staging destination for those materials.

Then extend the exporter/runtime-package manifest and notices from that exact
selected closure. The existing allowlist already identifies this requirement at
`packaging/export/source-allowlist.json` under `codec_dependency_contracts`;
it must not be bypassed by a workstation `CIX_PAQ_SOURCE_ROOT`.
