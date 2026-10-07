# Linux ARM64 local feasibility v1

A local QEMU system path is technically buildable but not presently runnable.
The installed host components are QEMU system ARM `1:8.2.2+ds-0ubuntu1.16` and
UEFI firmware `qemu-efi-aarch64 2024.02-2ubuntu0.8`. They are insufficient by
themselves: there is no ARM64 kernel, bootable ARM64 rootfs/cloud image,
user-mode emulator, ARM64 GNU toolchain/sysroot, or Rust ARM64 standard library.
The retained `kernel-vm` rootfs is x86-64 only.

The current PAQ bridge CMake wrappers are portable enough to configure on an
ARM64 GNU/Clang Linux compiler: their non-x86 Linux branch keeps `-O3`, strict
floating-point, aliasing, and no-RTTI options without x86 ISA flags. Their
retained upstream PAQ sources have historical `build-linux-cross-compile-aarch64.sh`
files, but those scripts are unqualified source instructions and need absent
cross compilers. No upstream source needs editing for the bridge build itself.

There is a product blocker before a current CLI **plus PAQ** validation can be
claimed. `rust/cix-native/src/paq_worker.rs` currently compiles the native PAQ
worker implementation only for `target_os = linux` and `target_arch = x86_64`;
all other targets return “currently requires Linux x86-64 qualification.” Thus
an ARM64 bridge build alone cannot make current full-engine PAQ selection work.
A CIX-owned platform-policy implementation and focused ARM64 PAQ worker
qualification are required first. This is distinct from a cross compiler or a
QEMU guest setup.

Once that source blocker is resolved, the smallest local path is a QEMU ARM64
system guest, not cross compilation:

1. Retain the installed QEMU and UEFI identities above. Acquire one exact,
   SHA-256-pinned Ubuntu 24.04 ARM64 cloud/rootfs image plus its matching ARM64
   kernel/boot metadata, and a generated no-network cloud-init seed. The image
   version, compressed byte size, expanded byte size, and hash must be recorded
   before admission; none is currently retained.
2. Within that guest, use a pinned ARM64 Rust toolchain/standard-library and
   ARM64 `cmake`, `gcc`, `g++`, and libc development sysroot. Their package
   version, package SHA-256, installed size, and guest paths must be frozen.
   The host’s apt metadata identifies only an optional fallback
   `qemu-user-static 1:8.2.2+ds-0ubuntu1.18` (14,709,858-byte `.deb`, SHA-256
   `5bb397f66063efa349f6fd5cb3b68cd96f29edd0994e4ba5115cf0859a716bf0`); it
   does not replace a bootable guest or supply the missing toolchain.
3. Build the frozen CIX source and selected PAQ bridge identities inside the
   guest, with a fresh private PAQ root. Run one small generated CLI archive,
   fresh-process exact decode, and one PAQ-selected archive/fresh decode.

The initial QEMU admission cannot fit the current shared allocation of roughly
3.21 GB plus a 4 GB job reservation. Before root schedules it, cache preservation
must create actual free capacity and the acquired guest inputs must yield a
specific byte calculation. A provisional **job** ceiling after that admission
is 3.5 GB: 1.6 GB sparse guest disk growth, 1.0 GB target/build outputs, 512 MB
PAQ bridges/private worker, 256 MB kernel/seed/logs/artifacts, and 132 MB
headroom. It uses one QEMU guest, at most four host CPUs, 12 GB RAM, and no
swap. QEMU execution establishes functional behavior only; it does not produce
native ARM64 throughput evidence.

A hosted native `ubuntu-24.04-arm` run is smaller operationally because it
avoids guest-image acquisition, but it still faces the same current PAQ worker
source gate. It is the preferred first executable target after that CIX-owned
policy change and after root resolves Actions/billing activation.
