#![allow(dead_code)]
#[path = "main.rs"]
mod cli;
// Reexport the CLI codec instances so library calls share models and globals.
pub use cli::{adaptive, bsc_ffi, external, fixedmix, huffman, legacy_lz, parallel, ppm, rank, resources, stdout_writer, zpaq_context};
// The CLI and public codecs share exactly one deadline/cancellation state.
pub use cli::limits;
// Rank coding in the library and CLI shares the CLI module's cancellation
// state and exact combinatorial implementation.
pub use cli::combinatorics;
pub mod oracle;
