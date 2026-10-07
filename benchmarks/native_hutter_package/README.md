# Native Rust Hutter package preparation

This directory prepares a Linux x86_64 package after a separately verified
native CIX archive exists. It does not build, encode, decode, or claim a Prize
result by itself.

The primary package is a static-ELF rules' relaxed split form: one identical bundled
launcher hard-linked as `comp9a` and `decomp9`, plus `archive9.bhm`. `comp9a`
with no arguments reads `enwik9` and invokes bundled native `cix --best
--threads 1 --verbose -o archive9.bhm enwik9`; `decomp9` with no arguments invokes
the same bundled `cix -d -o data9 archive9.bhm`. Its accounting is
`2 * length(cix9) + length(archive9.bhm)`, with zero option bytes because
all flags are compiled in. The launcher extracts the one bundled static CIX client
into a private directory, waits, removes the directory, and delegates CIX's atomic
file replacement.

The private runtime is created beneath the current working directory so its
space is included in runner accounting. Existing output is refused, and SIGINT
or SIGTERM is forwarded to the native child before cleanup. The split package
is the review target; no self-extracting form is prepared.

`package.sh` requires `--native-manifest native-release.json` from the static
d667 native build. It verifies client hashes against that manifest and rejects
clients or the launcher with either `PT_INTERP` or `DT_NEEDED`. It accepts
`--payload archive9.bhm` optionally. Without it, it
prepares and records the two executable programs and their embedded runtime but
does not have an archive or a numeric `S`. It emits `native-package.json` with
the fixed source revision, program and client hashes, static-ELF checks,
compiled flags, and package-source hash. `package-dynamic-experimental.sh`
preserves the earlier dynamic packaging draft for research only; it is not a
qualification path.

The packer accepts `uncix` only as a separately identified static provenance
artifact. It verifies and records its hash but does not embed or count it; both
submission operations use the embedded `cix` client.

Run the script only against the frozen d667 `cix` and `uncix` artifacts and a
verified physical archive. Inspect every generated include, static-ELF
identity and final byte count before counting `S`. The Hutter rules also
require offline execution, resource compliance, public OSI-licensed source and
reviewer acceptance; none is established by this preparation.
