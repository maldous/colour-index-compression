# Rust dependency notice audit — release 0.1 candidate

**Scope.** This private audit reads the frozen candidate's `Cargo.toml` and
`Cargo.lock` and the already-present local Cargo registry cache. It does not
download crates, alter the public export, or decide legal obligations. The CIX
project licence remains a proposed MIT grant pending owner confirmation.

## Finding

`THIRD_PARTY_NOTICES.txt` in the candidate export records the vendored C/C++
components (`libzpaq`, `libbsc`, and its embedded `libsais`) but does not name
the Rust crates in the locked dependency graph. The graph contains 32
registry-sourced crates in addition to CIX itself. On a Linux source build,
Rust code from the direct dependencies and their transitive dependencies is
compiled into the CLI binaries; `flate2` also uses `libz-sys` to link the host
zlib library. The build graph additionally contains helper crates, and the
lock includes macOS/Windows conditional crates for cross-platform resolution.

The local package metadata declares only permissive expressions in the cached
set: MIT, Apache-2.0, combinations of those, and one zlib-or-Apache-2.0-or-MIT
expression (`dispatch2`, a macOS conditional crate). This is metadata evidence,
not an independent licence interpretation. System zlib and the other native
libraries are dynamically linked distribution dependencies and have their own
system-package notices.

## Direct dependency scope

| Declared direct dependency | Purpose observed from manifest / lock |
| --- | --- |
| `sha2`, `crc32fast`, `num-bigint`, `num-traits` | Rust runtime code compiled into the CLI binaries. |
| `flate2` with `zlib` | Rust wrapper code plus `libz-sys`; links system zlib. |
| `libc`, `ctrlc` | Platform and signal handling runtime code; `ctrlc` reaches Unix-specific `nix` on Linux. |
| `cc` | Build dependency for native C/C++ compilation. |

The transitive graph also includes crypto primitives, numeric traits, platform
bindings, configuration/build helpers, and target-conditional Apple/Windows
crates. A source release that supports all listed target recipes should retain
an attribution record for the full lock, while a platform binary notice may be
narrowed only after a build-specific dependency analysis.

## Evidence bundle

`generate_rust_notice_bundle.py` makes a review bundle from an existing cache:

```sh
python3 generate_rust_notice_bundle.py \
  --lock /path/to/Cargo.lock \
  --registry-src /path/to/registry/src/index.crates.io-... \
  --output /private/output/rust-notices
```

It copies top-level cached licence/notice files when present and records each
locked crate's name, version, registry source, Cargo.lock checksum, declared
licence expression, and copied-file SHA-256. Crates with no top-level matching
file are listed for manual provenance review. Do not treat the generated bundle
as a replacement for the source packages or a legal determination.

## Precise release amendment proposed

A complete private prepared artifact now exists as
`THIRD_PARTY_NOTICES_RUST.md`. Before publishing a public source or binary release, regenerate and add that file (or fold equivalent content into
`THIRD_PARTY_NOTICES.txt`) which:

1. identifies the exact `Cargo.lock` crate names and versions;
2. states each crate's Cargo-declared licence expression;
3. includes required bundled notice text where the applicable licence or crate
   notice calls for redistribution; and
4. distinguishes Rust crates compiled into a specific binary from build-only
   and target-conditional entries in the accompanying package receipt.

Ship that attribution file beside `LICENSE` and the existing third-party
notices in source archives, binary tarballs, Debian/RPM package documentation,
and future platform packages. Retain the existing vendored C/C++ notices.

The precise patch is in `INTEGRATION_PATCH.md`. This is a documentation/package-only amendment. It should be generated from
the final locked graph and then reviewed with the final binary/package receipt;
it does not require a compressor or format change.
