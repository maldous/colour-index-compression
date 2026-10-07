# Linux ARM64 QEMU user-emulation path v1

The smaller local route is direct user emulation, not a system guest. A compiled
ARM64 ELF can run through `qemu-aarch64-static -L <ARM64 sysroot>` once the
emulator, ARM64 dynamic loader/libraries, and executable are present. This
avoids an ARM kernel, cloud image, UEFI boot, and guest disk growth.

The local apt metadata provides a candidate pinned closure. `qemu-user-static`
`1:8.2.2+ds-0ubuntu1.18` is a 14,709,858-byte archive with SHA-256
`5bb397f66063efa349f6fd5cb3b68cd96f29edd0994e4ba5115cf0859a716bf0`.
The compiler closure starts at GNU cross 13.3.0-6ubuntu2~24.04.1cross1:
`gcc-13-aarch64-linux-gnu` (21,069,414 bytes, SHA-256
`154d549389d13010bc0ef2e89c7870e22c4193afa69335f8e57c5fc891e75578`),
`g++-13-aarch64-linux-gnu` (12,167,358 bytes, SHA-256
`aa6dcef263e296de40464b7a31cd5f6f8f93e2c407874dc07b176dd2e7e87650`),
`cpp-13-aarch64-linux-gnu` (10,752,882 bytes, SHA-256
`6aafe2a7820e497263d871519326dc3e5bcecc0583cc49852c05abda8c1d2e55`),
`libgcc-13-dev-arm64-cross` (2,616,044 bytes, SHA-256
`eda9d79e18170fd46ee0ed62aa391f52bfe8c1a336d53162f2e1c0a675af548f`),
and `libstdc++-13-dev-arm64-cross` (2,656,446 bytes, SHA-256
`6682425bf6b14a00036684fb338a59a9c5ff89187d0feca5898cc8b0eaa1abfd`).
The supporting exact packages are the simulated closure: binutils,
cpp/gcc/g++ cross bases, ARM64 libc/libgcc/libstdc++ runtime and development
packages, and ARM64 Linux headers. The resolver presently proposes unrelated
QEMU system-package upgrades, so the approved recipe must download only exact
deb archives and extract them into an isolated sysroot/tool prefix; it must not
modify the host package database.

The missing Rust input is the exact `rust-std` component for the frozen Rust
release and `aarch64-unknown-linux-gnu` target. It is not locally cached, so
its release URL, archive byte count, SHA-256, and unpacked size are still
required before admission. The target needs the cross linker and sysroot above
through a frozen Cargo target configuration.

The first runnable validation should remain smaller than product PAQ policy:
compile one selected CIX PAQ bridge (`v215`) with the isolated cross compiler,
then run a tiny C bridge-ABI harness under QEMU user mode against that sysroot.
It proves only that the unmodified upstream source plus CIX wrapper executes on
ARM64. It does not relax the current Rust PAQ worker architecture gate and does
not claim CLI or full-engine PAQ support. If it fails, preserve the exact tool
and source identities and stop before policy work.

After a bridge pass, a second separately approved job can cross-build the CIX
CLI with the frozen Rust standard library and run a generated archive/fresh
exact decode under QEMU user mode. Only then is a CIX-owned change to the PAQ
worker platform policy worth considering; it must be followed by the real
PAQ-selected CLI path and fresh decode.

The target temporary budget is 750 MB additional to the current shared work:
200 MB exact deb archives and extracted user emulator/cross sysroot, 100 MB
Rust target component, 250 MB isolated Cargo target, 100 MB bridge build and
harness, 50 MB source/logs/receipts, and 50 MB headroom. The package closure’s
full installed and extracted byte total must be calculated from the exact
archives before dispatch; 750 MB is an admission ceiling, not an observed size.
Use one job, at most four host CPUs, 12 GB RAM, and no swap. QEMU user-mode
behavior remains emulated functional evidence, never native throughput.
