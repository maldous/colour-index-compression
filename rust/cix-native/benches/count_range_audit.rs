//! Audit-only Criterion target for count-range coding.
//!
//! The deterministic synthetic stream prevents corpus-specific selector effects
//! from being attributed to this inner-loop measurement.

use cix_native::rank;
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

fn input(bytes: usize) -> Vec<u8> {
    let mut state = 0x51ed_270bu32;
    (0..bytes)
        .map(|index| {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            (state as u8).wrapping_add(((index / 31) % 7) as u8)
        })
        .collect()
}

fn count_range(c: &mut Criterion) {
    let bytes = input(4 * 1024);
    let mut group = c.benchmark_group("count-range-audit");
    group.throughput(Throughput::Bytes(bytes.len() as u64));
    group.bench_with_input(
        BenchmarkId::new("encode", bytes.len()),
        &bytes,
        |bench, input| {
            bench.iter(|| {
                black_box(rank::encode_count_range(black_box(input)).expect("count-range encode"))
            })
        },
    );
    group.finish();
}

criterion_group!(benches, count_range);
criterion_main!(benches);
