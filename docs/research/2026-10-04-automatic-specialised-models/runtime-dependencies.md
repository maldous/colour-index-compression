# Portfolio-26 runtime dependency closure audit

**Method.** Read-only inspection of the current working tree, existing local
Python environment, local PAQ reference/fork trees, and `cargo tree`-free
source imports. No archive, corpus, build, encoder, decoder, package, or
network operation was run. Paths below are current local evidence, not a
shipping layout.

## Result

Portfolio-26's fresh encoder path is **not** a closed runtime: it imports
research-harness modules and resolves PAQ executables from
`benchmark-work/references`. Its cache/certificate branch additionally reads
`results/leaderboard` and is explicitly research-only. A standalone runtime is
possible, but it must extract the fresh transforms, frame parsers, PAQ source
closures and selected JXL wheel/runtime rather than copy the benchmark tree.

| Capability | Fresh encoder/decoder path | Local status | Extraction conclusion |
| --- | --- | --- | --- |
| Generic PAQ v215 / v216 | `benchmarks.competitive_codec`, CIXP wrapper; subprocess with `-simd AVX2` | Both executable references exist and match the hashes hard-coded in `competitive_codec.py`. Source trees and CMakeLists exist. | Extract `runtime/paq/v215` and `runtime/paq/v216` source plus deterministic CMake recipe; install only after target AVX2 admission. Keep CIXP version byte dispatch. |
| Joint-discount PAQ mode 2 | `competitive_joint_discount_v26` -> `paq_joint_discount_probe` -> `ecoff_section_pointers` transform; CIXB `0x1d` | Fork source and binary exist; fresh path uses mode environment `CIX_JOINT_DISCOUNT=2`, not result cache. | Extract forked PAQ v215 source, CIX discount/register headers, transform/inverse closure and decoder dispatch together. Do not carry `results/leaderboard/paq-joint-discount-full8`. |
| Section/pointer PAQ | `competitive_section_paq_v25` -> portfolio24 -> `qualified_prediction_paq` -> pointer transform | Python source present; v215 backend present. | Extract transform closure and CIXB frame reader; cache qualification paths are omitted. |
| Grouped-grid PAQ | portfolio24 -> `qualified_prediction_paq` -> `grid_conditional_paq_probe` | Python source and v215 backend present. | Extract detector, reversible grouped transform, frame reader, PAQ adapter. |
| Chemical/hydrogen | `competitive_chemical` / `competitive_hydrogen` -> SDF transforms -> PAQ v215 | Python source and v215 backend present. | Extract SDF validator, geometry/hydrogen transforms and CIXG/CIXQ readers. |
| Database remaining-count | `competitive_fixed_database` / `competitive_database_portfolio` -> MySQL record transforms | Python source present; no external native backend in the shown fresh path. | Extract validators, transforms, CIX framing and `cix.multinomial`; standard-library only on the inspected path. |
| Volume/JXL | `volume_image_codec` imports `numpy`, `imagecodecs`, uses `jpegxl_encode/decode`; CIXV | Installed wheel exists: imagecodecs 2026.8.16, CPython >=3.12, NumPy >=2.1. `_jpegxl.abi3.so` and bundled libjxl 0.12.0 / threads / cms libraries exist. No local imagecodecs/JXL source tree was found. | **Required available-host runtime** for the retained winning volume candidate in the approved Silesia pass. Its source-build portability gap is a later distribution/platform task; it is not grounds to omit the candidate. |
| State-only PAQ decoder | `competitive_filtered` -> `ecoff_filtered`; `benchmark-work/references/paq8px-cix-store-state` | This is in the portfolio26 fresh parent chain. `additions(data, cache=None)` admits modes 0/1/2; mode 1/2 decoding invokes the state-only PAQ fork. It also needs Python `brotli` / `_brotli`, v216 for fresh mode 1/2 encoding, and the structural inverse. | **Required runtime closure** whenever the restored filtered candidates are retained. Extract the fork source/binary recipe, CIXB `0x13` decoder dispatch, Brotli dependency, structural transform/inverse, and v216 encoder adapter together. |

