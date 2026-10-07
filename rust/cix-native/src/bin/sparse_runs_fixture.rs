#[path = "../limits.rs"]
mod limits;
#[path = "../rank.rs"]
mod rank;
#[path = "../combinatorics.rs"]
mod combinatorics;
#[path = "../sparse_runs.rs"]
mod sparse_runs;

use std::io::{self, Read, Write};

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    let mut input = Vec::new();
    io::stdin().read_to_end(&mut input).unwrap();
    let payload = match mode.as_str() {
        "sparse" => sparse_runs::encode_sparse(&input),
        "runs" => sparse_runs::encode_runs(&input),
        _ => Err("usage: sparse_runs_fixture sparse|runs".into()),
    };
    match payload {
        Ok(payload) => io::stdout().write_all(&payload).unwrap(),
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(2);
        }
    }
}
