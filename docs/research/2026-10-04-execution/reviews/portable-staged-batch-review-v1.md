# Portable staged batch review v1

Date: 2026-10-05
Scope: read-only review of the explicitly staged portable build, public-header, Squash contract, and CLI changes. No build, test, scan, or source edit was performed.

## Evidence match

The staged hashes match the bounded evidence exactly for all five PAQ/spatial CMake files, the runtime CMake file, `cli.rs`, and `packaging/squash/contract.c`.

`bridge-build-policy-v1` records matching before/after hashes for all four PAQ bridge CMake files and the spatial CMake file. Its scope is appropriate: the PAQ configure policy preserved the recorded Linux baseline options; the spatial bridge used explicit separated SDK roots and passed its recorded stride/roundtrip contract. The staged CMake changes implement that same explicit-root and fail-closed compiler-policy behavior.

`runtime-alias-layout-v2` binds the staged runtime CMake and CLI hashes. It passed Linux symlink layout plus synthetic Windows native-only copy layout and refused full-engine staging for Windows, Darwin, and FreeBSD. The staged `normalized_program_name` change has the tested behavior: Windows lowercases basename and removes a case-insensitive `.exe`; Unix leaves the basename unchanged. This is correctly limited to layout and extracted alias logic, not a native Windows executable or full CLI qualification.

`squash-contract-guard-v1` binds the staged contract source and the retained Squash/plugin inputs, then passed compilation and buffer/stream/splice execution. The typed `(void *)0` sentinel change is within that contract's variadic API scope.

The five staged public headers match `public-api-documentation-v1.json`: its before/after review reports `noncomment_text_equal: true` for `cix.h`, `cix_stream.h`, `cix_dictionary.h`, `cix_formats.h`, and `cix.hpp`. The staged changes are documentation-only in that evidence scope.

## Blocking boundaries

No evidence-backed blocker was found in this staged batch itself. The batch does not remove the broader gates: final-source build and export, native-language analysis, full CXX analysis, platform and package qualification, and RC51 acceptance remain open. The six-bridge Sonar v3 run was active during this review and is outside this batch's evidence.

The synthetic Windows runtime layout must continue to be described as staging-only. Full-engine Windows remains refused, and the staged evidence does not establish Windows loader, provider, archive, or executable behavior.