## Concrete evidence

- v215 binary: `benchmark-work/references/paq8px-v215/build-local/paq8px`, SHA-256 `b982f1e8307d6c38e8febc6415901fafcc2e84a14d51e0af7c5cbbe6322778e7`.
- v216 binary: `benchmark-work/references/paq8px-v216/build-local/paq8px`, SHA-256 `4fd7b3e768917a665ee4b91c6df3af1d22f540f7ff5beefe7fec689a8db182cc`.
- joint-discount binary: `benchmark-work/references/paq8px-cix-joint-discount/build-local/paq8px`, SHA-256 `7f8a4605eca962cd6015839922afb2f2f7dd669d597921c216919aaf620e8b5a`.
- The three inspected CMakeLists files share SHA-256 `8c38333cb4081e9039452b14869aabaaa86beebd4060b72c0e760f1ee0d33853`; this shows a common base build description, not equivalence of fork sources.
- `volume_image_codec.py` SHA-256 is `ccba8e513a60990bf1470479954bf0423c39eab11655bf6ad932e26755e3ccee` and calls lossless JXL only.
- `imagecodecs` wheel metadata reports version 2026.8.16, BSD-3-Clause, CPython >=3.12 and NumPy >=2.1. `ldd` on `_jpegxl.abi3.so` resolves bundled `libjxl-*.so.0.12.0`, `libjxl_threads-*.so.0.12.0`, `libjxl_cms-*.so.0.12.0`, Brotli libraries, and host glibc/libstdc++.

## Extraction closure

Create a new maintained `cix_runtime_specialized/` closure outside
`benchmarks/`, `results/`, and `benchmark-work/`:

1. `frames/`: CIXP/CIXB/CIXG/CIXQ/CIXV framing, length/CRC checks and archive-only dispatch.
2. `detectors/`: byte-structure validators only; no name/path/hash/result lookup.
3. `transforms/`: copied/reviewed reversible SDF, database, grouped-grid,
   executable/pointer and volume transforms with unit inverse tests.
4. `backends/paq/`: v215, v216 and joint-discount source roots, immutable
   source manifests, a CMake build recipe, SHA identity check of produced
   executable, CPU feature admission and subprocess adapter.
5. `backends/jxl/`: the installed pinned Python 3.12+, NumPy and imagecodecs/JXL
   closure is required on this host for the approved Silesia volume candidate.
   Preserve it for the pass; package its compatible wheel/native libraries or
   obtain a pinned buildable source closure as a later portability task.
6. `backends/paq-state-only/`: extract the state-only fork, Brotli dependency,
   CIXB `0x13` dispatch and structural inverse because filtered parent-chain
   modes 1/2 require them for independent archive decode.

The ordinary selector receives candidate callables from this closure and always
retains generic/raw fallback. A candidate archive stores its model and backend
identifier; decoding must use only that archive and installed closure.

## Buildability and gaps

**Buildable from local source:** base PAQ v215/v216 and the joint-discount fork
have CMake source trees and existing local CMake build evidence. Rebuilding is
not performed here. The exact compiler, CMake version, SIMD policy, source
licences and generated-binary reproducibility remain release gates.

**Present but not a standalone source closure:** Python specialised transforms
are buildable only after their import graph is extracted from benchmark modules.
They currently use standard library plus local `cix.multinomial`, except the
volume path.

**Missing locally for later portability work:** imagecodecs/JXL source and a
source-build recipe. The installed wheel is the required available-host closure
for the approved Silesia pass, while its host-specific nature is not adequate
evidence for portable Debian/RPM/macOS/Windows distribution. No package licence
bundle for that wheel was audited in this pass.

**Explicitly excluded from runtime extraction:** benchmark orchestration,
`results/`, certificate/cache branches, corpus identifiers, saved archives,
source-hash acceptance as encoder selection, and any path under
`benchmark-work` once the extracted source manifests are made.
