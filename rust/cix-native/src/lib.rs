#![allow(dead_code)]
pub mod adaptive;
#[path = "main.rs"]
mod cli;
pub mod external;
pub mod fixedmix;
pub mod huffman;
pub mod legacy_lz;
// The CLI and public codecs share exactly one deadline/cancellation state.
pub use cli::limits;
pub mod parallel;
pub mod resources;
pub mod oracle;
pub mod ppm;
pub mod rank;
pub mod zpaq_context;

pub mod stdout_writer;
