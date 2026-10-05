# Local Linux ARM64 fallback inventory v1

The local machine cannot currently execute a Linux ARM64 CIX binary. It has
`/bin/qemu-system-aarch64`, which is a system emulator, but no `qemu-aarch64`
user emulator, no `aarch64-linux-gnu-gcc` or `aarch64-linux-gnu-g++`, and only
the host `x86_64-unknown-linux-gnu` Rust target. The retained kernel VM rootfs
is an x86-64 library overlay, not an ARM64 guest rootfs; no ARM64 kernel image,
initramfs, or usable guest userspace was found under `benchmark-work`.

Several retained PAQ source trees contain historical ARM64 cross-compile shell
scripts. They are source instructions only: they require the absent GNU ARM64
C/C++ cross compilers and do not provide an executable target or qualified ARM64
PAQ output. Likewise, retained JXL’s cross-compile helper is not an installed
ARM64 sysroot or runnable guest. Cross-compilation alone would not establish
this target’s functional support.

The smallest actual validation route is one native `ubuntu-24.04-arm` private
runner job after root enables and dispatches the already prepared inventory
workflow. It must then add a separately reviewed native-contract job that:

1. checks out the frozen source SHA and records the hosted ARM64 identity;
2. builds the current CLI natively with its frozen Rust lock and records the
   Rust/C/C++ toolchain identities;
3. builds or supplies each mandatory ARM64 PAQ bridge from the selected retained
   PAQ source identities, with a fresh private PAQ work root;
4. runs a generated small-byte CLI encode followed by a fresh-process exact
   decode, then a PAQ-selected path and its fresh decode.

That is native execution, unlike a cross compile. It is still only CLI plus
mandatory PAQ evidence: full-engine qualification additionally requires the
selected JXL and spatial providers, resource/failure cleanup contracts, and
cross-target archive exchange.

For bounded admission, reserve one worker, at most four CPUs, 12 GB RAM, no
swap, and at most 4 GB temporary storage across all local work. A conservative
initial partition is 2.5 GB disposable native target/build output, 512 MB PAQ
bridge and private-worker output, 512 MB checked-out source/logs/artifacts, and
476 MB headroom. No component acquisition is admitted until its actual stored
byte size and SHA-256 are recorded; the current fallback contains none of the
needed ARM64 execution components.

Missing components are: an executable Linux ARM64 environment (either the
hosted ARM64 runner or an ARM64 kernel, initramfs/rootfs, and user-mode/system
emulation path); Rust standard library for `aarch64-unknown-linux-gnu`; ARM64
linker/compiler and matching sysroot; and selected ARM64 PAQ bridge outputs.
For local QEMU validation, the kernel, rootfs, emulator configuration, Rust
standard library, cross toolchain/sysroot, and all provider artifacts must each
be acquired by an approved source-identity recipe with exact archive size,
SHA-256, extraction location, and the above aggregate admission calculation.
No such acquisition or build was performed here.
