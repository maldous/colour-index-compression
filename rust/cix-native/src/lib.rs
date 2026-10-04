pub mod core;
pub mod full_engine;
pub mod jxl_bridge;
pub mod paq_bridge;
mod paq_worker;

/// Retained Squash callback ABI; it is implemented by the native core.
pub use core::cix_squash_splice;
/// Compatibility CLI entry point.  Library consumers use [`core`] directly.
pub fn main_entry() {
    let mut args = std::env::args_os().skip(1);
    if args.next().as_deref() == Some(std::ffi::OsStr::new(paq_worker::SWITCH)) {
        std::process::exit(paq_worker::main(&args.collect::<Vec<_>>()));
    }
    core::main_entry();
}
// Preserve the established library module paths while the implementation now
// resides under `core::codec`.
pub use core::codec::{
    adaptive, bsc_ffi, combinatorics, external, fixedmix, huffman, legacy_lz, limits, parallel,
    ppm, rank, resources, stdout_writer, zpaq_context,
};
