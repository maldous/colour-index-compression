//! Audit-only microbenchmarks for public, format-preserving CIX hot paths.
//!
//! Inputs are synthetic and deterministic. They are deliberately not corpus
//! fixtures: this measures implementation work, not selector quality.

use cix_native::{fixedmix, rank};
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

fn mixed_input(bytes: usize) -> Vec<u8> {
    let mut state = 0x9e37_79b9_u32;
    (0..bytes)
        .map(|index| {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            // A repeating record-like channel plus deterministic noise keeps
            // rank/count-range and mixer branches exercised.
            (state as u8).wrapping_add(((index / 17) % 11) as u8)
        })
        .collect()
}

fn cix_hot_kernels(c: &mut Criterion) {
    // Four KiB keeps the audit smoke run bounded. Larger blocks belong in a
    // separately recorded Criterion invocation after perf identifies a hot
    // kernel worth the extra wall time.
    let input = mixed_input(4 * 1024);
    let mut group = c.benchmark_group("native-hot-kernels");
    group.throughput(Throughput::Bytes(input.len() as u64));
    group.bench_with_input(
        BenchmarkId::new("composition_rank", input.len()),
        &input,
        |b, data| {
            b.iter(|| {
                black_box(
                    rank::encode_composition_tiles(black_box(data)).expect("composition encode"),
                )
            })
        },
    );
    group.bench_with_input(
        BenchmarkId::new("count_range", input.len()),
        &input,
        |b, data| {
            b.iter(|| {
                black_box(rank::encode_count_range(black_box(data)).expect("count-range encode"))
            })
        },
    );
    group.bench_with_input(
        BenchmarkId::new("fixedmix", input.len()),
        &input,
        |b, data| b.iter(|| black_box(fixedmix::encode(black_box(data)))),
    );
    group.finish();
}

criterion_group!(benches, cix_hot_kernels);
criterion_main!(benches);
