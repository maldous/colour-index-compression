# CIX

CIX (pronounced “six”) is a lossless command-line compressor for arbitrary
byte streams. It writes self-describing CIX archives and provides separate
commands to compress, restore, and stream restored bytes.

This repository is the source-only 0.1.0 release-preparation candidate. Its
project licence is pending owner confirmation; do not redistribute this copy
until the notice at the top of [LICENSE](LICENSE) is removed by that owner.

## Commands

| Command | Purpose |
| --- | --- |
| `cix` | Compress a file or standard input. |
| `uncix` | Restore a CIX archive, test it, or list it. |
| `cixcat` | Restore a CIX archive to standard output. |

```sh
cix report.dat
uncix report.dat.cix
cix --fast -c input.bin > input.cix
cixcat input.cix | tar -x
uncix -t input.cix
```

Input files are retained by default. Use `-f` to replace an existing output,
`-c` for standard output, `--fast` for lower compression latency, and
`--best` for a broader bounded search. Whole-file BEST can spend minutes even
on small inputs: eligible native whole-file work has a 15-minute allowance plus
up to 45 minutes based on input size. Direct external-library calls can add
time and are not preemptible, so this is not a total wall-time limit. Run
`cix --help`, `uncix --help`, or `cixcat --help` for the complete interface.

Archives are CIX streams, not ZIP, gzip, or tar files. CIX processes one file
per invocation; use tar or another archiver when preserving directory trees.

## Build from source

CIX requires Rust 1.98 or later, a C++17 compiler, and development libraries
for zlib, bzip2, liblzma, Zstandard, and Brotli. The locked dependency graph
is fetched from crates.io by Cargo unless your build environment supplies it
from an approved local mirror or vendor directory.

Debian or Ubuntu:

```sh
sudo apt install cargo rustc build-essential pkg-config zlib1g-dev libbz2-dev liblzma-dev libzstd-dev libbrotli-dev
rustc --version   # must report 1.98 or later
make build
```

Fedora, RHEL-compatible systems, or derivatives:

```sh
sudo dnf install cargo rust gcc-c++ pkgconf-pkg-config zlib-devel bzip2-devel xz-devel libzstd-devel brotli-devel
rustc --version   # must report 1.98 or later
make build
```

Some distribution releases package an older Rust compiler. In that case, use
a compatible Rust 1.98-or-later toolchain before building; do not assume the
distribution package meets this requirement. The default build uses Cargo’s
release profile. The LTO profile is available when a distribution policy
permits a slower build:

```sh
make PROFILE=release-lto build
```

Install to the conventional local prefix:

```sh
make PREFIX=/usr/local install
```

For a user installation without Make:

```sh
cargo install --path . --locked --root "$HOME/.local"
```

## Platform status

The release recipes cover source builds on Linux, macOS, and Windows. Linux
x86_64 is the only currently qualified host. macOS and Windows recipes are
provided for native qualification; no binaries for those systems are claimed
or supplied by this source candidate.

The normal CLI links system zlib, bzip2, liblzma, Zstandard, Brotli, and the
platform C++ runtime. Distribution packages should use their system libraries.
Do not present an arbitrary copied binary as a portable standalone build.

## Packaging

`packaging/debian/` and `packaging/rpm/` contain source-package recipes.
They install `cix`, `uncix`, `cixcat`, the three manual pages, licence,
and third-party notices. `packaging/macos/` and `packaging/windows/`
contain native source-build recipes; neither claims a qualified binary. The
optional Squash 0.8 plugin is under
`packaging/squash/`; it is not part of the base package and needs a separate
plugin load test.

## Security and compatibility

Use `uncix -t` before consuming data from an untrusted archive when you
only need an integrity check. CIX validates its framing, length checks, and
checksums, but decompression can require the resource limits selected by the
archive mode. See [SECURITY.md](SECURITY.md) for the supported
reporting path.

Current format references cover [container compatibility](docs/formats/COMPATIBILITY.md),
[CIXB1](docs/formats/FORMAT-CIXB1.md), and
[CIXZ1](docs/formats/FORMAT-CIXZ1.md). The public release should only make
compatibility claims backed by the corresponding release test receipt.

## Licence and notices

The proposed CIX project licence is MIT, pending owner approval. Vendored
libzpaq and libbsc obligations are collected in
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt). The locked Rust dependency
attribution is in [THIRD_PARTY_NOTICES_RUST.md](THIRD_PARTY_NOTICES_RUST.md).
Keep both files with every source or binary distribution.
