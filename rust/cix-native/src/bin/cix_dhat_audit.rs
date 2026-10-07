//! Heap-allocation audit binary. Built only with `--features audit-dhat`.
//!
//! This executable does not expose a production CIX command and cannot affect
//! normal release binaries. DHAT writes `dhat-heap.json` on clean exit.

use cix_native::{fixedmix, rank};

#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

fn fixture() -> Vec<u8> {
    let mut state = 0x6a09_e667_u32;
    // Keep the profiler smoke probe short enough for an allocator-instrumented
    // build. The committed Criterion probes also use a bounded 4 KiB input.
    (0..4 * 1024)
        .map(|index| {
            state = state
                .rotate_left(5)
                .wrapping_mul(1_664_525)
                .wrapping_add(1_013_904_223);
            (state as u8) ^ ((index / 29) as u8)
        })
        .collect()
}

fn main() {
    let profiler = dhat::Profiler::new_heap();
    let input = fixture();
    let composition = rank::encode_composition_tiles(&input).expect("composition encode");
    let count_range = rank::encode_count_range(&input).expect("count-range encode");
    let mixed = fixedmix::encode(&input);
    assert_eq!(
        rank::decode_composition_tiles(&composition, input.len()).expect("composition decode"),
        input
    );
    assert_eq!(
        rank::decode_composition_tiles(&count_range, input.len()).expect("count-range decode"),
        input
    );
    assert_eq!(
        fixedmix::decode(&mixed, input.len()).expect("fixedmix decode"),
        input
    );
    // Keep every payload alive until after correctness checks. The final line
    // is valid JSON for evidence collection.
    println!(
        "{{\"tool\":\"cix-dhat-audit\",\"input_bytes\":{},\"composition_bytes\":{},\"count_range_bytes\":{},\"fixedmix_bytes\":{}}}",
        input.len(),
        composition.len(),
        count_range.len(),
        mixed.len()
    );
    drop(profiler);
}
