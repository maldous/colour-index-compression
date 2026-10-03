# SquashFS integration audit — CIX 0.1

**Decision:** CIX 0.1 must not claim native SquashFS compression support and
must not ship the existing `squash/` plugin as SquashFS support.  It is a
plugin for the unrelated QuixDB **Squash 0.8 codec API**, which creates and
reads ordinary CIX streams.  It has no relationship to the Linux SquashFS
filesystem format or to `mksquashfs`/`unsquashfs`.

## Evidence inspected

* Local `mksquashfs` and `unsquashfs` are both 4.6.1 (2023-03-25).
  `mksquashfs -help` lists only `gzip`, `lzo`, `lz4`, `xz`, `zstd` and `lzma`.
* The running kernel has `CONFIG_SQUASHFS=y` and decompressor support for zlib,
  LZ4, LZO, XZ and Zstd.  It has no CIX decompressor.
* A local, non-root smoke test created a reproducible Zstd SquashFS image with
  `mksquashfs -comp zstd`, extracted it with `unsquashfs`, and byte-compared
  both files successfully.  `unsquashfs -s` reported SquashFS 4:0, `zstd`,
  128 KiB blocks.  The temporary artefact is
  `/tmp/cix-squashfs-smoke-KN7HS3` and is deliberately outside the source
  tree.
* Official upstream source was read from a fresh, isolated checkout at
  `/tmp/cix-squashfs-tools-Iw6FD0`.  `squashfs-tools/compressor.h` defines an
  in-process `struct compressor` interface; `compressor.c` compiles a fixed
  list of gzip, LZO, LZ4, XZ, Zstd and LZMA wrappers.  It has no runtime plugin
  ABI.  The SquashFS 4 superblock assigns compressor IDs 1--6 to those
  algorithms.  The Linux kernel's SquashFS documentation lists the same
  supported compression family. [Linux SquashFS documentation](https://kernel.org/doc/html/next/filesystems/squashfs.html)

## Why the present CIX callback cannot be used

`squash/squash-cix.c` registers QuixDB Squash callbacks and calls
`cix_squash_splice`.  That Rust function is a whole CIX **stream** encoder or
decoder: it emits/consumes CIX container headers, frames and footer checksums.
SquashFS instead invokes a selected compressor separately for data and
metadata blocks and stores only the selected compressor ID in the filesystem
superblock.  Inserting a CIX stream into a data block would not make a CIX
SquashFS image; standard readers would send it to the decoder named by the
superblock and fail.

Treating this as an upstream CIX feature would also be unsafe: a new ID would
need a matching decoder in every target kernel, and the upstream tools would
need matching code for image creation and extraction.  Reusing an existing
ID is format corruption.  A custom ID can be useful only for a controlled,
custom kernel and matching forked tools; it is not distributable, mountable
or package-manager compatible as a standard SquashFS image.

## 0.1 distribution policy

* Keep the base CIX CLI package independent of SquashFS.
* Do not include `squash/`, a SquashFS adapter, a claimed `mksquashfs -comp
  cix` option, or a CIX compressor ID in the public 0.1 source or binary
  package.
* The existing QuixDB Squash 0.8 plugin may remain private research code.  If
  released later, name it `cix-squash-codec-plugin` and describe it as a
  **QuixDB Squash plugin**, never as SquashFS support.  Its API SDK is absent
  on this host, so it is not qualified for a release package.
* CIX archives can be included as regular files in a standard SquashFS image,
  but this normally double-compresses the payload and is not a native CIX
  filesystem codec.  It should not be a promoted installation method.

## Bounded future custom-integration experiment

This is a separate GPL-compatible integration project, not a CIX 0.1 task.
It must be kept outside the MIT/Apache-compatible CIX distribution because it
would modify and link with GPL-2.0-or-later `squashfs-tools` sources.

1. Fork one pinned SquashFS-tools release in an isolated GPL worktree.
2. Add a new, unassigned compressor ID only after coordinating the format with
   the SquashFS/kernel maintainers; never overload IDs 1--6.
3. Implement block-local `init`, `compress` and `uncompress` wrappers around a
   deterministic, headerless CIX block codec.  The wrappers must honour the
   input block bound, return a stored/raw block when compression is not
   smaller, and reject malformed compressed blocks before output.
4. Add the same decoder and compressor-ID support to a matching test kernel.
   Without that kernel change, images can only be extracted by the forked
   userspace tools; they cannot mount.
5. Test under a disposable unprivileged extraction directory first:

   ```sh
   mksquashfs fixture-root cix.sqfs -noappend -comp cix -processors 1 \
     -all-time 0 -mkfs-time 0 -no-xattrs
   unsquashfs -no-progress -d extract cix.sqfs
   diff -ru fixture-root extract
   unsquashfs -s cix.sqfs
   ```

6. Before any mount test, verify a kernel with the custom decoder in an
   isolated VM.  Check data, inode, directory, fragment and xattr paths;
   incompressible blocks; empty files; sparse files; corrupted blocks and
   compressor options; reproducibility; and cross-version decode.  A mount
   test requires separate authority because it changes kernel/system state.

There is no feasible minimal adapter that preserves ordinary SquashFS
compatibility.  The correct first release position is standard CIX CLI
archives and standard SquashFS images using their supported codecs.
