#![allow(dead_code)]
pub mod adaptive;
pub mod bsc_ffi;
#[path = "main.rs"]
mod cli;
pub mod external;
pub mod fixedmix;
pub mod huffman;
pub mod legacy_lz;
// The CLI and public codecs share exactly one deadline/cancellation state.
pub use cli::limits;
// Rank coding in the library and CLI shares the CLI module's cancellation
// state and exact combinatorial implementation.
pub use cli::combinatorics;
pub mod oracle;
pub mod parallel;
pub mod ppm;
pub mod rank;
pub mod resources;
pub mod zpaq_context;

pub mod stdout_writer;
