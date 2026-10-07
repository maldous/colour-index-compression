# Optional QuixDB Squash plugin qualification review

## Decision

The optional QuixDB **Squash 0.8** plugin cannot be built or loaded on this
host.  The required `squash-0.8` pkg-config entry, development headers,
runtime library and `squash` command are absent.  The only local Squash source
tree is an unbuilt 0.7.0 reference under `benchmark-work/references/`; it is
not API 0.8 and must not be substituted for a 0.8 qualification.

The standard SquashFS transport test has passed separately.  It proves a CIX
archive can be stored as an opaque regular file in a standard Zstd SquashFS
image.  It does not qualify this plugin and does not make CIX a SquashFS
compressor.

The frozen C ABI test for `cix_squash_splice` is also a separate passed check.
It proves callback interoperability with the frozen CIX shared library but
does not exercise QuixDB's plugin discovery or loader.

## Bounded qualification when a real SDK is available

`schedule-plugin-qualification.sh` is root-owned scheduling input.  It makes
no system-wide installation, rebuilds no Rust code, and uses a selected frozen
`libcix_native.so`.  It requires a real Squash 0.8 SDK and command-line tool,
compiles only the existing C shim into an isolated temporary plugin directory,
and checks levels 1, 6 and 9 with a small existing fixture.

The resulting evidence may describe only a **QuixDB Squash codec plugin**.
It must never be used to claim native Linux SquashFS support, a `mksquashfs
-comp cix` option, kernel mountability, or package-manager integration.

## Root-owned execution gate

Run only after all of these are true:

1. A selected, hashed release shared library is available.
2. `pkg-config --modversion squash-0.8` reports an API-0.8 SDK, and its
   `squash` CLI and runtime loader are installed.
3. An existing small local fixture is selected and its hash recorded.
4. The isolated work directory is new and owned by the release evidence run.
5. The base CIX distribution remains independent of this optional plugin.

No network installation, kernel change, SquashFS fork, or public export is
part of this schedule.
