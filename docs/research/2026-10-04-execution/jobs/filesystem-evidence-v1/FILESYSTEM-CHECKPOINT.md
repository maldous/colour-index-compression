# Experimental CIX SquashFS filesystem checkpoint

The experimental CIX SquashFS reader is qualified for the pinned evidence in
this directory.  It registers a separate filesystem named `cix_squashfs` and
accepts only private compressor ID **65001**.  It does not modify, replace, or
qualify stock `squashfs`, stock SquashFS tools, or stock Squashfuse.

The portable profile qualification passed with AddressSanitizer and
UndefinedBehaviorSanitizer, the C contract, and 1,545 successful Rust/C exact
choice cases.  Each successful differential case also restored the original
bytes through both the legacy stack entry point and the caller-workspace entry
point.  The source receipt and copied byte-exact qualification receipt are
listed in [filesystem-evidence.json](filesystem-evidence.json).

The warning-clean `kernel-module-v3` build produced the module hash recorded in
the evidence ledger for Ubuntu `6.8.0-142-generic`.  Its reader source is the
verified `fs/squashfs` extraction recorded by `kernel-source-v4`; the CIX
wrapper owns the private-ID dispatch and leaves upstream source unchanged.

The disposable `kernel-vm-v2` run passed under TCG with two virtual CPUs.  The
separate kernel and Squashfuse guest paths each restored and SHA-256 checked all
305 fixture files, including the retained empty file.  The two readers together
performed four xattr checks.  The guest also rejected the three bounded cases:
malformed profile version, truncated profile payload, and oversized declared
profile length.  The VM console and fixture receipt are copied here byte-for-byte
and their digests are recorded in the ledger.

The predecessor records remain part of the evidence.  `kernel-module-v1`
built with first-party warnings; `kernel-module-v2` built warning-clean but was
superseded.  `kernel-vm-v1` failed because the pinned reader converted the
private unsigned wire ID to signed short `-535`.  `kernel-module-v3` restores
the `u16` identity in the CIX-owned dispatcher, and `kernel-vm-v2` is the
passing follow-up.  Those files are linked from the ledger rather than erased.

This is a bounded compatibility result.  It does not assert support for other
kernels, other reader versions, unsigned-module policies outside this disposable
VM, arbitrary malformed images, release media, or any stock implementation.

The later `kernel-module-v4` build also passed using the public bundled
source manifest, without an external research receipt override. Its portable
profile, decoder, registration translation units and module Makefile hashes
match v3. The module was not loaded into the host kernel. This packaging-only
check does not replace or expand the VM-v2 runtime evidence. See the adjacent
`kernel-module-v4/receipt.json` and `input-hashes.json` records.
