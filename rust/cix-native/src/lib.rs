pub mod core;
pub mod full_engine;
pub mod paq_bridge;

/// Retained Squash callback ABI; it is implemented by the native core.
pub use core::cix_squash_splice;
/// Compatibility CLI entry point.  Library consumers use [`core`] directly.
pub use core::main_entry;
// Preserve the established library module paths while the implementation now
// resides under `core::codec`.
pub use core::codec::{
    adaptive, bsc_ffi, combinatorics, external, fixedmix, huffman, legacy_lz, limits, parallel,
    ppm, rank, resources, stdout_writer, zpaq_context,
};
