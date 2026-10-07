# Non-PAQ provider source closure v1

This review reads the frozen fourteen-provider closure and retained receipts. It
does not build, copy, test, acquire, or select an artifact.

## Bound inputs

The selected closure binds ten non-PAQ Linux x86_64 ELF artifacts by SHA-256:
the CIX JXL and spatial bridges, three JXL libraries, three Brotli libraries,
CharLS, and OpenJPEG. The engineering-only
`docs/research/2026-10-04-execution/reviews/non-paq-provider-sources-v1.json` binds those selected hashes
to the retained evidence below without changing provider selection.

| Group | Existing evidence | Disposition |
| --- | --- | --- |
| JXL, Brotli, Highway, skcms | `jxl-provision-v2/source.json` records the `libjxl` v0.12.0 commit, recursive source tree map (4,094 files) and required submodule commits. `jxl-bridge-v3/installed.json` contains the exact selected hashes for the bridge and six JXL/Brotli shared libraries. | Complete local source input identity. The new staging recipe verifies the entire tree before copying it. |
| CIX spatial bridge | `spatial-counts-v2/source.json` hashes the frozen CMake file, bridge implementation, header and README. `provider-binary-binding-v1.json` binds that snapshot to selected `libcix_spatial_bridge.so` through the recorded CMake install RPATH change. | Complete engineering source-to-selected-installed-binary trace for the recorded snapshot. It does not make later current-source rebuilds byte-identical. |
| CharLS 2.4.2 | `codec-sdk-provision-v1` records the exact runtime and development `.deb` archives. `ubuntu-codec-source-provenance-v1.json` records the official Ubuntu `.dsc`, original and Debian source archives with byte counts and SHA-256, and streams the retained runtime package member to the selected ELF digest. | Immutable source inputs identified; archives are not yet retained or staged as a source tree. |
| OpenJPEG 2.5.0 | The same evidence records exact binary inputs, official Ubuntu source descriptors and component archives, and streams the retained runtime package member to the selected ELF digest. | Immutable source inputs identified; archives are not yet retained or staged as a source tree. |

## Reusable staging recipe

`rust/cix-native/packaging/export/stage_non_paq_provider_sources.py` takes only
explicit roots and evidence. Before writing, it verifies the selected ELF
digests, every JXL source receipt member, the frozen spatial bridge source
members, the JXL installed-receipt mappings, and both retained CharLS/OpenJPEG
runtime/development package archives. It stages the available JXL source and
spatial snapshot, then writes an identity record that retains the unresolved
source obligations. `--require-source-complete` deliberately fails until those
two source-package chains exist.

The scheduled caller must pass a fresh export directory, the frozen selected
closure, the repository evidence root, the retained JXL root, the retained
spatial snapshot and the retained codec package-archive directory. This is an
engineering source-input step; it is not part of a public release export.

## Evidence-selected remaining gap

Retain the six already identified CharLS and OpenJPEG descriptor/component
archives, verify their recorded SHA-256 values before unpacking, and write
staged source-tree receipts. Then bind those receipts to the existing direct
package-member-to-selected-ELF evidence and add the result to a later final
dependency closure.

This review makes no legal conclusion. Notice text and licence-field review
remain governed by the separate notice work.
