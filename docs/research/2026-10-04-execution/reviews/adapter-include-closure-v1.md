# Adapter include-closure review v1

**Scope:** read-only review of `tools/sonar-cxx/repair.py` against the actual
qualified adapter compiler records and `scan-v3` container compilation
database.  No source, tool, or scan was modified.

## Root cause

`external_include_mounts()` at
`tools/sonar-cxx/repair.py:524-544` only collects absolute `-I`, `-isystem`,
and `-iquote` operands.  `containerize_commands()` at lines 546-562 rewrites
only absolute path operands.  It does not resolve the actual compiler working
directory for relative include or forced-include operands.

The three kernel adapter commands in
`scan-v3/cix-native-adapters/compile_commands.json` retain:

```
-I./arch/x86/include
-I./arch/x86/include/uapi
-I./include/uapi
-include ./include/linux/compiler-version.h
-include ./include/linux/kconfig.h
-I./ubuntu/include
-include ./include/linux/compiler_types.h
```

Their recorded directory is `/cix-external/7`, derived from the qualified
working directory `/lib/modules/6.8.0-142-generic/build` in
`filesystem-commands-v1.json`.  The source build command is correct: the
kernel-module-v4 build log shows `make` entering the matching header tree.

However, the generic header tree contains symlinks such as:

- `arch/x86/include/uapi` -> the sibling
  `linux-headers-6.8.0-142/arch/x86/include/uapi` tree;
- `include/uapi` -> the sibling `linux-headers-6.8.0-142/include/uapi` tree.

The current anonymous `/cix-external/7` bind contains only the generic tree.
Those symlinks therefore resolve outside that bind.  The scanner records the
resulting missing paths exactly:
`/cix-external/7/arch/x86/include/uapi`,
`/cix-external/7/include/uapi`, and
`/cix-external/7/ubuntu/include`.

This is a scanner input-rebasing error, not a missing product header or an
unsupported kernel construct.  It also explains the broad external-header
warnings that contaminate the adapter parser result.

## Smallest sound correction

Extend the existing command rebasing pipeline; do not add a broad `/usr/src`
mount and do not manufacture declaration shims.

1. In `external_include_mounts()` (lines 524-544), for each actual command,
   resolve a relative include operand against that command's recorded absolute
   `directory`.  Admit the resolved path only if it exists, is a directory,
   and is outside the CIX source root.  Do the same for the parent directory of
   an existing relative forced-include file.

2. In `containerize_commands()` (lines 546-562), rewrite those relative
   operands to the direct, resolved, read-only mount path.  Handle both joined
   and two-token forms for `-I`, `-isystem`, `-iquote`, `-idirafter`,
   `-include`, and `-imacros`.  The rewrite must be row-specific because
   `./include` means the compiler record's directory, not the scanner process
   working directory.

3. Keep `directory` itself mapped as today, but do not rely on it to make
   symlinked relative include paths work.  Directly mounting the canonical
   resolved include directory gives the parser the same header content chosen
   by the qualified compiler and avoids following a host-only sibling symlink.

4. Record the source command, its original working directory, each resolved
   relative operand, and the resulting read-only destination in the scan
   receipt.  Reject a relative operand that escapes or cannot be resolved from
   the recorded directory; do not guess an include root.

This is a narrow extension of the current absolute-path behavior.  It reuses
only paths that the actual passed compiler argv names and requires no source
normalization or runtime algorithm change.

## Why this is sufficient to address the observed defect

The qualified kernel command already establishes the required working
directory and all relative include operands.  Resolving the listed operands
before mounting selects their real target directories, including the separate
Ubuntu common-header targets behind the header-tree symlinks.  It removes the
specific missing `/cix-external/7/...` paths without mounting unrelated host
content.

The same row-aware handling also covers legitimate non-kernel records with
`-I.` or relative forced includes.  Their current behavior otherwise depends
on an output/build directory that is not necessarily available inside the
scanner container.

This correction should be applied and re-scanned before considering any
GObject, Node, Blosc, RocksDB, or SquashFS parser projection.  It will not by
itself remove a genuine pinned-parser grammar limitation, but it is necessary
to distinguish one from missing compilation context.
