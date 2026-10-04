# Leased qualification command

Under a fresh WaveScheduler lease, create a new work directory outside the
repository and run CMake on `rust/cix-native/adapters/squashfs/profile` with
`-fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror`.
Build only `cix_squashfs_profile_contract`, run it with ASAN/UBSAN enabled, and
retain configure/build/contract logs plus hashes of the profile source, header,
contract and native differential source.  Then invoke the existing
`native_differential.rs` qualification against that same frozen C library; it
is intentionally not a Cargo target.  Record it separately rather than
claiming a Cargo test ran.
