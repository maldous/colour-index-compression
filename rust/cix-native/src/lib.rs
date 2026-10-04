pub mod c_api;
pub mod c_dictionary_api;
pub mod c_format_api;
pub mod c_stream_api;
mod cli;
pub mod core;
pub mod dictionaries;
pub mod full_engine;
pub mod jxl_bridge;
pub mod paq_bridge;
mod paq_supervisor;
mod paq_worker;
pub mod standard_formats;

/// Retained Squash callback ABI; it is implemented by the native core.
pub use core::cix_squash_splice;
/// Compatibility CLI entry point.  Library consumers use [`core`] directly.
pub fn main_entry() {
    let mut args = std::env::args_os().skip(1);
    if args.next().as_deref() == Some(std::ffi::OsStr::new(paq_worker::SWITCH)) {
        std::process::exit(paq_worker::main(&args.collect::<Vec<_>>()));
    }
    cli::main_entry();
}
// Preserve the established codec primitive paths without exposing the private
// executable implementation module.
pub use core::{
    adaptive, bsc_ffi, combinatorics, external, fixedmix, huffman, legacy_lz, limits, parallel,
    ppm, rank, resources, stdout_writer, zpaq_context,
};
